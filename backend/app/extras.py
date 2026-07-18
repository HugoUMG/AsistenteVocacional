"""Features on-demand del dashboard: simulador de un día en la carrera y
comparador entre dos carreras. Ambas reciben el contexto ya calculado por
/api/recommend (descripcion, razones) desde el frontend, así que no dependen
del catálogo ni de nombres exactos en la BD — 1 llamada a Gemini cada una,
solo cuando el estudiante las pide."""

import os

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.recomendar import MODELO


# --- Simulador "Un día siendo..." ---

class EventoDia(BaseModel):
    hora: str  # p.ej. "08:00"
    actividad: str


class SimulacionDia(BaseModel):
    eventos: list[EventoDia]
    cierre: str


SYSTEM_SIMULADOR = (
    "Eres un orientador vocacional. Genera una narrativa realista y concreta de "
    "un día típico ejerciendo la carrera indicada, adaptada cuando sea posible al "
    "perfil del estudiante.\n"
    "- 'eventos': 5 a 7 momentos del día, cada uno con 'hora' (formato HH:MM) y "
    "'actividad' (1 frase breve y vívida). Cubre desde la mañana hasta la tarde "
    "o noche, en orden cronológico.\n"
    "- Sé honesto: incluye tanto lo atractivo de la profesión como algún reto o "
    "exigencia real, no lo idealices.\n"
    "- 'cierre': 1 frase final que invite a la reflexión sobre si esa rutina "
    "encaja con el estudiante.\n"
    "Español, cercano, sin emojis, sin viñetas."
)


def simular_dia(carrera: str, descripcion: str, respuestas: dict) -> SimulacionDia:
    perfil = "\n".join(f"- {k}: {v}" for k, v in respuestas.items())
    # ponytail: el cliente debe quedar en una variable con nombre (no encadenado
    # inline) — si no, el GC lo cierra a mitad de la llamada ("client has been
    # closed"). Mismo patrón que recomendar.py/preguntas.py.
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODELO,
        contents=(
            f"CARRERA: {carrera}\nPor qué le fue recomendada: {descripcion}\n\n"
            f"PERFIL DEL ESTUDIANTE:\n{perfil}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_SIMULADOR,
            response_mime_type="application/json",
            response_schema=SimulacionDia,
            temperature=0.6,
        ),
    )
    return SimulacionDia.model_validate_json(resp.text)


# --- Comparador de carreras ---

class Comparacion(BaseModel):
    en_comun: list[str]
    puntos_a: list[str]
    puntos_b: list[str]
    recomendacion: str


SYSTEM_COMPARADOR = (
    "Eres un orientador vocacional. Un estudiante está indeciso entre dos "
    "carreras y quiere entender la diferencia entre ambas, a la luz de su "
    "propio perfil.\n"
    "- 'en_comun': 2 a 3 frases cortas de lo que ambas carreras comparten.\n"
    "- 'puntos_a' / 'puntos_b': 2 a 4 frases cortas que distinguen a cada una "
    "(qué exige, qué predomina en el día a día), en tono neutral y objetivo, "
    "sin decir cuál es 'mejor'.\n"
    "- 'recomendacion': 1 a 2 frases conectando con el perfil del estudiante "
    "para ayudarlo a decidir, sin ser tajante (ambas siguen siendo válidas).\n"
    "Español, cercano, sin emojis, sin viñetas."
)


def comparar_carreras(
    carrera_a: str, descripcion_a: str,
    carrera_b: str, descripcion_b: str,
    respuestas: dict,
) -> Comparacion:
    perfil = "\n".join(f"- {k}: {v}" for k, v in respuestas.items())
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODELO,
        contents=(
            f"CARRERA A: {carrera_a}\n{descripcion_a}\n\n"
            f"CARRERA B: {carrera_b}\n{descripcion_b}\n\n"
            f"PERFIL DEL ESTUDIANTE:\n{perfil}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_COMPARADOR,
            response_mime_type="application/json",
            response_schema=Comparacion,
            temperature=0.4,
        ),
    )
    return Comparacion.model_validate_json(resp.text)
