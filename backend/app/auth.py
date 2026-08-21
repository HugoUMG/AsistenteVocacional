"""Login con Google: identifica al estudiante entre visitas y sostiene su
historial (`/api/historial`). Iniciar sesión es obligatorio para evaluarse: sin
cuenta no hay a quién aplicarle el enfriamiento entre evaluaciones ni el tope de
uso (ver app/cuota.py).

Flujo: el frontend obtiene un ID token de Google (Google Identity Services) y
lo manda a `POST /api/auth/google`. Este módulo lo verifica contra
GOOGLE_CLIENT_ID y emite un JWT PROPIO (HS256, firmado con SESSION_SECRET)
que el frontend guarda y reenvía como `Authorization: Bearer <token>`. No se
usa el ID token de Google como sesión: expira rápido (~1h) y no es lo que
Google recomienda para sesiones largas.

Self-check sin red: uv run python -m app.auth
"""

import os
import time

import jwt
from fastapi import Depends, Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

ALGORITMO = "HS256"
# 90 días: es un JWT de "recuérdame" para un alumno que vuelve a ver su
# historial, no una sesión de operaciones sensibles.
DIAS_EXPIRACION = 90


class SinCredencialesGoogle(RuntimeError):
    pass


def verificar_google(id_token_str: str) -> dict:
    """Verifica un ID token de Google Identity Services contra GOOGLE_CLIENT_ID.
    Devuelve {sub, email, name}. Lanza ValueError si el token es inválido
    (expirado, firma mala, o de otro client id)."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise SinCredencialesGoogle(
            "Falta GOOGLE_CLIENT_ID en backend/.env. Se crea gratis en "
            "console.cloud.google.com > APIs & Services > Credentials."
        )
    datos = google_id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)
    return {"sub": datos["sub"], "email": datos.get("email"), "name": datos.get("name", "")}


def _secreto() -> str:
    s = os.getenv("SESSION_SECRET")
    if not s:
        raise SinCredencialesGoogle("Falta SESSION_SECRET en backend/.env.")
    return s


def emitir_jwt(estudiante_id: int) -> str:
    ahora = int(time.time())
    return jwt.encode(
        # "sub" viaja como string: PyJWT exige ese tipo si el claim está presente.
        {"sub": str(estudiante_id), "iat": ahora, "exp": ahora + DIAS_EXPIRACION * 86400},
        _secreto(),
        algorithm=ALGORITMO,
    )


def decodificar_jwt(token: str) -> int | None:
    """Devuelve el estudiante_id del token, o None si es inválido/expirado.
    No lanza: quien llama decide si eso es un 401 o simplemente "sin sesión"."""
    try:
        datos = jwt.decode(token, _secreto(), algorithms=[ALGORITMO])
        return int(datos["sub"])
    except (jwt.PyJWTError, SinCredencialesGoogle, KeyError, ValueError):
        return None


def _token_de_header(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def estudiante_actual(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> models.Estudiante | None:
    """Dependencia OPCIONAL: no lanza 401 si no hay sesión, para que los
    endpoints existentes sigan funcionando sin login (registro anónimo)."""
    token = _token_de_header(authorization)
    if not token:
        return None
    eid = decodificar_jwt(token)
    return db.get(models.Estudiante, eid) if eid else None


def requiere_login(
    estudiante: models.Estudiante | None = Depends(estudiante_actual),
) -> models.Estudiante:
    """Para endpoints que SÍ necesitan sesión (ej. /api/historial)."""
    if estudiante is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para ver tu historial.")
    return estudiante


def _admins() -> set[str]:
    """Correos con acceso al registro de administración (ADMIN_EMAILS en
    backend/.env, separados por coma). Vacío = nadie entra, que es el default
    seguro: en un despliegue sin la variable la sección queda cerrada."""
    return {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}


def es_admin(estudiante: models.Estudiante) -> bool:
    return (estudiante.email or "").lower() in _admins()


def requiere_admin(
    estudiante: models.Estudiante = Depends(requiere_login),
) -> models.Estudiante:
    """Para el registro de quienes aplican la evaluación (/api/admin/...).
    Se apoya en el login de Google: el correo lo verifica Google, no el usuario.

    ponytail: lista de correos en el .env, no una tabla de roles. Son dos o tres
    personas; si algún día hay que dar y quitar accesos desde la app, ahí sí
    toca una tabla."""
    if not es_admin(estudiante):
        raise HTTPException(status_code=403, detail="Esta sección es solo para administradores.")
    return estudiante


def _self_check():
    os.environ["SESSION_SECRET"] = "clave-de-prueba-no-usar-en-produccion"

    token = emitir_jwt(42)
    assert decodificar_jwt(token) == 42

    assert decodificar_jwt("esto-no-es-un-jwt") is None
    assert decodificar_jwt(token + "x") is None  # firma corrupta

    # Un token firmado con OTRA clave no debe validar con la actual.
    ajeno = jwt.encode({"sub": 1, "iat": 0, "exp": 9999999999}, "otra-clave", algorithm=ALGORITMO)
    assert decodificar_jwt(ajeno) is None

    # Token ya expirado.
    vencido = jwt.encode({"sub": 1, "iat": 0, "exp": 1}, os.environ["SESSION_SECRET"], algorithm=ALGORITMO)
    assert decodificar_jwt(vencido) is None

    assert _token_de_header(None) is None
    assert _token_de_header("Bearer abc123") == "abc123"
    assert _token_de_header("abc123") is None  # sin el prefijo "Bearer "

    # Admins: se lee del entorno, se normaliza a minúsculas y sin espacios.
    os.environ["ADMIN_EMAILS"] = " Uno@Gmail.com , dos@gmail.com "
    assert _admins() == {"uno@gmail.com", "dos@gmail.com"}
    os.environ["ADMIN_EMAILS"] = ""
    assert _admins() == set(), "sin la variable no entra nadie"

    print("auth self-check OK — JWT propio, sin llamadas a Google")


if __name__ == "__main__":
    _self_check()
