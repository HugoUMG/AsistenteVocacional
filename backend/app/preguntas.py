"""Test vocacional adaptativo tipo 'Akinator': la IA decide la SIGUIENTE
pregunta según el catálogo y las respuestas dadas, para ir descartando unas
carreras y reforzando otras. Catálogo-agnóstico: no depende de qué carreras
haya cargadas."""

from pydantic import BaseModel

from app.filtro import preseleccionar
from app.recomendar import MODELO, TONO, _catalogo_texto, generar, uso_tokens

SYSTEM = (
    "Eres un orientador vocacional que conduce un test tipo 'Akinator' para "
    "descubrir qué carrera del catálogo encaja mejor con el estudiante.\n"
    "LE HABLAS A UN ADOLESCENTE de 13 a 17 años: escribe MUY sencillo y cercano, "
    "como un amigo mayor que lo aconseja, sin palabras de adulto ni tono formal "
    "(los detalles de tono van más abajo, respétalos).\n\n"
    "Con base en el catálogo y las respuestas dadas hasta ahora, decide la "
    "SIGUIENTE pregunta más útil: la que mejor permita DESCARTAR unas carreras y "
    "REFORZAR otras (máxima discriminación entre las que aún son plausibles).\n\n"
    "ESTILO DE CONVERSACIÓN (muy importante):\n"
    "- Cada pregunta debe SONAR como un orientador humano que escucha, no como una "
    "encuesta. En 'pregunta_texto', abre con una frase breve y cálida que RETOME o "
    "REFLEJE algo que el estudiante ya dijo (usa sus propias palabras o menciona una "
    "respuesta anterior), y LUEGO formula la pregunta. Ej. (fíjate en lo simple del "
    "lenguaje): 'Se nota que te gusta ayudar a los demás y que la biología te llama "
    "la atención. Ahora cuéntame una cosa: ...'.\n"
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
    "- FORMATO: en 'pregunta_texto' resalta con **negrita** (Markdown, dobles "
    "asteriscos) 1 a 3 palabras o ideas CLAVE que quieras que el estudiante note; "
    "usa *cursiva* solo para un matiz puntual. No abuses del resaltado ni lo uses "
    "en las opciones.\n"
    "- NO agregues una opción 'Otro'; la interfaz la añade automáticamente.\n"
    "- Marca 'multiple': true SOLO si la pregunta admite naturalmente varias "
    "respuestas a la vez (p. ej. varios intereses o metas); si no, false.\n"
    "- El estudiante YA respondió unas preguntas iniciales. Haz AL MENOS 4 preguntas "
    "adicionales para afinar bien, y hasta 8 como máximo. Marca terminado=true SOLO "
    "cuando el perfil sea claro: cuando la carrera #1 del ranking supere a la #2 por "
    "al menos 20 puntos. Si el top está parejo (diferencia < 20), sigue preguntando "
    "(terminado=false) para desempatar; no cortes con el perfil ambiguo.\n"
    "- 'ranking': tu estimación ACTUAL y provisional de afinidad de las 4 a 6 "
    "carreras más probables según lo respondido hasta ahora, cada una con 'carrera' "
    "(nombre corto y claro) y 'afinidad' entero 0-100, de mayor a menor. Se irá "
    "afinando con cada respuesta; inclúyelo siempre.\n"
    "- CONTRADICCIONES: si detectas que dos respuestas previas del estudiante son "
    "inconsistentes entre sí (p. ej. dijo que disfruta trabajar en equipo pero "
    "también que prefiere estar completamente solo), pon en 'alerta_contradiccion' "
    "una frase breve, amable y sin juzgar que se lo señale (p. ej. 'Noto que tus "
    "respuestas muestran intereses un poco distintos, quiero entenderlo mejor.') y "
    "haz que la siguiente pregunta ayude a aclarar esa tensión. Si no hay ninguna "
    "contradicción, deja 'alerta_contradiccion' como cadena vacía.\n"
    "- Si terminado=true, deja pregunta_texto vacío y opciones vacías.\n"
    "- Para 'opcion', llena opciones con value (id corto en minúsculas) y label "
    "(texto visible, sin emojis). Para 'sino' y 'texto', deja opciones vacío.\n\n"
    + TONO
)


class Opcion(BaseModel):
    value: str
    label: str


class Ranking(BaseModel):
    carrera: str
    afinidad: int  # estimación provisional 0-100


class SiguientePaso(BaseModel):
    terminado: bool
    pregunta_texto: str
    pregunta_tipo: str  # "sino" | "opcion" | "texto"
    multiple: bool  # en "opcion": permite elegir varias
    opciones: list[Opcion]
    ranking: list[Ranking]  # radar en tiempo real
    alerta_contradiccion: str  # "" si no hay contradicción detectada


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


def siguiente_pregunta(respuestas: dict, carreras) -> tuple[SiguientePaso, dict]:
    # Pre-filtro sin IA: recalculado en cada llamada con TODAS las respuestas
    # acumuladas hasta ahora (ver app/filtro.py). Si el catálogo ya es chico
    # (p. ej. un solo departamento pequeño), no recorta nada.
    candidatas = preseleccionar(respuestas, carreras)
    if len(candidatas) < len(carreras):
        print(f"[filtro] next-question: {len(carreras)} -> {len(candidatas)} carreras candidatas")

    resp = generar(
        model=MODELO,
        system=SYSTEM,
        catalogo=(
            "CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
            f"{_catalogo_texto(candidatas)}"
        ),
        variable=f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{_historial(respuestas)}",
        schema=SiguientePaso,
        temperature=0.5,
    )
    return SiguientePaso.model_validate_json(resp.text), uso_tokens(resp, MODELO)


if __name__ == "__main__":
    # ponytail: self-check del historial, sin llamar a la API.
    h = _historial({"nombre": "Ana", "¿Te gusta la naturaleza?": "sí"})
    assert "Ana" in h and "naturaleza" in h
    print("ok")
