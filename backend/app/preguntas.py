"""Test vocacional adaptativo tipo 'Akinator': la IA decide la SIGUIENTE
pregunta según el catálogo y las respuestas dadas, para ir descartando unas
carreras y reforzando otras. Catálogo-agnóstico: no depende de qué carreras
haya cargadas."""

from pydantic import BaseModel

from app import holland as holland_mod
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

# Puntos de afinidad que la carrera #1 debe sacarle a la #2 para que el chat
# pueda darse por terminado. Va en el prompt Y en el guard de código de
# siguiente_pregunta(), desde la misma constante para que no se desincronicen:
# antes solo estaba escrito en el prompt y nadie verificaba que se cumpliera.
MARGEN_DESEMPATE = 20

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
    f"SOLO si además la carrera #1 del ranking supera a la #2 por al menos "
    f"{MARGEN_DESEMPATE} puntos; si el top está parejo (diferencia < "
    f"{MARGEN_DESEMPATE}), sigue preguntando para desempatar, y que esa pregunta "
    "SEPARE a esas dos carreras en concreto (sin nombrárselas al estudiante).\n"
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


def _cobertura(session_id: str | None, extra: dict[str, int] | None = None) -> dict[str, int]:
    """`extra`: dimensiones que ya llegan cubiertas desde afuera (el test corto
    de personalidad, ver app/personalidad.py). Solo se aplica al CREAR la
    entrada de la sesión, igual que COBERTURA_INICIAL; llamadas siguientes
    reusan lo que ya había, sin pisar el progreso hecho en el chat."""
    clave = session_id or "_sin_sesion"
    if clave not in _COBERTURA_POR_SESION:
        inicial = dict(COBERTURA_INICIAL)
        if extra:
            inicial.update(extra)
        _COBERTURA_POR_SESION[clave] = inicial
    return _COBERTURA_POR_SESION[clave]


def empatado(ranking: list) -> bool:
    """¿El top del ranking provisional está demasiado parejo para terminar?

    El prompt ya pedía no terminar con el top empatado, pero nadie lo
    verificaba: el guard de siguiente_pregunta() solo miraba las dimensiones
    pendientes, así que un terminado=true con 78 contra 78 pasaba tal cual.

    ponytail: compara #1 contra #2 y ya. No mira si hay tres empatadas ni pesa
    cuántas van; si el chat resulta cortarse parejo seguido, el techo se sube
    mirando toda la cola del ranking.
    """
    return len(ranking) >= 2 and (ranking[0].afinidad - ranking[1].afinidad) < MARGEN_DESEMPATE


def _texto_cobertura(cobertura: dict[str, int]) -> str:
    partes = [f"{d}:{'cubierta' if cobertura[d] else 'PENDIENTE'}" for d in DIMENSIONES]
    return ", ".join(partes)


