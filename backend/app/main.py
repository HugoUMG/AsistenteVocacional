import os
import re
import unicodedata
from collections import Counter
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import edge_tts
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from google.genai import errors as genai_errors

from app import models, recomendar, preguntas, extras, psicometrico, cip_fogliatto, holland, holland_filtro, personalidad, auth, cuota, filtro, diversificado


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: create_all en arranque en vez de migraciones. Cambiar a Alembic
    # cuando el esquema empiece a evolucionar con datos reales que conservar.
    Base.metadata.create_all(bind=engine)
    # create_all NO agrega columnas a tablas que ya existen. Las nuevas se
    # agregan aqui, idempotentes (sintaxis de PostgreSQL). ponytail: sigue sin
    # ser Alembic; cuando haya mas de un par de estas lineas, migrar.
    with engine.begin() as con:
        con.execute(text("ALTER TABLE resultados_holland ADD COLUMN IF NOT EXISTS perfil JSONB"))
        con.execute(text("ALTER TABLE respuestas_cuestionario ADD COLUMN IF NOT EXISTS juicio VARCHAR(12)"))
        con.execute(text("ALTER TABLE respuestas_cuestionario ADD COLUMN IF NOT EXISTS juicio_nota TEXT"))
    yield


app = FastAPI(title="Recomendador Vocacional API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(genai_errors.APIError)
async def _gemini_fallo(request, exc):
    """Cualquier falla de la API de Gemini (modelo retirado, cuota agotada,
    caida del servicio). Sin este manejador la excepcion sale del stack de
    middlewares, la respuesta se va SIN cabeceras CORS y el navegador reporta
    "Failed to fetch": el alumno ve una pantalla muerta y nadie sabe por que.
    Con 503 y mensaje, el frontend lo muestra tal cual."""
    from fastapi.responses import JSONResponse
    print(f"[gemini] la API fallo: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "El asistente no esta disponible en este momento. "
                 "Intentalo de nuevo en unos minutos."},
    )


@app.exception_handler(recomendar.ContenidoRechazado)
async def _contenido_rechazado(request, exc):
    # Gemini bloqueó la petición/respuesta por sus filtros de seguridad (p. ej. el
    # estudiante escribió algo ofensivo). 422 con mensaje amable en vez de un 500.
    from fastapi.responses import JSONResponse
    print(f"[seguridad] Gemini rechazó contenido: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "No pudimos procesar esa respuesta. Por favor evita "
                 "lenguaje ofensivo o fuera de tema e inténtalo de nuevo."},
    )


# Quien puede llamar a la API desde el navegador: en local, el servidor de
# desarrollo de Vite; desplegado, la URL del sitio. Varios se separan con coma.
# No se usa "*": las peticiones llevan el token de sesion en una cabecera.
ORIGENES = [
    o.strip()
    for o in os.getenv("ORIGENES_PERMITIDOS", "http://localhost:5173").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["*"],
    allow_headers=["*"],
)


# El nombre lo teclea el estudiante y luego se muestra en el dashboard/PDF y se
# inyecta en los prompts, así que se valida en la frontera: sin control de
# largo/caracteres, un troll podría meter un nombre kilométrico o basura.
_NOMBRE_OK = re.compile(r"^[\wáéíóúüñÁÉÍÓÚÜÑ'’\-\. ]+$")

# ponytail: lista curada de groserías comunes en español, NO exhaustiva — no
# atrapa evasiones ("3stupido", "est-upido") ni todo el vocabulario ofensivo; es
# un filtro básico para el nombre (que se muestra en el dashboard/PDF), no una
# moderación completa. Se compara por palabra tras normalizar (minúsculas + sin
# acentos), así "Estúpido" y "ESTUPIDO" caen igual. La MISMA lista vive en el
# frontend (Chat.jsx) para cortar antes de que el nombre llegue al saludo.
_PALABRAS_OFENSIVAS = {
    "estupido", "estupida", "idiota", "imbecil", "tonto", "tonta", "tarado",
    "pendejo", "pendeja", "mierda", "puta", "puto", "cabron", "cabrona", "verga",
    "culero", "culo", "pene", "pito", "cono", "chinga", "chingar", "mamon",
    "mamada", "joder", "jodete", "marica", "maricon", "zorra", "perra", "polla",
    "follar", "gilipollas", "cojones", "baboso", "babosa", "estupidos", "putos",
    "putas", "wey", "guey", "coger", "verguero",
}


