from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now():
    return datetime.now(timezone.utc)


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    # email opcional: el chatbot solo pide el nombre. Se puede capturar luego.
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    respuestas: Mapped[list["RespuestaCuestionario"]] = relationship(
        back_populates="estudiante"
    )


class Carrera(Base):
    __tablename__ = "carreras"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    departamento: Mapped[str] = mapped_column(String(60), index=True)  # ej. Totonicapán
    centro: Mapped[str] = mapped_column(String(60), index=True)  # ej. CUNTOTO
    universidad: Mapped[str] = mapped_column(String(120))
    # perfil: el "banco de palabras" vocacional (afinidades, habilidades,
    # entorno, gustos, estilo cognitivo). La IA lo lee como texto.
    perfil: Mapped[str] = mapped_column(Text)


class RespuestaCuestionario(Base):
    __tablename__ = "respuestas_cuestionario"

    id: Mapped[int] = mapped_column(primary_key=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("estudiantes.id"))
    # ponytail: respuestas como JSON. El cuestionario aún no está fijo; cuando lo esté,
    # se puede normalizar a columnas/tabla aparte si se necesita consultar por respuesta.
    respuestas: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # resultado de /api/recommend, guardado para poder evaluar precisión luego.
    recomendacion: Mapped[dict | None] = mapped_column(JSON, default=None)
    # feedback del alumno: True = le pareció acertada, False = no, None = sin responder.
    feedback: Mapped[bool | None] = mapped_column(default=None)

    estudiante: Mapped["Estudiante"] = relationship(back_populates="respuestas")
