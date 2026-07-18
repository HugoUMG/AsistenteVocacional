from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
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


@app.get("/api/departamentos")
def departamentos(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Carrera.departamento)
        .distinct()
        .order_by(models.Carrera.departamento)
        .all()
    )
    return {"departamentos": [r[0] for r in rows]}


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


@app.post("/api/next-question")
def next_question(data: NextIn, db: Session = Depends(get_db)):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    carreras = _carreras(db, data.respuestas)
    return preguntas.siguiente_pregunta(data.respuestas, carreras).model_dump()


@app.post("/api/recommend")
def recommend(data: SurveyIn, db: Session = Depends(get_db)):
    if not recomendar.hay_api_key():
        raise HTTPException(
            status_code=503,
            detail="Falta configurar GEMINI_API_KEY en el backend.",
        )
    carreras = _carreras(db, data.respuestas)
    resultado = recomendar.recomendar(data.respuestas, carreras)
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


@app.post("/api/simular-dia")
def simular_dia(data: SimularIn):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    return extras.simular_dia(data.carrera, data.descripcion, data.respuestas).model_dump()


class CompararIn(BaseModel):
    carrera_a: str
    descripcion_a: str
    carrera_b: str
    descripcion_b: str
    respuestas: dict


@app.post("/api/comparar")
def comparar(data: CompararIn):
    if not recomendar.hay_api_key():
        raise HTTPException(status_code=503, detail="Falta configurar GEMINI_API_KEY en el backend.")
    return extras.comparar_carreras(
        data.carrera_a, data.descripcion_a,
        data.carrera_b, data.descripcion_b,
        data.respuestas,
    ).model_dump()


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
