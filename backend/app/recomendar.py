"""Motor de recomendación: le pasa el perfil del estudiante y el catálogo de
carreras a Gemini, y devuelve carreras recomendadas con justificación."""

import os

from google import genai
from google.genai import types
from pydantic import BaseModel

# Modelo configurable: cámbialo con GEMINI_MODEL en .env si hace falta.
MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM = (
    "Eres un orientador vocacional. A partir del perfil de un estudiante y un "
    "catálogo de carreras, recomienda las 3 carreras más afines, de mayor a "
    "menor. Usa SOLO carreras del catálogo. En cada justificación, conecta de "
    "forma concreta los intereses y el estilo del estudiante con el perfil "
    "vocacional de la carrera. Escribe en español, cercano y claro."
)


class Recomendacion(BaseModel):
    carrera: str
    universidad: str
    justificacion: str


class Recomendaciones(BaseModel):
    recomendaciones: list[Recomendacion]


def hay_api_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _catalogo_texto(carreras) -> str:
    return "\n\n".join(
        f"### {c.nombre} ({c.universidad} - {c.centro})\n{c.perfil}"
        for c in carreras
    )


def recomendar(respuestas: dict, carreras) -> list[Recomendacion]:
    """respuestas: dict con las respuestas del cuestionario.
    carreras: lista de models.Carrera (el catálogo).
    Devuelve hasta 3 carreras recomendadas, de mayor a menor afinidad."""
    perfil = "\n".join(f"- {k}: {v}" for k, v in respuestas.items())

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODELO,
        contents=(
            f"PERFIL DEL ESTUDIANTE:\n{perfil}\n\n"
            f"CATÁLOGO DE CARRERAS:\n{_catalogo_texto(carreras)}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=Recomendaciones,
            temperature=0.4,
        ),
    )
    return Recomendaciones.model_validate_json(resp.text).recomendaciones


if __name__ == "__main__":
    # ponytail: self-check del parseo del catálogo, sin llamar a la API.
    class _C:
        def __init__(self, n, u, ce, p):
            self.nombre, self.universidad, self.centro, self.perfil = n, u, ce, p

    txt = _catalogo_texto([_C("Ing. Forestal", "USAC", "CUNTOTO", "ama el bosque")])
    assert "Ing. Forestal" in txt and "CUNTOTO" in txt and "bosque" in txt
    print("ok")
