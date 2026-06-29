from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app import models, recomendar


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


@app.post("/api/recommend")
def recommend(data: SurveyIn, db: Session = Depends(get_db)):
    if not recomendar.hay_api_key():
        raise HTTPException(
            status_code=503,
            detail="Falta configurar GEMINI_API_KEY en el backend.",
        )
    carreras = db.query(models.Carrera).all()
    if not carreras:
        raise HTTPException(status_code=409, detail="No hay carreras en el catálogo.")
    recs = recomendar.recomendar(data.respuestas, carreras)
    return {"carreras": [r.model_dump() for r in recs]}
