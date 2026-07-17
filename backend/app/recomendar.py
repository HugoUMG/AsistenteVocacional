"""Motor de recomendación: le pasa el perfil del estudiante y el catálogo de
carreras a Gemini, y devuelve un análisis de afinidad por carrera (agrupando
las universidades que ofrecen la misma carrera)."""

import os

from google import genai
from google.genai import types
from pydantic import BaseModel

# Modelo configurable: cámbialo con GEMINI_MODEL en .env si hace falta.
MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM = (
    "Eres un orientador vocacional. Analiza el perfil del estudiante contra TODO "
    "el catálogo de carreras y produce un análisis de afinidad.\n\n"
    "Reglas:\n"
    "- AGRUPA por programa académico: si una misma carrera (p. ej. Derecho) la "
    "ofrecen varios centros o incluso distintos departamentos, es UN solo grupo "
    "con varias instituciones. Usa un nombre canónico claro y corto para el grupo.\n"
    "- Asigna a cada carrera un porcentaje de afinidad ENTERO. Los porcentajes de "
    "TODAS las carreras deben sumar exactamente 100.\n"
    "- Incluye únicamente las carreras con afinidad mayor a 1. Ordena de mayor a "
    "menor afinidad.\n"
    "- 'descripcion': explicación general (2-3 frases) de por qué la carrera encaja "
    "con el perfil, válida para todas las instituciones que la ofrecen; NO menciones "
    "una universidad concreta aquí.\n"
    "- Por cada institución indica universidad, centro y departamento (tal como "
    "aparecen en el catálogo) y su 'enfoque': qué distingue a ESE centro para esa "
    "carrera (su sello o énfasis particular), en 1-2 frases.\n"
    "- Escribe en español, cercano y claro."
)


class Institucion(BaseModel):
    universidad: str
    centro: str
    departamento: str
    enfoque: str


class CarreraRecomendada(BaseModel):
    carrera: str
    afinidad: int
    descripcion: str
    instituciones: list[Institucion]


class Resultado(BaseModel):
    carreras: list[CarreraRecomendada]


def hay_api_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _catalogo_texto(carreras) -> str:
    return "\n\n".join(
        f"### {c.nombre} ({c.universidad} - {c.centro} - {c.departamento})\n{c.perfil}"
        for c in carreras
    )


def recomendar(respuestas: dict, carreras) -> list[CarreraRecomendada]:
    """respuestas: dict con las respuestas del cuestionario.
    carreras: lista de models.Carrera (el catálogo).
    Devuelve las carreras afines (>1%) con su % y el detalle por institución."""
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
            response_schema=Resultado,
            temperature=0.3,
        ),
    )
    return Resultado.model_validate_json(resp.text).carreras


if __name__ == "__main__":
    # ponytail: self-check del parseo del catálogo, sin llamar a la API.
    class _C:
        def __init__(self, n, u, ce, p):
            self.nombre, self.universidad, self.centro, self.perfil = n, u, ce, p

    txt = _catalogo_texto([_C("Ing. Forestal", "USAC", "CUNTOTO", "ama el bosque")])
    assert "Ing. Forestal" in txt and "CUNTOTO" in txt and "bosque" in txt
    print("ok")