def _normaliza(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sin_acentos.lower()


def _tiene_groseria(nombre: str) -> bool:
    tokens = re.split(r"[ \-.']+", _normaliza(nombre))
    return any(t in _PALABRAS_OFENSIVAS for t in tokens)


# --- Schemas (validación en la frontera: datos del navegador) ---
# El session_id lo manda el navegador (un UUID, 36 chars) y se guarda en columnas
# VARCHAR(64) de uso_tokens y resultados_psicometricos. Sin el tope, uno más largo
# reventaba el INSERT y salía como 500 sin manejar (psycopg StringDataRightTruncation).
SessionId = Annotated[str | None, Field(default=None, max_length=64)]


class RegisterIn(BaseModel):
    nombre: str
    email: EmailStr | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        v = " ".join(v.split())  # recorta y colapsa espacios
        if not (2 <= len(v) <= 40):
            raise ValueError("El nombre debe tener entre 2 y 40 caracteres.")
        if not _NOMBRE_OK.match(v):
            raise ValueError("El nombre solo puede llevar letras, espacios, guiones y apóstrofos.")
        if _tiene_groseria(v):
            raise ValueError("Por favor escribe tu nombre real, sin palabras ofensivas.")
        return v


class EstudianteOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr | None = None

    model_config = {"from_attributes": True}


class AreaHolland(BaseModel):
    letra: str = Field(pattern="^[RIASEC]$")
    title: str = Field(max_length=60)
    score: int = Field(ge=0, le=holland.MAX_AREA)


class HollandRef(BaseModel):
    """El perfil de Holland que el chat arrastra cuando el alumno hizo el test
    antes (modo 3). Llega desde localStorage, o sea que es dato NO confiable que
    termina dentro del prompt: por eso se valida forma y tamaño acá y el texto
    lo arma el backend (`holland.bloque`), no el navegador."""

    codigo: str = Field(pattern="^[RIASEC]{3}$")
    areas: list[AreaHolland] = Field(min_length=6, max_length=6)
    ocupaciones: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("ocupaciones")
    @classmethod
    def _titulos_ok(cls, v: list[str]) -> list[str]:
        if any(len(t) > 120 for t in v):
            raise ValueError("Título de ocupación demasiado largo")
        return v

    def bloque(self) -> str:
        return holland.bloque(self.codigo,
                              [a.model_dump() for a in self.areas],
                              self.ocupaciones)

    def puntajes(self) -> dict[str, int]:
        """{letra: 0-40}, para que Holland pueda pesar como estructura sobre el
        catálogo (experimental, `HOLLAND_EN_RECOMENDACION`)."""
        return {a.letra: a.score for a in self.areas}


class RasgoScore(BaseModel):
    clave: str = Field(max_length=40)
    puntaje: int = Field(ge=0, le=100)


class PersonalidadRef(BaseModel):
    """El perfil del test corto de personalidad/valores/estilo cognitivo,
    igual de NO confiable que HollandRef (viene de localStorage): se valida
    forma y tamaño acá, y el texto del prompt lo arma el backend."""

    personalidad: list[RasgoScore] = Field(min_length=6, max_length=6)
    valores: list[RasgoScore] = Field(min_length=4, max_length=4)
    estilo_cognitivo: list[RasgoScore] = Field(min_length=4, max_length=4)
    estilo_dominante: str = Field(max_length=40)

    def bloque(self) -> str:
        return personalidad.bloque({
            "personalidad": {r.clave: r.puntaje for r in self.personalidad},
            "valores": {r.clave: r.puntaje for r in self.valores},
            "estilo_cognitivo": {r.clave: r.puntaje for r in self.estilo_cognitivo},
            "estilo_dominante": self.estilo_dominante,
        })


class SurveyIn(BaseModel):
    estudiante_id: int
    respuestas: dict
    session_id: SessionId = None  # para atribuir el uso de tokens a la sesión
    holland: HollandRef | None = None  # modo 3: hizo el test antes del chat
    personalidad: PersonalidadRef | None = None  # test corto de personalidad antes del chat


class SurveyOut(BaseModel):
    id: int
    estudiante_id: int
    respuestas: dict

    model_config = {"from_attributes": True}


# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/register", response_model=EstudianteOut, status_code=201)
def register(
    data: RegisterIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """Devuelve la cuenta del alumno logueado. El login es obligatorio para
    evaluarse (ver app/cuota.py), asi que ya no se crean cuentas anonimas: el
    nombre que teclea en el chat se sigue usando para el saludo y el PDF, pero
    la cuenta es siempre la de Google."""
    return estudiante


@app.post("/api/submit-survey", response_model=SurveyOut, status_code=201)
def submit_survey(
    data: SurveyIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    # El estudiante_id sale de la sesion, no del cuerpo: con login obligatorio,
    # aceptar el id del cliente dejaria escribir en la fila de otra cuenta.
    resp = models.RespuestaCuestionario(
        estudiante_id=estudiante.id, session_id=data.session_id, respuestas=data.respuestas
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return resp


class TtsIn(BaseModel):
    texto: str


# ponytail: edge-tts es una API no oficial (reversa el servicio "Read Aloud" de
# Microsoft) — gratis y con voz neuronal, pero puede romperse si Microsoft
# cambia el endpoint. Si eso pasa, cae aquí con un 502 y el frontend sigue
# funcionando con la voz nativa del navegador (ver hablar() en Chat.jsx).
_VOZ_TTS = "es-MX-DaliaNeural"


@app.post("/api/tts")
async def tts(data: TtsIn):
    texto = data.texto.strip().replace("**", "")
    if not texto:
        raise HTTPException(status_code=400, detail="Texto vacío")

    async def generar():
        try:
            comunicador = edge_tts.Communicate(texto, _VOZ_TTS)
            async for chunk in comunicador.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            print(f"[tts] edge-tts falló: {e}")

    return StreamingResponse(generar(), media_type="audio/mpeg")


class NextIn(BaseModel):
    respuestas: dict
    session_id: SessionId = None
    holland: HollandRef | None = None  # modo 3: hizo el test antes del chat
    personalidad: PersonalidadRef | None = None  # test corto de personalidad antes del chat


@app.get("/api/departamentos")
def departamentos(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Carrera.departamento)
        .distinct()
        .order_by(models.Carrera.departamento)
        .all()
    )
    return {"departamentos": [r[0] for r in rows]}


@app.get("/api/carreras")
def carreras(db: Session = Depends(get_db)):
    """Catálogo completo para el botón 'Ver catálogo'. El frontend agrupa por
    nombre las sedes que ofrecen la misma carrera."""
    rows = db.query(models.Carrera).order_by(models.Carrera.nombre).all()

    def _arquetipo(perfil: str) -> str | None:
        # ponytail: el perfil empieza "Arquetipo: X. AFINIDAD..."; tomamos la 1a frase.
        m = re.match(r"Arquetipo:\s*(.+?)\.\s", perfil or "")
        return m.group(1) if m else None

    return {
        "carreras": [
            {
                "nombre": c.nombre,
                "universidad": c.universidad,
                "centro": c.centro,
                "departamento": c.departamento,
                "arquetipo": _arquetipo(c.perfil),
                "sello": c.sello,
            }
            for c in rows
        ]
    }


def _carreras(db, respuestas):
    """Carreras filtradas por el departamento (o región, varios separados por
    coma) elegido. 'Ambos' = sin filtro. Si el alumno dijo que abandonó una
    carrera, esa se descarta aquí: no tiene sentido devolverle lo que ya dejó."""
    q = db.query(models.Carrera)
    depto = (respuestas or {}).get("departamento")
    if depto and depto != "Ambos":
        deptos = [d.strip() for d in depto.split(",")]
        q = q.filter(models.Carrera.departamento.in_(deptos))
    carreras = filtro.descartar(q.all(), (respuestas or {}).get("carrera_descartada"))
    if not carreras:
        raise HTTPException(status_code=409, detail="No hay carreras para ese filtro.")
    return carreras


def _registrar_uso(db, session_id, endpoint, uso):
    """Guarda el consumo de tokens de una llamada a Gemini. Sin session_id no se
    atribuye (p. ej. llamadas de prueba)."""
    if not session_id:
        return
    db.add(models.UsoTokens(session_id=session_id, endpoint=endpoint, **uso))
    db.commit()


@app.post("/api/next-question")
def next_question(
    data: NextIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    # Se revisa en cada turno, no solo en el primero: cuenta chats TERMINADOS,
    # asi que no corta al alumno a mitad de su propia conversacion.
    cuota.revisar_tope_diario(db, estudiante)
    carreras = _carreras(db, data.respuestas)
    paso, uso = preguntas.siguiente_pregunta(
        data.respuestas, carreras, data.session_id,
        holland=data.holland.bloque() if data.holland else None,
        holland_puntajes=data.holland.puntajes() if data.holland else None,
        personalidad=data.personalidad.bloque() if data.personalidad else None,
    )
    _registrar_uso(db, data.session_id, "next-question", uso)
    return paso.model_dump()


@app.post("/api/recommend")
def recommend(
    data: SurveyIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    if not recomendar.hay_api_key():
        raise HTTPException(
            status_code=503,
            detail="Falta configurar GEMINI_API_KEY en el backend.",
        )
    carreras = _carreras(db, data.respuestas)
    resultado, uso = recomendar.recomendar(
        data.respuestas, carreras,
        holland=data.holland.bloque() if data.holland else None,
        holland_puntajes=data.holland.puntajes() if data.holland else None,
        personalidad=data.personalidad.bloque() if data.personalidad else None,
        session_id=data.session_id,
    )
    _registrar_uso(db, data.session_id, "recommend", uso)
    carreras_out = [r.model_dump() for r in resultado.carreras]

    # Guarda la recomendación en el registro más reciente de este alumno,
    # para poder cruzarla luego con el juicio del profesional y medir precisión.
    respuesta_id = None
    resp = (
        db.query(models.RespuestaCuestionario)
        .filter(models.RespuestaCuestionario.estudiante_id == estudiante.id)
        .order_by(models.RespuestaCuestionario.id.desc())
        .first()
    )
    if resp is not None:
        resp.recomendacion = carreras_out
        db.commit()
        respuesta_id = resp.id

    return {
        "carreras": carreras_out,
        "respuesta_id": respuesta_id,
        "confianza": resultado.confianza,
        "confianza_nota": resultado.confianza_nota,
        # Solo para quien va en básicos: su siguiente decisión es el
        # diversificado, no la universidad. Sin IA, ver app/diversificado.py.
        "diversificados": (
            diversificado.sugerir([c["carrera"] for c in carreras_out])
            if (data.respuestas or {}).get("nivel") == "Básico" else []
        ),
    }


class SimularIn(BaseModel):
    carrera: str
    descripcion: str
    respuestas: dict
    session_id: SessionId = None


@app.post("/api/simular-dia")
def simular_dia(
    data: SimularIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    sim, uso = extras.simular_dia(data.carrera, data.descripcion, data.respuestas)
    _registrar_uso(db, data.session_id, "simular-dia", uso)
    return sim.model_dump()


class CompararIn(BaseModel):
    carrera_a: str
    descripcion_a: str
    carrera_b: str
    descripcion_b: str
    respuestas: dict
    session_id: SessionId = None


@app.post("/api/comparar")
def comparar(
    data: CompararIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    cmp, uso = extras.comparar_carreras(
        data.carrera_a, data.descripcion_a,
        data.carrera_b, data.descripcion_b,
        data.respuestas,
    )
    _registrar_uso(db, data.session_id, "comparar", uso)
    return cmp.model_dump()


class PsicometricoIn(BaseModel):
    # {"1": 5, "41": 2, ...} — el JSON del navegador manda las claves como texto.
    respuestas: dict[int, int]
    tiempos: dict[str, int] = {}  # segundos por categoría
    session_id: SessionId = None

    @field_validator("respuestas")
    @classmethod
    def _rango_valido(cls, v: dict[int, int]) -> dict[int, int]:
        for item, valor in v.items():
            if not 1 <= item <= 100:
                raise ValueError(f"Ítem fuera de rango: {item}")
            # Ítems 1-40: escala Likert 1..5. Ítems 41-100: índice de opción 0..3.
            ok = 1 <= valor <= 5 if item <= 40 else 0 <= valor <= 3
            if not ok:
                raise ValueError(f"Valor fuera de rango en el ítem {item}: {valor}")
        # Los 40 de personalidad son obligatorios: con menos, la consistencia y la
        # deseabilidad social salían en 0% y la interfaz las pintaba como alerta
        # roja sobre CERO datos, que es indistinguible de haberse contradicho.
        # Las de razonamiento sí pueden ir en blanco (eso es lo que mide 'intentadas').
        if sum(1 for i in v if i <= 40) != 40:
            raise ValueError("Faltan respuestas de la sección de personalidad (son las 40).")
        return v

    @field_validator("tiempos")
    @classmethod
    def _tiempos_sanos(cls, v: dict[str, int]) -> dict[str, int]:
        # El navegador reporta estos segundos y terminan dentro del prompt de la
        # IA: se acotan a [0, 2h] para que un valor absurdo o negativo no genere
        # una lectura sin sentido. ponytail: se recorta, no se rechaza — que un
        # cronómetro raro no le tire el examen encima al estudiante.
        return {k: max(0, min(7200, seg)) for k, seg in v.items()}


@app.get("/api/psicometrico/preguntas")
def psicometrico_preguntas():
    """Banco de 100 ítems SIN la clave de respuestas (vive solo en el backend)."""
    return psicometrico.preguntas()


@app.post("/api/psicometrico")
def psicometrico_calificar(
    data: PsicometricoIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    puntajes = psicometrico.calificar(data.respuestas, data.tiempos)
    fila = models.ResultadoPsicometrico(
        session_id=data.session_id or "sin-sesion",
        estudiante_id=estudiante.id,
        respuestas={str(k): v for k, v in data.respuestas.items()},
        puntajes=puntajes,
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)

    # El resumen es un extra: si Gemini no está disponible, el estudiante se
    # queda igual con sus puntajes ya guardados en vez de perder el examen.
    resumen = None
    if recomendar.hay_api_key():
        try:
            res, uso = psicometrico.resumen(puntajes)
            resumen = res.model_dump()
            fila.resumen = resumen
            db.commit()
            _registrar_uso(db, data.session_id, "psicometrico", uso)
        except Exception as e:
            print(f"[psicometrico] no se pudo generar el resumen con IA: {e}")

    return {"id": fila.id, "puntajes": puntajes, "resumen": resumen}


class CipIn(BaseModel):
    # {"1": "A", "2": "D", ...} — Desagrado, Indiferencia o Agrado por cada ítem.
    respuestas: dict[int, str]
    sexo: str  # el baremo del CIP solo existe separado por sexo, no combinado
    muestra: str = cip_fogliatto.MUESTRA_DEFAULT

    @field_validator("respuestas")
    @classmethod
    def _rango_valido(cls, v: dict[int, str]) -> dict[int, str]:
        for item, valor in v.items():
            if not 1 <= item <= cip_fogliatto.N_ITEMS:
                raise ValueError(f"Ítem fuera de rango: {item}")
            if valor not in cip_fogliatto.VALOR:
                raise ValueError(f"Respuesta no válida en el ítem {item}: {valor}")
        return v


@app.get("/api/cip/preguntas")
def cip_preguntas():
    """Los 150 ítems del CIP y la definición de las 15 escalas."""
    return cip_fogliatto.preguntas()


@app.post("/api/cip")
def cip_calificar(data: CipIn, estudiante: models.Estudiante = Depends(auth.requiere_login)):
    """Califica el CIP y devuelve el perfil por escala.

    ponytail: NO guarda nada en la base de datos. Es un prototipo de un instrumento
    cuya autorización de uso sigue pendiente, así que no corresponde persistir
    respuestas de estudiantes todavía. Cuando haya permiso escrito y supervisión
    profesional, se agrega la tabla y se guarda igual que `psicometrico`.
    """
    return {
        "resultado": cip_fogliatto.calificar(data.respuestas, data.sexo, data.muestra),
        "sinceridad": cip_fogliatto.sinceridad(data.respuestas),
    }


class HollandIn(BaseModel):
    respuestas: str  # 60 dígitos 1-5, en el orden de las preguntas
    zona: int | None = Field(default=4, ge=1, le=5)  # Job Zone; 4 ≈ carrera universitaria
    session_id: SessionId = None  # para guardar el resultado

    @field_validator("respuestas")
    @classmethod
    def _cadena_ok(cls, v: str) -> str:
        if not holland.valida(v):
            raise ValueError(
                f"Se esperan {holland.N_PREGUNTAS} respuestas con valores del 1 al 5"
            )
        return v


def _onet(fn, *args, **kwargs):
    """Traduce fallas del servicio de O*NET a errores que el alumno entienda."""
    try:
        return fn(*args, **kwargs)
    except holland.SinCredenciales as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.HTTPError as e:
        print(f"[holland] O*NET falló: {e}")
        raise HTTPException(
            status_code=502,
            detail="El servicio de O*NET no respondió. Intentá de nuevo en un momento.",
        )


@app.get("/api/holland/preguntas")
def holland_preguntas():
    """Los 60 ítems del Interest Profiler en español, servidos por O*NET."""
    return _onet(holland.preguntas)


@app.post("/api/holland")
def holland_perfil(
    data: HollandIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """Puntajes RIASEC y carreras afines. El cálculo lo hace la API oficial.

    Se guarda el resultado (es el instrumento avalado del proyecto y entra en la
    investigación). Sin session_id no se guarda: son llamadas de prueba."""
    perfil = _onet(holland.perfil, data.respuestas, data.zona)
    perfil["carreras_catalogo"] = holland_filtro.carreras_afines(
        {a["letra"]: a["score"] for a in perfil["areas"]}
    )
    if data.session_id:
        db.add(models.ResultadoHolland(
            session_id=data.session_id,
            estudiante_id=estudiante.id,
            respuestas=data.respuestas,
            codigo=perfil["codigo"],
            areas={a["letra"]: a["score"] for a in perfil["areas"]},
            perfil=_perfil_para_el_chat(perfil),
        ))
        db.commit()
    return perfil


# Los mismos campos que el chat necesita en el prompt (ver holland-perfil.js en
# el frontend). Se guardan aparte de 'areas' porque ahi solo van los numeros y
# los titulos de las ocupaciones tambien entran al prompt.
_OCUPACIONES_EN_PERFIL = 8


def _perfil_para_el_chat(perfil: dict) -> dict:
    return {
        "codigo": perfil["codigo"],
        "areas": [{"letra": a["letra"], "title": a["title"], "score": a["score"]}
                  for a in perfil["areas"]],
        "ocupaciones": [c["title"] for c in perfil.get("carreras", [])[:_OCUPACIONES_EN_PERFIL]],
    }


@app.get("/api/holland/mio")
def holland_mio(
    db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """El ultimo perfil de Holland guardado de ESTE alumno.

    El chat lo recupera desde la cuenta y no desde el localStorage del
    navegador: en un laboratorio, dos alumnos en la misma maquina se estaban
    quedando con el perfil del anterior. Devuelve null si nunca hizo el test."""
    fila = (
        db.query(models.ResultadoHolland)
        .filter(models.ResultadoHolland.estudiante_id == estudiante.id,
                models.ResultadoHolland.perfil.isnot(None))
        .order_by(models.ResultadoHolland.id.desc())
        .first()
    )
    return {**fila.perfil, "fecha": fila.created_at.isoformat()} if fila else None


@app.get("/api/holland/{rid}")
def holland_guardado(
    rid: int, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """El resultado completo de un Holland guardado, tal como se vio al
    terminar el test. Se recalcula desde la cadena de 60 dígitos en vez de
    guardar el perfil entero: así las filas viejas tambien abren completas.

    ponytail: una llamada a O*NET por cada apertura, sin cache. Si pesa,
    guardar el perfil completo en la fila."""
    fila = (
        db.query(models.ResultadoHolland)
        .filter(models.ResultadoHolland.id == rid,
                models.ResultadoHolland.estudiante_id == estudiante.id)
        .first()
    )
    if not fila:
        raise HTTPException(404, "No se encontró ese resultado.")
    perfil = _onet(holland.perfil, fila.respuestas, 4)
    perfil["carreras_catalogo"] = holland_filtro.carreras_afines(
        {a["letra"]: a["score"] for a in perfil["areas"]}
    )
    return perfil


class PersonalidadIn(BaseModel):
    # {id_item: 1..5}, los 48 ítems del test corto (personalidad/valores/estilo).
    respuestas: dict[int, int]
    session_id: SessionId = None  # para guardar el resultado

    @field_validator("respuestas")
    @classmethod
    def _respuestas_ok(cls, v: dict[int, int]) -> dict[int, int]:
        if not personalidad.valida(v):
            raise ValueError("Faltan ítems o hay valores fuera de rango (1 a 5).")
        return v


@app.get("/api/personalidad/preguntas")
def personalidad_preguntas():
    """Los 48 ítems del test corto (personalidad/valores/estilo cognitivo)."""
    return personalidad.preguntas()


@app.post("/api/personalidad")
def personalidad_calificar(
    data: PersonalidadIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(cuota.evaluador),
):
    """Puntajes por rasgo, calculados por reglas (sin llamar a Gemini).

    Se guarda si hay session_id, igual que Holland."""
    puntajes = personalidad.calificar(data.respuestas)
    if data.session_id:
        db.add(models.ResultadoPersonalidad(
            session_id=data.session_id,
            estudiante_id=estudiante.id,
            respuestas={str(k): v for k, v in data.respuestas.items()},
            puntajes=puntajes,
        ))
        db.commit()
    return puntajes


class GoogleAuthIn(BaseModel):
    credential: str  # ID token de Google Identity Services


class EstudianteAuthOut(BaseModel):
    token: str
    estudiante: EstudianteOut


@app.post("/api/auth/google", response_model=EstudianteAuthOut)
def auth_google(data: GoogleAuthIn, db: Session = Depends(get_db)):
    """Login opcional con Google: verifica el ID token, crea o reusa la cuenta
    por su `sub` (estable, a diferencia del email) y devuelve un JWT propio.
    Ver app/auth.py."""
    try:
        datos = auth.verificar_google(data.credential)
    except auth.SinCredencialesGoogle as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o vencido.")

    est = db.query(models.Estudiante).filter(models.Estudiante.google_sub == datos["sub"]).first()
    if est is None:
        # Alguien que ya se había registrado anónimo con el mismo correo: se
        # adopta esa cuenta en vez de crear una duplicada.
        est = db.query(models.Estudiante).filter(models.Estudiante.email == datos["email"]).first() \
            if datos["email"] else None
    if est is None:
        est = models.Estudiante(nombre=datos["name"] or "Sin nombre", email=datos["email"],
                                 google_sub=datos["sub"])
        db.add(est)
    else:
        est.google_sub = datos["sub"]
        if datos["email"]:
            est.email = datos["email"]
    db.commit()
    db.refresh(est)
    return {"token": auth.emitir_jwt(est.id), "estudiante": est}


class ReclamarIn(BaseModel):
    session_id: SessionId = None


@app.post("/api/historial/reclamar", status_code=204)
def historial_reclamar(
    data: ReclamarIn, db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """Le pega el estudiante_id de la sesión logueada a los resultados
    anónimos (sin estudiante_id) de este session_id — el "¿quieres guardar
    tus resultados?" de después del test. El WHERE estudiante_id IS NULL
    evita reclamar un resultado que ya es de otra cuenta."""
    if not data.session_id:
        return
    for modelo in (models.RespuestaCuestionario, models.ResultadoHolland,
                   models.ResultadoPersonalidad, models.ResultadoPsicometrico):
        (
            db.query(modelo)
            .filter(modelo.session_id == data.session_id, modelo.estudiante_id.is_(None))
            .update({"estudiante_id": estudiante.id})
        )
    db.commit()


@app.get("/api/historial")
def historial(
    db: Session = Depends(get_db), estudiante: models.Estudiante = Depends(auth.requiere_login),
):
    """Todo lo que este alumno ha guardado, de los 4 instrumentos, más reciente
    primero. Cada fila trae su `tipo` para que el frontend sepa cómo pintarla."""
    chat = (
        db.query(models.RespuestaCuestionario)
        .filter(models.RespuestaCuestionario.estudiante_id == estudiante.id)
        .order_by(models.RespuestaCuestionario.created_at.desc())
        .all()
    )
    holland_filas = (
        db.query(models.ResultadoHolland)
        .filter(models.ResultadoHolland.estudiante_id == estudiante.id)
        .order_by(models.ResultadoHolland.created_at.desc())
        .all()
    )
    personalidad_filas = (
        db.query(models.ResultadoPersonalidad)
        .filter(models.ResultadoPersonalidad.estudiante_id == estudiante.id)
        .order_by(models.ResultadoPersonalidad.created_at.desc())
        .all()
    )
    psicometrico_filas = (
        db.query(models.ResultadoPsicometrico)
        .filter(models.ResultadoPsicometrico.estudiante_id == estudiante.id)
        .order_by(models.ResultadoPsicometrico.created_at.desc())
        .all()
    )
    return {
        # 'diversificados' se recalcula aquí en vez de guardarse: sale de la
        # recomendación y del nivel, que ya están en la fila, y así una mejora
        # de la tabla se refleja también en el historial viejo.
        "chat": [
            {"id": r.id, "fecha": r.created_at, "respuestas": r.respuestas,
             "recomendacion": r.recomendacion,
             "diversificados": (
                 diversificado.sugerir([c.get("carrera", "") for c in r.recomendacion])
                 if (r.respuestas or {}).get("nivel") == "Básico"
                 and isinstance(r.recomendacion, list) else []
             )}
            for r in chat
        ],
        "holland": [
            {"id": r.id, "fecha": r.created_at, "codigo": r.codigo, "areas": r.areas}
            for r in holland_filas
        ],
        "personalidad": [
            {"id": r.id, "fecha": r.created_at, "puntajes": r.puntajes}
            for r in personalidad_filas
        ],
        "psicometrico": [
            {"id": r.id, "fecha": r.created_at, "puntajes": r.puntajes, "resumen": r.resumen}
            for r in psicometrico_filas
        ],
    }


# Preguntas fijas que se muestran como columnas del registro, en el orden en que
# el chat las hace (ver frontend/src/Chat.jsx).
CAMPOS_REGISTRO = ("nombre", "edad", "nivel", "grado", "carrera_cursada",
                   "gusto_grado", "motivo", "departamento")


# Orden en que se muestran los puntajes RIASEC (el mismo de O*NET).
_LETRAS_RIASEC = ("R", "I", "A", "S", "E", "C")


def _holland_por_evaluacion(db: Session, filas) -> dict[int, dict]:
    """Para cada evaluación del chat, el resultado de Holland del alumno: el del
    MISMO recorrido (mismo session_id) y, si no hay, el más reciente de esa
    cuenta. El psicólogo necesita saber si el alumno ya venía medido y con qué
    puntajes, no solo qué contestó en el chat.

    ponytail: trae todas las filas de Holland de las cuentas involucradas y las
    cruza en memoria. Son cientos de filas; si crece, un LATERAL por session_id.
    """
    sesiones = {f.session_id for f in filas if f.session_id}
    cuentas = {f.estudiante_id for f in filas if f.estudiante_id}
    if not sesiones and not cuentas:
        return {}
    hollands = (
        db.query(models.ResultadoHolland)
        .filter(or_(models.ResultadoHolland.session_id.in_(sesiones or {""}),
                    models.ResultadoHolland.estudiante_id.in_(cuentas or {0})))
        .order_by(models.ResultadoHolland.id)
        .all()
    )
    return _cruza_holland(filas, hollands)


def _cruza_holland(filas, hollands) -> dict[int, dict]:
    """La parte sin base de datos de _holland_por_evaluacion, para poder
    probarla (ver el self-check al final del archivo)."""
    # El id crece con el tiempo, así que la última escritura gana: el más reciente.
    por_sesion = {h.session_id: h for h in hollands}
    por_cuenta = {h.estudiante_id: h for h in hollands if h.estudiante_id}
    # Un alumno puede repetir el test cuantas veces quiera: se cuentan todos y
    # el detalle los lista, pero en el registro se muestra el que corresponde.
    cuantos = Counter(h.estudiante_id for h in hollands if h.estudiante_id)
    salida = {}
    for f in filas:
        h = por_sesion.get(f.session_id) or por_cuenta.get(f.estudiante_id)
        if h is None:
            continue
        salida[f.id] = {**_holland_dict(h, f.session_id),
                        "total": cuantos.get(f.estudiante_id, 1)}
    return salida


def _holland_dict(h, session_id=None) -> dict:
    """Un resultado de Holland como lo consume el frontend."""
    areas = h.areas or {}
    return {
        "codigo": h.codigo,
        "areas": {le: areas.get(le) for le in _LETRAS_RIASEC},
        "fecha": h.created_at,
        # False = lo hizo en otro recorrido, no antes de ESTE chat.
        "mismo_recorrido": bool(session_id) and h.session_id == session_id,
    }


def _holland_historial(db: Session, r) -> list[dict]:
    """Todos los Holland de ese alumno, del más reciente al más viejo. Repetir
    el test es válido y el psicólogo necesita ver cómo se movió el perfil, no
    solo la última foto."""
    if not r.estudiante_id and not r.session_id:
        return []
    filas = (
        db.query(models.ResultadoHolland)
        .filter(or_(models.ResultadoHolland.estudiante_id == r.estudiante_id,
                    models.ResultadoHolland.session_id == r.session_id)
                if r.estudiante_id else
                models.ResultadoHolland.session_id == r.session_id)
        .order_by(models.ResultadoHolland.id.desc())
        .all()
    )
    return [_holland_dict(h, r.session_id) for h in filas]


@app.get("/api/admin/soy")
def admin_soy(estudiante: models.Estudiante | None = Depends(auth.estudiante_actual)):
    """¿La sesión actual es de administración? Lo consulta el menú para decidir
    si muestra el acceso al registro. Nunca lanza 403: responder que no es la
    respuesta correcta para un alumno, no un error."""
    return {"admin": bool(estudiante) and auth.es_admin(estudiante)}


@app.get("/api/admin/respuestas/{respuesta_id}")
def admin_respuesta(
    respuesta_id: int, db: Session = Depends(get_db),
    admin: models.Estudiante = Depends(auth.requiere_admin),
):
    """Una evaluación completa: todo lo que contestó el alumno y todo lo que se
    le recomendó, para que quien aplica el estudio pueda ver su recorrido y su
    dashboard igual que lo vio él. Mismo formato que una fila de
    /api/historial, así el frontend reusa las mismas pantallas."""
    r = db.get(models.RespuestaCuestionario, respuesta_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Esa evaluación no existe.")
    rec = r.recomendacion if isinstance(r.recomendacion, list) else []
    return {
        "id": r.id,
        "fecha": r.created_at,
        "respuestas": r.respuestas,
        "recomendacion": rec,
        "juicio": r.juicio,
        "juicio_nota": r.juicio_nota,
        "diversificados": (
            diversificado.sugerir([c.get("carrera", "") for c in rec])
            if (r.respuestas or {}).get("nivel") == "Básico" else []
        ),
        "cuenta": r.estudiante.email if r.estudiante else None,
        "holland": _holland_por_evaluacion(db, [r]).get(r.id),
        "holland_historial": _holland_historial(db, r),
    }


@app.get("/api/admin/respuestas")
def admin_respuestas(
    db: Session = Depends(get_db),
    admin: models.Estudiante = Depends(auth.requiere_admin),
    limite: int = 500,
):
    """Registro para quien aplica la evaluación: qué contestó cada alumno en las
    preguntas fijas y qué carreras le salieron. Solo para los correos de
    ADMIN_EMAILS (ver app/auth.py).

    Son datos de estudiantes, varios de ellos menores: esta lista no se comparte
    fuera de quienes aplican el estudio y su consentimiento (ver
    docs/estudio-con-estudiantes.md)."""
    filas = (
        db.query(models.RespuestaCuestionario)
        .order_by(models.RespuestaCuestionario.created_at.desc())
        .limit(max(1, min(limite, 2000)))
        .all()
    )
    hollands = _holland_por_evaluacion(db, filas)
    salida = []
    for r in filas:
        resp = r.respuestas or {}
        h = hollands.get(r.id)
        # recomendacion se guarda como la LISTA de carreras (ver /api/recommend).
        rec = r.recomendacion if isinstance(r.recomendacion, list) else []
        salida.append({
            "id": r.id,
            "fecha": r.created_at,
            **{c: resp.get(c) for c in CAMPOS_REGISTRO},
            "carrera_descartada": resp.get("carrera_descartada"),
            "top3": [c.get("carrera") for c in rec[:3]],
            "termino": bool(rec),  # False = abandonó antes de ver resultados
            "juicio": r.juicio,
            "juicio_nota": r.juicio_nota,
            "cuenta": r.estudiante.email if r.estudiante else None,
            "holland": h["codigo"] if h else None,
            "holland_puntajes": (
                " ".join(f"{l}{h['areas'][l]}" for l in _LETRAS_RIASEC
                         if h["areas"].get(l) is not None) if h else None
            ),
            "holland_previo": bool(h) and h["mismo_recorrido"],
            "holland_total": h["total"] if h else 0,
        })
    return salida


class JuicioIn(BaseModel):
    respuesta_id: int
    # Literal en vez de texto libre: es la variable que se va a tabular, y un
    # "Acertó " con espacio o un "si" suelto arruinan el conteo en silencio.
    juicio: Literal["acerto", "parcial", "no_acerto"] | None = None
    nota: str | None = Field(default=None, max_length=4000)


@app.post("/api/admin/juicio", status_code=204)
def admin_juicio(
    data: JuicioIn, db: Session = Depends(get_db),
    admin: models.Estudiante = Depends(auth.requiere_admin),
):
    """Calificación del profesional sobre una evaluación, desde /admin. Es el
    criterio externo de docs/estudio-con-estudiantes.md §4 y se exporta junto
    con el resto de la fila."""
    resp = db.get(models.RespuestaCuestionario, data.respuesta_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Esa evaluación no existe.")
    resp.juicio = data.juicio
    resp.juicio_nota = (data.nota or "").strip() or None
    db.commit()


@app.get("/api/uso-tokens")
def resumen_uso_tokens(db: Session = Depends(get_db)):
    """Resumen para estimar costo/presupuesto: tokens por sesión, total, promedio
    por sesión y desglose por endpoint."""
    por_sesion = (
        db.query(
            models.UsoTokens.session_id,
            func.count(models.UsoTokens.id),
            func.sum(models.UsoTokens.prompt_tokens),
            func.sum(models.UsoTokens.output_tokens),
            func.sum(models.UsoTokens.total_tokens),
            func.sum(models.UsoTokens.cached_tokens),
        )
        .group_by(models.UsoTokens.session_id)
        .all()
    )
    sesiones = [
        {
            "session_id": sid,
            "llamadas": llamadas,
            "prompt_tokens": int(pt or 0),
            "output_tokens": int(ot or 0),
            "total_tokens": int(tt or 0),
            "cached_tokens": int(ct or 0),
        }
        for sid, llamadas, pt, ot, tt, ct in por_sesion
    ]
    por_endpoint = (
        db.query(
            models.UsoTokens.endpoint,
            func.count(models.UsoTokens.id),
            func.sum(models.UsoTokens.total_tokens),
        )
        .group_by(models.UsoTokens.endpoint)
        .all()
    )
    total = sum(s["total_tokens"] for s in sesiones)
    total_prompt = sum(s["prompt_tokens"] for s in sesiones)
    total_cached = sum(s["cached_tokens"] for s in sesiones)
    n = len(sesiones)
    return {
        "num_sesiones": n,
        "total_tokens": total,
        "promedio_tokens_por_sesion": round(total / n) if n else 0,
        # % del prompt que vino del Context Caching (precio ~10% del normal).
        # En 0 si el caché no está activo (tier gratis: ver _get_cache en recomendar.py).
        "pct_prompt_cacheado": round(total_cached / total_prompt * 100, 1) if total_prompt else 0,
        "por_endpoint": [
            {"endpoint": ep, "llamadas": ll, "total_tokens": int(tt or 0)}
            for ep, ll, tt in por_endpoint
        ],
        "sesiones": sesiones,
    }


if __name__ == "__main__":
    # Self-check del cruce de Holland con el registro (sin base de datos).
    from types import SimpleNamespace as N

    ev = [N(id=1, session_id="s1", estudiante_id=7),   # Holland del mismo recorrido
          N(id=2, session_id="s2", estudiante_id=7),   # solo tiene uno viejo, de la cuenta
          N(id=3, session_id="s3", estudiante_id=9)]   # nunca hizo Holland
    hs = [N(id=10, session_id="s0", estudiante_id=7, codigo="ASE",
            areas={"R": 1, "I": 2, "A": 3, "S": 4, "E": 5, "C": 6}, created_at="ayer"),
          N(id=11, session_id="s1", estudiante_id=7, codigo="RIA",
            areas={"R": 9, "I": 8, "A": 7}, created_at="hoy")]
    out = _cruza_holland(ev, hs)
    assert out[1]["codigo"] == "RIA" and out[1]["mismo_recorrido"] is True
    assert out[1]["areas"] == {"R": 9, "I": 8, "A": 7, "S": None, "E": None, "C": None}
    # Sin fila de su recorrido cae a la más reciente de la cuenta (id mayor).
    assert out[2]["codigo"] == "RIA" and out[2]["mismo_recorrido"] is False
    assert out[2]["total"] == 2  # repitió el test: los dos se cuentan
    assert 3 not in out
    print("cruce de Holland: ok")
