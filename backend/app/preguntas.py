"""Test vocacional adaptativo tipo 'Akinator': la IA decide la SIGUIENTE
pregunta según el catálogo y las respuestas dadas, para ir descartando unas
carreras y reforzando otras. Catálogo-agnóstico: no depende de qué carreras
haya cargadas."""

import os

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.recomendar import MODELO, _catalogo_texto

SYSTEM = (
    "Eres un orientador vocacional que conduce un test tipo 'Akinator' para "
    "descubrir qué carrera del catálogo encaja mejor con el estudiante.\n\n"
    "Con base en el catálogo y las respuestas dadas hasta ahora, decide la "
    "SIGUIENTE pregunta más útil: la que mejor permita DESCARTAR unas carreras y "
    "REFORZAR otras (máxima discriminación entre las que aún son plausibles).\n\n"
    "ESTILO DE CONVERSACIÓN (muy importante):\n"
    "- Cada pregunta debe SONAR como un orientador humano que escucha, no como una "
    "encuesta. En 'pregunta_texto', abre con una frase breve y cálida que RETOME o "
    "REFLEJE algo que el estudiante ya dijo (usa sus propias palabras o menciona una "
    "respuesta anterior), y LUEGO formula la pregunta. Ej.: 'Me queda claro que "
    "disfrutas ayudar a los demás y te atrae la biología. Ahora quiero entender algo "
    "más: ...'.\n"
    "- Demuestra MEMORIA: conecta la nueva pregunta con lo que respondió antes.\n"
    "- Varía las aperturas (no empieces siempre igual, evita repetir 'Entiendo' o "
    "'Interesante').\n"
    "- De vez en cuando plantea la pregunta como un ESCENARIO real (p. ej. 'Imagina "
    "que tienes un sábado libre y puedes hacer lo que quieras, ¿qué eliges?').\n\n"
    "Reglas:\n"
    "- Pregunta sobre intereses, gustos, habilidades, valores y estilo de trabajo. "
    "NUNCA menciones nombres de carreras ni de universidades en la pregunta.\n"
    "- Prefiere 'sino' (Sí/No) u 'opcion' (opción múltiple, 2 a 4 opciones) porque "
    "discriminan mejor. Usa 'texto' (respuesta abierta) solo ocasionalmente para matices.\n"
    "- No repitas una pregunta ya hecha ni preguntes algo que ya se deduce.\n"
    "- Español, segunda persona, cercano y claro. NO uses emojis (ni en la "
    "pregunta ni en las opciones).\n"
    "- NO agregues una opción 'Otro'; la interfaz la añade automáticamente.\n"
    "- Marca 'multiple': true SOLO si la pregunta admite naturalmente varias "
    "respuestas a la vez (p. ej. varios intereses o metas); si no, false.\n"
    "- El estudiante YA respondió unas preguntas iniciales. Haz solo las preguntas "
    "adicionales necesarias para afinar (normalmente 2 o 3). Marca terminado=true "
    "en cuanto el perfil sea claro; no alargues el test innecesariamente.\n"
    "- Si terminado=true, deja pregunta_texto vacío y opciones vacías.\n"
    "- Para 'opcion', llena opciones con value (id corto en minúsculas) y label "
    "(texto visible, sin emojis). Para 'sino' y 'texto', deja opciones vacío."
)


class Opcion(BaseModel):
    value: str
    label: str


class SiguientePaso(BaseModel):
    terminado: bool
    pregunta_texto: str
    pregunta_tipo: str  # "sino" | "opcion" | "texto"
    multiple: bool  # en "opcion": permite elegir varias
    opciones: list[Opcion]


def _historial(respuestas: dict) -> str:
    lineas = []
    for k, v in respuestas.items():
        if k == "nombre":
            lineas.append(f"El estudiante se llama {v}.")
        else:
            lineas.append(f"P: {k}\nR: {v}")
    if len(lineas) <= 1:
        lineas.append("Aún no ha respondido preguntas vocacionales.")
    return "\n".join(lineas)


def siguiente_pregunta(respuestas: dict, carreras) -> SiguientePaso:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODELO,
        contents=(
            "CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
            f"{_catalogo_texto(carreras)}\n\n"
            f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{_historial(respuestas)}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=SiguientePaso,
            temperature=0.5,
        ),
    )
    return SiguientePaso.model_validate_json(resp.text)


if __name__ == "__main__":
    # ponytail: self-check del historial, sin llamar a la API.
    h = _historial({"nombre": "Ana", "¿Te gusta la naturaleza?": "sí"})
    assert "Ana" in h and "naturaleza" in h
    print("ok")
