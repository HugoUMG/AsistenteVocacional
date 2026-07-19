from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
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
    # Cuando la MISMA carrera la ofrecen varias sedes, comparten perfil_grupo
    # (p. ej. "ciencias_juridicas") y el perfil viene de data/perfiles_compartidos.json
    # en vez de repetirse por sede. 'sello' es lo que SÍ distingue a esta sede (1-2
    # frases). Ambos None para carreras de una sola sede (sin cambio de comportamiento).
    perfil_grupo: Mapped[str | None] = mapped_column(String(80), index=True, default=None)
    sello: Mapped[str | None] = mapped_column(Text, default=None)


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


class UsoTokens(Base):
    """Log de consumo de tokens por CADA llamada a Gemini, para estimar costo y
    presupuesto. El total por sesión = SUMA de total_tokens agrupando por
    session_id (el frontend manda un session_id por test)."""

    __tablename__ = "uso_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    endpoint: Mapped[str] = mapped_column(String(40))  # next-question | recommend | simular-dia | comparar
    modelo: Mapped[str] = mapped_column(String(60))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