def siguiente_pregunta(
    respuestas: dict, carreras, session_id: str | None = None,
    holland: str | None = None, holland_puntajes: dict[str, int] | None = None,
    personalidad: str | None = None, personalidad_cobertura: dict[str, int] | None = None,
) -> tuple[SiguientePaso, dict]:
    """`holland`: bloque de texto con el perfil RIASEC medido, si el alumno hizo
    el test antes del chat (modo 3, ver docs/holland.md). Va como sección aparte
    del prompt y NO entra al pre-filtro del catálogo: recortar el catálogo al
    sector de Holland se midió y borra las carreras correctas
    (experiments/holland-en-chat.md §3). La cobertura de dimensiones no cambia:
    las 4 preguntas fijas se quedan y ya cubren intereses.

    `holland_puntajes`: {letra: 0-40}, los seis puntajes del alumno; obligatorio
    junto con `holland` para armar la adenda (`holland_mod.adenda_chat` nombra el
    área más alta en la apertura y detecta empates, ver
    experiments/holland-apertura.md).

    `personalidad`: bloque de texto del test corto de personalidad/valores/estilo
    cognitivo, si el alumno lo hizo antes del chat (ver app/personalidad.py).
    `personalidad_cobertura`: {dimensión: 1}, las que ese test ya cubrió (siempre
    personalidad/valores/estilo_cognitivo); se usa para SEMBRAR la cobertura de
    la sesión y así el chat no vuelve a preguntarlas."""
    # Pre-filtro sin IA: recalculado en cada llamada con TODAS las respuestas
    # acumuladas hasta ahora (ver app/filtro.py). Si el catálogo ya es chico
    # (p. ej. un solo departamento pequeño), no recorta nada.
    candidatas = preseleccionar(respuestas, carreras)
    if len(candidatas) < len(carreras):
        print(f"[filtro] next-question: {len(carreras)} -> {len(candidatas)} carreras candidatas")

    cobertura = _cobertura(session_id, personalidad_cobertura)
    hechas = sum(cobertura.values()) - sum(COBERTURA_INICIAL.values())
    pendientes = [d for d in PRIORITARIAS if not cobertura[d]]

    variable = (
        (f"{personalidad}\n\n" if personalidad else "")
        + (f"{holland}\n\n" if holland else "")
        + f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{_historial(respuestas)}\n\n"
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
            system=SYSTEM + (holland_mod.adenda_chat(holland_puntajes) if holland else ""),
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
        corta_antes_de_tiempo = (
            paso.terminado
            and (pendientes or empatado(paso.ranking))
            and hechas < MAX_ADAPTATIVAS
        )
        if not corta_antes_de_tiempo:
            break
        if pendientes:
            motivo = f"pendientes {pendientes}"
            recordatorio = (
                f"\n\nRECORDATORIO: quedan dimensiones prioritarias sin cubrir "
                f"({', '.join(pendientes)}). terminado DEBE ser false; dirige la "
                "pregunta a una de ellas."
            )
        else:
            motivo = (f"empate {paso.ranking[0].carrera} {paso.ranking[0].afinidad} vs "
                      f"{paso.ranking[1].carrera} {paso.ranking[1].afinidad}")
            recordatorio = (
                f"\n\nRECORDATORIO: tu propio ranking deja a '{paso.ranking[0].carrera}' "
                f"y '{paso.ranking[1].carrera}' separadas por menos de {MARGEN_DESEMPATE} "
                "puntos, así que el top NO está resuelto. terminado DEBE ser false. Haz "
                "una pregunta cuya respuesta SEPARE a esas dos en concreto: busca en qué "
                "se diferencian sus perfiles dentro del catálogo y pregunta por eso. NO "
                "las nombres al estudiante."
            )
        print(f"[dimension] next-question: terminó con {motivo}, reintentando")
        variable += recordatorio

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

    # empatado(): el guard que faltaba. El prompt pedía no terminar con el top
    # parejo y el código no lo verificaba.
    def _r(*afinidades):
        return [Ranking(carrera=f"C{i}", afinidad=a) for i, a in enumerate(afinidades)]

    assert empatado(_r(78, 78)), "78 contra 78 es empate"
    assert empatado(_r(80, 61)), "19 de diferencia sigue siendo empate"
    assert not empatado(_r(80, 60)), "20 justos ya desempata"
    assert not empatado(_r(90, 10)), "diferencia amplia no es empate"
    assert not empatado(_r(50)), "con una sola carrera no hay con quién empatar"
    assert not empatado([]), "ranking vacío no debe romper ni bloquear el cierre"

    # El margen del prompt y el del guard salen de la misma constante.
    assert f"{MARGEN_DESEMPATE} puntos" in SYSTEM

    # El guard de verdad: que el reintento SE DISPARE con el top empatado. Se
    # sustituye generar() por un doble que no llama a la API y que devuelve
    # terminado=true; lo que se mide es cuántas veces lo llamó siguiente_pregunta
    # y qué recordatorio le mandó en el segundo intento.
    # OJO: se parchean los globals de ESTE módulo, no los de `app.preguntas`
    # importado aparte. Con `python -m app.preguntas` el archivo se carga dos
    # veces (como __main__ y como app.preguntas) y son objetos distintos: tocar
    # el otro no afecta a la siguiente_pregunta() que se llama aquí.
    _g = globals()

    def _doble(paso_json):
        llamadas = []

        class _Resp:
            text = paso_json
            usage_metadata = None
        def _fake(**kw):
            llamadas.append(kw["variable"])
            return _Resp()
        return _fake, llamadas

    def _paso(terminado, ranking, dimension=""):
        return SiguientePaso(
            terminado=terminado, pregunta_texto="", pregunta_tipo="sino", multiple=False,
            opciones=[], ranking=_r(*ranking), alerta_contradiccion="",
            dimension_objetivo=dimension,
        ).model_dump_json()

    _real_generar, _real_cat = _g["generar"], _g["_catalogo_texto"]
    _g["_catalogo_texto"] = lambda c: "catalogo"
    try:
        # Todas las dimensiones cubiertas, pero el top empatado: debe reintentar
        # y el recordatorio debe nombrar a las dos carreras empatadas.
        _COBERTURA_POR_SESION["empate"] = {d: 1 for d in DIMENSIONES}
        _g["generar"], vistas = _doble(_paso(True, (70, 70)))
        siguiente_pregunta({"nombre": "Ana"}, [], "empate")
        assert len(vistas) == 2, f"debió reintentar con el top empatado, llamó {len(vistas)}"
        assert "C0" in vistas[1] and "C1" in vistas[1], \
            "el recordatorio debe nombrarle al modelo las dos carreras empatadas"

        # Mismo caso pero con el top resuelto: NO debe reintentar.
        _COBERTURA_POR_SESION["claro"] = {d: 1 for d in DIMENSIONES}
        _g["generar"], vistas = _doble(_paso(True, (90, 40)))
        siguiente_pregunta({"nombre": "Ana"}, [], "claro")
        assert len(vistas) == 1, "con el top resuelto debe cerrar en un solo intento"

        # Y una pregunta normal (terminado=false) tampoco reintenta, aunque el
        # ranking venga parejo: el guard solo mira si intenta CERRAR.
        _COBERTURA_POR_SESION["sigue"] = {d: 1 for d in DIMENSIONES}
        _g["generar"], vistas = _doble(_paso(False, (70, 70), "valores"))
        siguiente_pregunta({"nombre": "Ana"}, [], "sigue")
        assert len(vistas) == 1, "si no intenta cerrar, no hay nada que forzar"
    finally:
        _g["generar"], _g["_catalogo_texto"] = _real_generar, _real_cat
        for k in ("empate", "claro", "sigue"):
            _COBERTURA_POR_SESION.pop(k, None)

    print("ok")
