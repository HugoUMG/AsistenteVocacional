"""Limites de uso para produccion: cuantos chats puede hacer un alumno por dia
y cuanto puede gastar la app en total.

Son dos, a proposito. El login (app/auth.py) por si solo no protege el credito
de Gemini, crear una cuenta de Google es gratis; y un enfriamiento entre
evaluaciones no aporta nada encima de un techo diario, solo agrega un mensaje
mas que entender y bloquea al alumno que se equivoco y quiere rehacerlo bien.

Se limita **el chat y nada mas**, porque es lo unico que cuesta: el test de
Holland lo califica O*NET, no Gemini, y responder sus 60 items toma un cuarto de
hora, asi que se autolimita solo. Quien lo repita no le hace dano a nadie, y
sigue disponible aunque la app ya haya gastado su presupuesto del dia.

Self-check sin base de datos ni red: uv run python -m app.cuota
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import auth, models
from app.db import get_db

VENTANA_DIARIA = timedelta(hours=24)
# Chats que un mismo alumno puede terminar en 24 horas.
MAX_CHATS_DIARIOS = int(os.getenv("MAX_CHATS_DIARIOS", "3"))
# Suma de tokens de Gemini de TODOS los alumnos en el dia UTC en curso. Medido:
# una sesion completa gasta unos 54,000 tokens, asi que el default alcanza para
# unas 37. Ajustar segun el credito real de la cuenta.
TOPE_TOKENS_DIARIO = int(os.getenv("TOPE_TOKENS_DIARIO", "2000000"))


def chats_recientes(db: Session, estudiante_id: int) -> list[datetime]:
    """Cuando termino cada chat de este alumno en las ultimas 24 horas.

    Solo cuentan los terminados, o sea con recomendacion entregada: al que se le
    cayo el internet a media conversacion no se le gasta un cupo.

    Ventana deslizante, no dia calendario: asi nadie espera al cambio de fecha
    ni junta seis chats a caballo de la medianoche."""
    desde = datetime.now(timezone.utc) - VENTANA_DIARIA
    filas = db.query(models.RespuestaCuestionario.created_at).filter(
        models.RespuestaCuestionario.estudiante_id == estudiante_id,
        models.RespuestaCuestionario.recomendacion.isnot(None),
        models.RespuestaCuestionario.created_at >= desde,
    ).all()
    return [f[0] for f in filas]


def espera_por_tope(fechas: list[datetime], ahora: datetime | None = None,
                    maximo: int | None = None) -> timedelta:
    """Cuanto falta para que se libere un cupo. timedelta(0) = todavia le quedan.

    El cupo se libera cuando el chat que lo ocupa sale de la ventana. Si hay mas
    registros que cupos (porque el limite bajo), se mira el que corresponde al
    cupo, no el mas viejo de todos."""
    maximo = MAX_CHATS_DIARIOS if maximo is None else maximo
    if maximo <= 0 or len(fechas) < maximo:
        return timedelta(0)
    ahora = ahora or datetime.now(timezone.utc)
    libera = sorted(fechas)[len(fechas) - maximo] + VENTANA_DIARIA
    return max(timedelta(0), libera - ahora)


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


def revisar_tope_diario(db: Session, estudiante: models.Estudiante) -> None:
    falta = espera_por_tope(chats_recientes(db, estudiante.id))
    if falta:
        raise HTTPException(
            status_code=429,
            detail=f"Ya hiciste {MAX_CHATS_DIARIOS} chats con Orienta en las últimas "
                   f"24 horas. Vas a poder hacer otro en {legible(falta)}. Mientras "
                   f"tanto podés revisar tus resultados en 'Mi historial', o hacer el "
                   f"test de Holland, que no tiene límite.",
            headers={"Retry-After": str(int(falta.total_seconds()))},
        )


def tokens_de_hoy(db: Session) -> int:
    inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(func.coalesce(func.sum(models.UsoTokens.total_tokens), 0)).filter(
        models.UsoTokens.created_at >= inicio
    ).scalar() or 0


def revisar_tope_global(db: Session) -> None:
    # ponytail: se consulta la suma del dia en cada llamada, sin cache. Son
    # milisegundos contra un indice; si algun dia la tabla pesa, se cachea el
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
    """Dependencia de todo endpoint que gasta Gemini: exige sesion iniciada y
    respeta el tope global del dia. Lo que no gasta Gemini (Holland) no pasa por
    aqui: no tiene por que caerse cuando se acaba el presupuesto."""
    revisar_tope_global(db)
    return estudiante


def _self_check():
    ahora = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    tres = [ahora - timedelta(hours=h) for h in (20, 10, 2)]

    assert espera_por_tope([], ahora) == timedelta(0)
    assert espera_por_tope(tres[:2], ahora) == timedelta(0)  # le queda uno
    assert espera_por_tope(tres, ahora) == timedelta(hours=4)  # el de hace 20h libera a las 24
    # Con mas registros que cupos, libera el que ocupa el cupo, no el mas viejo.
    assert espera_por_tope([ahora - timedelta(hours=23)] + tres, ahora) == timedelta(hours=4)
    # Los que ya salieron de la ventana no ocupan cupo.
    assert espera_por_tope([ahora - timedelta(hours=30)] * 5, ahora, maximo=3) == timedelta(0)
    assert espera_por_tope(tres, ahora, maximo=0) == timedelta(0)  # tope apagado
    # Un reloj torcido no debe dar una espera negativa.
    assert espera_por_tope([ahora + timedelta(days=1)] * 3, ahora) > timedelta(0)

    assert legible(timedelta(hours=3, minutes=12)) == "3 horas y 12 minutos"
    assert legible(timedelta(hours=1)) == "1 hora"
    assert legible(timedelta(minutes=45)) == "45 minutos"
    assert legible(timedelta(seconds=20)) == "1 minuto"  # nunca "0 minutos"

    print("cuota self-check OK: tope de chats y mensajes, sin base de datos")


if __name__ == "__main__":
    _self_check()
