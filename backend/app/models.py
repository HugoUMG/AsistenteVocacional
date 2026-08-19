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
    # id estable de Google ("sub" del token) para el login opcional (ver
    # app/auth.py): el email puede cambiar, el sub no. NULL = cuenta anónima
    # (nunca inició sesión con Google), que sigue siendo el caso normal.
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
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
    # Para "guardar resultados" después de un chat anónimo (ver app/auth.py):
    # el session_id ya viaja desde el navegador, esto solo lo persiste. NULL
    # en filas viejas (antes de esta columna) o si nunca se manda.
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    # ponytail: respuestas como JSON. El cuestionario aún no está fijo; cuando lo esté,
    # se puede normalizar a columnas/tabla aparte si se necesita consultar por respuesta.
    respuestas: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # resultado de /api/recommend, guardado para poder evaluar precisión luego.
    recomendacion: Mapped[dict | None] = mapped_column(JSON, default=None)
    # feedback del alumno: True = le pareció acertada, False = no, None = sin responder.
    feedback: Mapped[bool | None] = mapped_column(default=None)

    estudiante: Mapped["Estudiante"] = relationship(back_populates="respuestas")


class ResultadoPsicometrico(Base):
    """Examen psicométrico de 100 ítems (pestaña aparte del chat vocacional).
    Guarda las respuestas crudas, los puntajes calculados y el resumen de la IA."""

    __tablename__ = "resultados_psicometricos"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    # NULL = anónimo (el caso normal). Se llena al calificar si hay sesión, o
    # después vía /api/historial/reclamar si el login llega tarde.
    estudiante_id: Mapped[int | None] = mapped_column(ForeignKey("estudiantes.id"), index=True, default=None)
    # {id_item: valor}. Personalidad = 1..5 (escala Likert); resto = índice de opción.
    respuestas: Mapped[dict] = mapped_column(JSON)
    puntajes: Mapped[dict] = mapped_column(JSON)
    resumen: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ResultadoHolland(Base):
    """Test de intereses de Holland (O*NET Interest Profiler).

    Se guarda al calificar, aunque el alumno no siga al chat: es el instrumento
    avalado del proyecto y sus resultados entran en la investigación. Los
    puntajes los calcula O*NET, no este backend (ver docs/holland.md)."""

    __tablename__ = "resultados_holland"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    estudiante_id: Mapped[int | None] = mapped_column(ForeignKey("estudiantes.id"), index=True, default=None)
    # Los 60 dígitos 1-5 tal como se mandaron a O*NET, por si hay que recalificar.
    respuestas: Mapped[str] = mapped_column(String(60))
    codigo: Mapped[str] = mapped_column(String(3))  # p. ej. "ASC"
    areas: Mapped[dict] = mapped_column(JSON)  # {"R": 12, "I": 10, ...}
    # El perfil completo tal como lo consume el chat (codigo, areas con su
    # nombre y puntaje, y los titulos de las ocupaciones). Se guarda porque
    # 'areas' solo tiene los numeros y las ocupaciones SI entran al prompt:
    # sin esto, recuperar el perfil desde la base degrada el prompt en
    # silencio. NULL en filas anteriores a esta columna.
    perfil: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ResultadoPersonalidad(Base):
    """Test corto de personalidad/valores/estilo cognitivo (pre-chat, opcional).

    Se guarda al calificar, igual que Holland: no llama a Gemini, el cálculo
    es por reglas (ver app/personalidad.py)."""

    __tablename__ = "resultados_personalidad"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    estudiante_id: Mapped[int | None] = mapped_column(ForeignKey("estudiantes.id"), index=True, default=None)
    respuestas: Mapped[dict] = mapped_column(JSON)  # {id_item: 1..5}
    puntajes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
    # De prompt_tokens, cuántos vinieron del Context Caching (facturados a ~10%
    # del precio normal) en vez de mandados de nuevo en cada llamada. Requiere
    # billing habilitado (el tier gratis no permite almacenamiento de caché);
    # mientras tanto queda en 0 y todo el prompt se factura a precio normal.
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
