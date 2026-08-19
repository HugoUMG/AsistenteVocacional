"""Límites de uso para producción: un enfriamiento por alumno entre
evaluaciones y un tope global de tokens por día.

Por qué existe: el login (app/auth.py) por sí solo NO protege el crédito de
Gemini, crear una cuenta de Google es gratis y toma dos minutos. Lo que de
verdad lo protege es esto: el enfriamiento corta al alumno que repite el test
diez veces en una hora, y el tope diario es el freno de emergencia si algo se
sale de control (un curso entero entrando el mismo día, un script, un bug).

El enfriamiento es POR INSTRUMENTO (el chat por su lado, Holland por el suyo)
a propósito: en el modo 3 el alumno hace Holland y pasa al chat de inmediato,
y un enfriamiento compartido lo dejaría encerrado en su propia sesión.

Self-check sin base de datos ni red: uv run python -m app.cuota
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import auth, models
from app.db import get_db

HORAS_ENFRIAMIENTO = float(os.getenv("HORAS_ENFRIAMIENTO", "4"))
# Suma de tokens de Gemini de TODOS los alumnos en el día UTC en curso. El
# default alcanza para ~200 evaluaciones completas; ajustar en backend/.env
# según el crédito real (ver decisions/gemini-costos-y-caching.md).
TOPE_TOKENS_DIARIO = int(os.getenv("TOPE_TOKENS_DIARIO", "2000000"))


def ultima_evaluacion(db: Session, estudiante_id: int, instrumento: str) -> datetime | None:
    """Cuándo TERMINÓ la última evaluación de este alumno con ese instrumento.

    Solo cuentan las terminadas: un chat con recomendación entregada, un Holland
    calificado. Las que quedaron a medias (se cayó el internet, cerró la
    pestaña) no encierran a nadie durante cuatro horas."""
    if instrumento == "holland":
        q = db.query(func.max(models.ResultadoHolland.created_at)).filter(
            models.ResultadoHolland.estudiante_id == estudiante_id
        )
    else:
        q = db.query(func.max(models.RespuestaCuestionario.created_at)).filter(
            models.RespuestaCuestionario.estudiante_id == estudiante_id,
            models.RespuestaCuestionario.recomendacion.isnot(None),
        )
    return q.scalar()


def espera_restante(ultima: datetime | None, ahora: datetime | None = None) -> timedelta:
    """Cuánto falta para poder volver a evaluar. timedelta(0) = ya puede."""
    if ultima is None:
        return timedelta(0)
    ahora = ahora or datetime.now(timezone.utc)
    return max(timedelta(0), ultima + timedelta(hours=HORAS_ENFRIAMIENTO) - ahora)


def legible(falta: timedelta) -> str:
    """'3 horas y 12 minutos', para el mensaje que ve el alumno."""
    minutos = max(1, round(falta.total_seconds() / 60))
    horas, minutos = divmod(minutos, 60)
    partes = []
    if horas:
        partes.append(f"{horas} hora" + ("s" if horas != 1 else ""))
    if minutos:
        partes.append(f"{minutos} minuto" + ("s" if minutos != 1 else ""))
    return " y ".join(partes)


def revisar_enfriamiento(db: Session, estudiante: models.Estudiante, instrumento: str) -> None:
    falta = espera_restante(ultima_evaluacion(db, estudiante.id, instrumento))
    if falta:
        raise HTTPException(
            status_code=429,
            detail=f"Ya completaste una evaluación hace poco. Vas a poder hacer "
                   f"otra en {legible(falta)}. Mientras tanto podés revisar tus "
                   f"resultados en 'Mi historial'.",
            headers={"Retry-After": str(int(falta.total_seconds()))},
        )


def tokens_de_hoy(db: Session) -> int:
    inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(func.coalesce(func.sum(models.UsoTokens.total_tokens), 0)).filter(
        models.UsoTokens.created_at >= inicio
    ).scalar() or 0


def revisar_tope_global(db: Session) -> None:
    # ponytail: se consulta la suma del día en cada llamada, sin caché. Son
    # milisegundos contra un índice; si algún día la tabla pesa, se cachea el
    # total en memoria por un minuto.
    if tokens_de_hoy(db) >= TOPE_TOKENS_DIARIO:
        raise HTTPException(
            status_code=429,
            detail="El asistente alcanzó su límite de uso por hoy. Volvé a "
                   "intentarlo mañana.",
        )


def evaluador(
    db: Session = Depends(get_db),
    estudiante: models.Estudiante = Depends(auth.requiere_login),
) -> models.Estudiante:
    """Dependencia de todo endpoint que gasta Gemini o califica un test:
    exige sesión iniciada y respeta el tope global del día."""
    revisar_tope_global(db)
    return estudiante


def _self_check():
    ahora = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

    assert espera_restante(None, ahora) == timedelta(0)  # nunca evaluó
    assert espera_restante(ahora - timedelta(hours=5), ahora) == timedelta(0)  # ya pasó
    assert espera_restante(ahora - timedelta(hours=4), ahora) == timedelta(0)  # justo en el borde
    assert espera_restante(ahora, ahora) == timedelta(hours=HORAS_ENFRIAMIENTO)
    assert espera_restante(ahora - timedelta(hours=1), ahora) == timedelta(hours=3)
    # Una fecha futura (reloj torcido) no debe dar una espera negativa.
    assert espera_restante(ahora + timedelta(days=1), ahora) > timedelta(0)

    assert legible(timedelta(hours=3, minutes=12)) == "3 horas y 12 minutos"
    assert legible(timedelta(hours=1)) == "1 hora"
    assert legible(timedelta(minutes=45)) == "45 minutos"
    assert legible(timedelta(seconds=20)) == "1 minuto"  # nunca "0 minutos"

    print("cuota self-check OK — enfriamiento y mensajes, sin base de datos")


if __name__ == "__main__":
    _self_check()
