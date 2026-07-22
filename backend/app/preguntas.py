"""Test vocacional adaptativo tipo 'Akinator': la IA decide la SIGUIENTE
pregunta según el catálogo y las respuestas dadas, para ir descartando unas
carreras y reforzando otras. Catálogo-agnóstico: no depende de qué carreras
haya cargadas."""

from pydantic import BaseModel

from app.filtro import preseleccionar
from app.recomendar import (
    ANTI_INYECCION,
    MODELO,
    TONO,
    _catalogo_texto,
    _texto_seguro,
    generar,
    uso_tokens,
)

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
    "- COBERTURA DE DIMENSIONES: un buen perfil vocacional explora 7 dimensiones "
    "(personalidad, intereses, habilidades, estilo_cognitivo, valores, entorno, "
    "motivaciones). Cada mensaje del usuario te dice, con datos reales (no lo "
    "adivines tú), cuáles ya están cubiertas y cuáles siguen PENDIENTES. SIEMPRE "
    "dirige la siguiente pregunta a una dimensión PENDIENTE que el mensaje te "
    "indique; nunca profundices en una ya cubierta mientras haya una pendiente. "
    "Sigue exactamente la instrucción de terminado que venga en el mensaje del "
    "usuario (ese estado es más confiable que lo que tú infieras del historial).\n"
    "- NUNCA menciones nombres de carreras ni de universidades en la pregunta.\n"
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
    "- El estudiante YA respondió unas preguntas iniciales. Cuando ya no queden "
    "dimensiones pendientes (según el mensaje del usuario), marca terminado=true "
    "SOLO si además la carrera #1 del ranking supera a la #2 por al menos 20 "
    "puntos; si el top está parejo (diferencia < 20), sigue preguntando para "
    "desempatar.\n"
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
    "- 'dimension_objetivo': la dimensión (de las 7 de arriba) que esta pregunta "
    "busca cubrir; usa exactamente uno de: personalidad, intereses, habilidades, "
    "estilo_cognitivo, valores, entorno, motivaciones. Si terminado=true, deja "
    "cadena vacía.\n"
    "- Si terminado=true, deja pregunta_texto vacío y opciones vacías.\n"
    "- Para 'opcion', llena opciones con value (id corto en minúsculas) y label "
    "(texto visible, sin emojis). Para 'sino' y 'texto', deja opciones vacío.\n\n"
    + TONO
    + ANTI_INYECCION
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
    dimension_objetivo: str  # personalidad|intereses|habilidades|estilo_cognitivo|valores|entorno|motivaciones


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


DIMENSIONES = (
    "personalidad", "intereses", "habilidades", "estilo_cognitivo",
    "valores", "entorno", "motivaciones",
)
# Las preguntas fijas (impacto/estilo/entorno/gustos, ver Chat.jsx) ya tocan
# motivaciones, intereses y entorno de entrada; las otras 4 arrancan en 0.
COBERTURA_INICIAL = {d: (1 if d in ("intereses", "entorno", "motivaciones") else 0) for d in DIMENSIONES}
PRIORITARIAS = ("personalidad", "habilidades", "valores", "estilo_cognitivo")

MIN_ADAPTATIVAS = 4
MAX_ADAPTATIVAS = 8

# ponytail: estado en memoria de proceso, por session_id (un id por carga de
# página, ver frontend/src/session.js). Se pierde al reiniciar el backend;
# aceptable para un despliegue de un solo proceso. Si algún día hay varias
# instancias del backend, esto necesita moverse a la BD o a un cache compartido.
_COBERTURA_POR_SESION: dict[str, dict[str, int]] = {}


def _cobertura(session_id: str | None) -> dict[str, int]:
    clave = session_id or "_sin_sesion"
    return _COBERTURA_POR_SESION.setdefault(clave, dict(COBERTURA_INICIAL))


def _texto_cobertura(cobertura: dict[str, int]) -> str:
    partes = [f"{d}:{'cubierta' if cobertura[d] else 'PENDIENTE'}" for d in DIMENSIONES]
    return ", ".join(partes)


