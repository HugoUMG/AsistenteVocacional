from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app import models, recomendar, preguntas, extras


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ponytail: create_all en arranque en vez de migraciones. Cambiar a Alembic
    # cuando el esquema empiece a evolucionar con datos reales que conservar.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Recomendador Vocacional API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas (validación en la frontera: datos del navegador) ---
class RegisterIn(BaseModel):
    nombre: str
    email: EmailStr | None = None


class EstudianteOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr | None = None

    model_config = {"from_attributes": True}


class SurveyIn(BaseModel):
    estudiante_id: int
    respuestas: dict
    session_id: str | None = None  # para atribuir el uso de tokens a la sesión


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


class NextIn(BaseModel):
    respuestas: dict
    session_id: str | None = None


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
    return {
        "carreras": [
            {
                "nombre": c.nombre,
                "universidad": c.universidad,
                "centro": c.centro,
                "departamento": c.departamento,
            }
            for c in rows
        ]
    }


def _carreras(db, respuestas):
    """Carreras filtradas por el departamento elegido. 'Ambos' = sin filtro."""
    q = db.query(models.Carrera)
    depto = (respuestas or {}).get("departamento")
    if depto and depto != "Ambos":
        q = q.filter(models.Carrera.departamento == depto)
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
    paso, uso = preguntas.siguiente_pregunta(data.respuestas, carreras)
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
    session_id: str | None = None


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
    session_id: str | None = None


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
