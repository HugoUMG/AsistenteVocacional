"""Límites de uso para producción: un enfriamiento por alumno entre
evaluaciones y un tope global de tokens por día.

Por qué existe: el login (app/auth.py) por sí solo NO protege el crédito de
Gemini, crear una cuenta de Google es gratis y toma dos minutos. Lo que de
verdad lo protege es esto: el enfriamiento corta al alumno que repite el test
muchas veces seguidas, y el tope diario es el freno de emergencia si algo se
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

MINUTOS_ENFRIAMIENTO = float(os.getenv("MINUTOS_ENFRIAMIENTO", "10"))
# Evaluaciones que un mismo alumno puede terminar en 24 horas, sumando todos los
# instrumentos. El enfriamiento corta la repeticion inmediata; esto corta la
# insistencia a lo largo del dia, que es la que se come el presupuesto.
MAX_EVALUACIONES_DIARIAS = int(os.getenv("MAX_EVALUACIONES_DIARIAS", "3"))
# Suma de tokens de Gemini de TODOS los alumnos en el día UTC en curso. El
# default alcanza para unas 37 evaluaciones completas, medidas en 54,000
# tokens cada una; ajustar en backend/.env
# según el crédito real (ver decisions/gemini-costos-y-caching.md).
TOPE_TOKENS_DIARIO = int(os.getenv("TOPE_TOKENS_DIARIO", "2000000"))


VENTANA_DIARIA = timedelta(hours=24)


def evaluaciones_recientes(db: Session, estudiante_id: int) -> list[datetime]:
    """Cuando termino cada RECORRIDO de este alumno en las ultimas 24 horas.

    Un recorrido, no una llamada ni un instrumento: el `session_id` acompana al
    alumno desde el test de Holland hasta el chat y el dashboard, y solo cambia
    cuando elige empezar otra prueba (ver frontend/src/session.js). Por eso
    "Holland y luego el chat" cuenta como UNA evaluacion, que es como lo vive el
    alumno, mientras que hacer Holland hoy y volver manana por el chat cuenta
    como dos.

    Ventana deslizante, no dia calendario: asi nadie espera al cambio de fecha
    ni junta seis evaluaciones a caballo de la medianoche."""
    desde = datetime.now(timezone.utc) - VENTANA_DIARIA
    chats = db.query(
        models.RespuestaCuestionario.id, models.RespuestaCuestionario.session_id,
        models.RespuestaCuestionario.created_at,
    ).filter(
        models.RespuestaCuestionario.estudiante_id == estudiante_id,
        models.RespuestaCuestionario.recomendacion.isnot(None),
        models.RespuestaCuestionario.created_at >= desde,
    ).all()
    holland = db.query(
        models.ResultadoHolland.id, models.ResultadoHolland.session_id,
        models.ResultadoHolland.created_at,
    ).filter(
        models.ResultadoHolland.estudiante_id == estudiante_id,
        models.ResultadoHolland.created_at >= desde,
    ).all()

    return agrupar_recorridos((("chat", chats), ("holland", holland)))


def agrupar_recorridos(grupos) -> list[datetime]:
    """De filas (id, session_id, created_at) a una fecha por recorrido: la de lo
    ultimo que el alumno hizo en el. Las filas que comparten `session_id`
    colapsan en una sola; sin session_id (filas viejas), cada una cuenta por su
    cuenta, que es la lectura conservadora."""
    recorridos: dict[str, datetime] = {}
    for tabla, filas in grupos:
        for fila_id, sesion, cuando in filas:
            clave = sesion or f"{tabla}-{fila_id}"
            anterior = recorridos.get(clave)
            if anterior is None or cuando > anterior:
                recorridos[clave] = cuando
    return list(recorridos.values())


def espera_por_tope(fechas: list[datetime], ahora: datetime | None = None,
                    maximo: int | None = None) -> timedelta:
    """Cuanto falta para que se libere un cupo. timedelta(0) = todavia le quedan.

    El cupo se libera cuando la evaluacion que lo ocupa sale de la ventana. Si
    hay mas registros que cupos (porque el limite bajo), se mira la que
    corresponde al cupo, no la mas vieja de todas."""
    maximo = MAX_EVALUACIONES_DIARIAS if maximo is None else maximo
    if maximo <= 0 or len(fechas) < maximo:
        return timedelta(0)
    ahora = ahora or datetime.now(timezone.utc)
    libera = sorted(fechas)[len(fechas) - maximo] + VENTANA_DIARIA
    return max(timedelta(0), libera - ahora)


def revisar_tope_diario(db: Session, estudiante: models.Estudiante) -> None:
    falta = espera_por_tope(evaluaciones_recientes(db, estudiante.id))
    if falta:
        raise HTTPException(
            status_code=429,
            detail=f"Ya completaste {MAX_EVALUACIONES_DIARIAS} evaluaciones en las "
                   f"ultimas 24 horas. Vas a poder hacer otra en {legible(falta)}. "
                   f"Tus resultados siguen en 'Mi historial'.",
            headers={"Retry-After": str(int(falta.total_seconds()))},
        )


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
    return max(timedelta(0), ultima + timedelta(minutes=MINUTOS_ENFRIAMIENTO) - ahora)


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

    espera = timedelta(minutes=MINUTOS_ENFRIAMIENTO)
    assert espera_restante(None, ahora) == timedelta(0)  # nunca evaluó
    assert espera_restante(ahora - espera * 2, ahora) == timedelta(0)  # ya pasó
    assert espera_restante(ahora - espera, ahora) == timedelta(0)  # justo en el borde
    assert espera_restante(ahora, ahora) == espera
    assert espera_restante(ahora - espera / 2, ahora) == espera / 2
    # Una fecha futura (reloj torcido) no debe dar una espera negativa.
    assert espera_restante(ahora + timedelta(days=1), ahora) > timedelta(0)

    # Un recorrido = un session_id: Holland y el chat de la misma sesion cuentan
    # una sola vez, y eso es lo que hace que el modo "test y luego chat" no
    # consuma dos cupos.
    t1, t2 = ahora - timedelta(hours=2), ahora - timedelta(hours=1)
    mezcla = (("chat", [(1, "s-A", t2)]), ("holland", [(9, "s-A", t1)]))
    assert agrupar_recorridos(mezcla) == [t2], "Holland + chat de una sesion son un recorrido"
    dos = (("chat", [(1, "s-A", t2)]), ("holland", [(9, "s-B", t1)]))
    assert sorted(agrupar_recorridos(dos)) == sorted([t2, t1]), "sesiones distintas, dos recorridos"
    # Sin session_id cada fila cuenta aparte, y no colisionan entre tablas.
    sin_id = (("chat", [(1, None, t1)]), ("holland", [(1, None, t2)]))
    assert len(agrupar_recorridos(sin_id)) == 2

    # Tope de 3 evaluaciones cada 24 horas.
    tres = [ahora - timedelta(hours=h) for h in (20, 10, 2)]
    assert espera_por_tope([], ahora) == timedelta(0)
    assert espera_por_tope(tres[:2], ahora) == timedelta(0)  # le queda una
    assert espera_por_tope(tres, ahora) == timedelta(hours=4)  # la de hace 20h libera a las 24
    # Con mas registros que cupos, libera el que ocupa el cupo, no el mas viejo.
    assert espera_por_tope([ahora - timedelta(hours=23)] + tres, ahora) == timedelta(hours=4)
    # Ninguna dentro de la ventana: las viejas no ocupan cupo.
    assert espera_por_tope([ahora - timedelta(hours=30)] * 5, ahora, maximo=3) == timedelta(0)
    assert espera_por_tope(tres, ahora, maximo=0) == timedelta(0)  # tope apagado

    assert legible(timedelta(hours=3, minutes=12)) == "3 horas y 12 minutos"
    assert legible(timedelta(hours=1)) == "1 hora"
    assert legible(timedelta(minutes=45)) == "45 minutos"
    assert legible(timedelta(seconds=20)) == "1 minuto"  # nunca "0 minutos"

    print("cuota self-check OK: enfriamiento, tope diario y mensajes, sin base de datos")


if __name__ == "__main__":
    _self_check()
