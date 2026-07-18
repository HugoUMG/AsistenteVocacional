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
    "- 'razones': 3 a 5 frases MUY cortas, tipo checklist, de por qué esta carrera "
    "encaja con ESTE estudiante, conectando con sus respuestas (p. ej. 'Disfrutas "
    "resolver problemas', 'Te gustan las matemáticas'). Sin viñetas ni emojis.\n"
    "- 'factores': 3 a 5 dimensiones del perfil que MÁS influyeron en esta "
    "recomendación, cada una con 'nombre' corto (p. ej. 'Pensamiento lógico', "
    "'Trato con personas') y 'peso' entero 0-100 (cuánto pesó para esta carrera). "
    "No tienen que sumar 100.\n"
    "- Por cada institución indica universidad, centro y departamento (tal como "
    "aparecen en el catálogo) y su 'enfoque': qué distingue a ESE centro para esa "
    "carrera (su sello o énfasis particular), en 1-2 frases.\n"
    "- 'confianza': entero 0-100 que refleja qué tan segura es la recomendación en "
    "conjunto. Alta (80-100) si el perfil apunta claramente a un área; media "
    "(50-79) si hay un par de áreas compitiendo; baja (<50) si las respuestas son "
    "escasas, ambiguas o dispersas entre muchas áreas distintas.\n"
    "- 'confianza_nota': 1 frase corta explicando esa confianza en términos del "
    "perfil (p. ej. 'Tus respuestas apuntan de forma consistente a un mismo área' "
    "o 'Todavía hay algo de ambigüedad entre dos áreas distintas').\n"
    "- Escribe en español, cercano y claro."
)


class Institucion(BaseModel):
    universidad: str
    centro: str
    departamento: str
    enfoque: str


class Factor(BaseModel):
    nombre: str
    peso: int  # 0-100: cuánto influyó esa dimensión


class CarreraRecomendada(BaseModel):
    carrera: str
    afinidad: int
    descripcion: str
    razones: list[str]
    factores: list[Factor]
    instituciones: list[Institucion]


class Resultado(BaseModel):
    carreras: list[CarreraRecomendada]
    confianza: int
    confianza_nota: str


def hay_api_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _catalogo_texto(carreras) -> str:
    return "\n\n".join(
        f"### {c.nombre} ({c.universidad} - {c.centro} - {c.departamento})\n{c.perfil}"
        for c in carreras
    )


def recomendar(respuestas: dict, carreras) -> Resultado:
    """respuestas: dict con las respuestas del cuestionario.
    carreras: lista de models.Carrera (el catálogo).
    Devuelve las carreras afines (>1%) con su % y detalle, más la confianza global."""
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
    return Resultado.model_validate_json(resp.text)


if __name__ == "__main__":
    # ponytail: self-check del parseo del catálogo, sin llamar a la API.
    class _C:
        def __init__(self, n, u, ce, p):
            self.nombre, self.universidad, self.centro, self.perfil = n, u, ce, p

    txt = _catalogo_texto([_C("Ing. Forestal", "USAC", "CUNTOTO", "ama el bosque")])
    assert "Ing. Forestal" in txt and "CUNTOTO" in txt and "bosque" in txt
    print("ok")