def siguiente_pregunta(
    respuestas: dict, carreras, session_id: str | None = None
) -> tuple[SiguientePaso, dict]:
    # Pre-filtro sin IA: recalculado en cada llamada con TODAS las respuestas
    # acumuladas hasta ahora (ver app/filtro.py). Si el catálogo ya es chico
    # (p. ej. un solo departamento pequeño), no recorta nada.
    candidatas = preseleccionar(respuestas, carreras)
    if len(candidatas) < len(carreras):
        print(f"[filtro] next-question: {len(carreras)} -> {len(candidatas)} carreras candidatas")

    cobertura = _cobertura(session_id)
    hechas = sum(cobertura.values()) - sum(COBERTURA_INICIAL.values())
    pendientes = [d for d in PRIORITARIAS if not cobertura[d]]

    variable = (
        f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{_historial(respuestas)}\n\n"
        f"COBERTURA DE DIMENSIONES (estado real, no lo infieras del historial): "
        f"{_texto_cobertura(cobertura)}.\n"
        f"Llevas {hechas} pregunta(s) adaptativa(s) de mínimo {MIN_ADAPTATIVAS} y "
        f"máximo {MAX_ADAPTATIVAS}. "
        + (
            f"Dimensiones prioritarias AÚN PENDIENTES: {', '.join(pendientes)} — tu "
            "siguiente pregunta DEBE apuntar a una de estas (usa ese valor exacto en "
            "'dimension_objetivo'). terminado DEBE ser false.\n"
            if pendientes and hechas < MAX_ADAPTATIVAS
            else "Todas las dimensiones prioritarias ya están cubiertas; puedes "
            "terminar si el ranking ya es claro.\n"
        )
    )

    uso_total = None
    paso = None
    for _ in range(2):  # 1 intento normal + 1 reintento si ignora la cobertura pendiente
        resp = generar(
            model=MODELO,
            system=SYSTEM,
            catalogo=(
                "CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
                f"{_catalogo_texto(candidatas)}"
            ),
            variable=variable,
            schema=SiguientePaso,
            temperature=0.5,
        )
        paso = SiguientePaso.model_validate_json(_texto_seguro(resp))
        uso_total = uso_tokens(resp, MODELO)
        corta_antes_de_tiempo = paso.terminado and pendientes and hechas < MAX_ADAPTATIVAS
        if not corta_antes_de_tiempo:
            break
        print(f"[dimension] next-question: terminó con pendientes {pendientes}, reintentando")
        variable += (
            f"\n\nRECORDATORIO: quedan dimensiones prioritarias sin cubrir "
            f"({', '.join(pendientes)}). terminado DEBE ser false; dirige la "
            "pregunta a una de ellas."
        )

    if paso.dimension_objetivo:
        cobertura[paso.dimension_objetivo] = 1
        print(f"[dimension] next-question -> {paso.dimension_objetivo} "
              f"(pendientes tras esta: {[d for d in PRIORITARIAS if not cobertura[d]]})")
    return paso, uso_total


if __name__ == "__main__":
    # ponytail: self-check del historial y de la cobertura, sin llamar a la API.
    h = _historial({"nombre": "Ana", "¿Te gusta la naturaleza?": "sí"})
    assert "Ana" in h and "naturaleza" in h

    _COBERTURA_POR_SESION.clear()
    cob = _cobertura("s1")
    assert cob == COBERTURA_INICIAL and cob is not COBERTURA_INICIAL  # copia, no alias
    assert [d for d in PRIORITARIAS if not cob[d]] == list(PRIORITARIAS)  # nada prioritario cubierto aún
    cob["personalidad"] = 1
    assert _cobertura("s1")["personalidad"] == 1  # persiste entre llamadas de la misma sesión
    assert _cobertura("s2")["personalidad"] == 0  # sesiones distintas no se mezclan
    print("ok")
