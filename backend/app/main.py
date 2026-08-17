import re
import unicodedata
from contextlib import asynccontextmanager
from typing import Annotated

import edge_tts
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app import models, recomendar, preguntas, extras, psicometrico, cip_fogliatto, holland


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: create_all en arranque en vez de migraciones. Cambiar a Alembic
    # cuando el esquema empiece a evolucionar con datos reales que conservar.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Recomendador Vocacional API", version="0.1.0", lifespan=lifespan)


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


class SurveyIn(BaseModel):
    estudiante_id: int
    respuestas: dict
    session_id: SessionId = None  # para atribuir el uso de tokens a la sesión


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
def register(data: RegisterIn, db: Session = Depends(get_db)):
    est = models.Estudiante(nombre=data.nombre, email=data.email)
    db.add(est)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El email ya está registrado")
    db.refresh(est)
    return est


@app.post("/api/submit-survey", response_model=SurveyOut, status_code=201)
def submit_survey(data: SurveyIn, db: Session = Depends(get_db)):
    if db.get(models.Estudiante, data.estudiante_id) is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    resp = models.RespuestaCuestionario(
        estudiante_id=data.estudiante_id, respuestas=data.respuestas
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
    coma) elegido. 'Ambos' = sin filtro."""
    q = db.query(models.Carrera)
    depto = (respuestas or {}).get("departamento")
    if depto and depto != "Ambos":
        deptos = [d.strip() for d in depto.split(",")]
        q = q.filter(models.Carrera.departamento.in_(deptos))
    carreras = q.all()
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
def next_question(data: NextIn, db: Session = Depends(get_db)):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    carreras = _carreras(db, data.respuestas)
    paso, uso = preguntas.siguiente_pregunta(data.respuestas, carreras, data.session_id)
    _registrar_uso(db, data.session_id, "next-question", uso)
    return paso.model_dump()


@app.post("/api/recommend")
def recommend(data: SurveyIn, db: Session = Depends(get_db)):
    if not recomendar.hay_api_key():
        raise HTTPException(
            status_code=503,
            detail="Falta configurar GEMINI_API_KEY en el backend.",
        )
    carreras = _carreras(db, data.respuestas)
    resultado, uso = recomendar.recomendar(data.respuestas, carreras)
    _registrar_uso(db, data.session_id, "recommend", uso)
    carreras_out = [r.model_dump() for r in resultado.carreras]

    # Guarda la recomendación en el registro más reciente de este alumno,
    # para poder cruzarla luego con el feedback y medir precisión.
    respuesta_id = None
    resp = (
        db.query(models.RespuestaCuestionario)
        .filter(models.RespuestaCuestionario.estudiante_id == data.estudiante_id)
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
    }


class SimularIn(BaseModel):
    carrera: str
    descripcion: str
    respuestas: dict
    session_id: SessionId = None


@app.post("/api/simular-dia")
def simular_dia(data: SimularIn, db: Session = Depends(get_db)):
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
def comparar(data: CompararIn, db: Session = Depends(get_db)):
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
def psicometrico_calificar(data: PsicometricoIn, db: Session = Depends(get_db)):
    puntajes = psicometrico.calificar(data.respuestas, data.tiempos)
    fila = models.ResultadoPsicometrico(
        session_id=data.session_id or "sin-sesion",
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
def cip_calificar(data: CipIn):
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
def holland_perfil(data: HollandIn):
    """Puntajes RIASEC y carreras afines. El cálculo lo hace la API oficial.

    ponytail: no guarda nada en la base de datos, igual que el CIP. Si el test se
    va a usar en la investigación, se agrega una tabla como `resultados_psicometricos`.
    """
    return _onet(holland.perfil, data.respuestas, data.zona)


class FeedbackIn(BaseModel):
    respuesta_id: int
    acertada: bool


@app.post("/api/feedback", status_code=204)
def feedback(data: FeedbackIn, db: Session = Depends(get_db)):
    resp = db.get(models.RespuestaCuestionario, data.respuesta_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    resp.feedback = data.acertada
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
