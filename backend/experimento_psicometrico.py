"""Experimento A/B: ¿mejora el chat si el examen psicométrico va PRIMERO?

Hipótesis: si el alumno responde el psicométrico antes de conversar, el chat
puede **saltarse las 4 preguntas fijas** (impacto/estilo/entorno/gustos) y usar
sus 4-8 turnos en preguntas especializadas, porque personalidad, habilidades y
estilo cognitivo ya vienen MEDIDOS por el instrumento en vez de estimados por
la propia IA.

## Aislamiento

Este script NO toca `app/`. El puente psicométrico→chat (`perfil_texto`) y el
bucle del brazo NUEVO viven aquí. El flujo en producción sigue exactamente
igual mientras el experimento no se acepte (regla 4 del proyecto).

## Brazos

- **VIEJO**: el flujo de hoy. 4 preguntas fijas respondidas por la persona +
  `preguntas.siguiente_pregunta()` tal cual + `recomendar.recomendar()`.
- **NUEVO**: sin preguntas fijas. La hoja del psicométrico se califica con
  `psicometrico.calificar()` y el resultado entra al prompt como PERFIL MEDIDO;
  la cobertura arranca con personalidad/habilidades/estilo_cognitivo ya
  cubiertas, así que las preguntas van directo a intereses, valores, entorno y
  motivaciones.

Ambos brazos usan la MISMA persona respondiendo (mismo guion de sinceridad), el
mismo catálogo y el mismo número máximo de preguntas adaptativas.

## Realismo de los perfiles

Cada perfil mezcla verdad y distorsión a propósito, como un alumno real:

- Las secciones objetivas (lógico/verbal/numérico) NO las responde la IA: se
  simulan con una probabilidad de acierto por sección y un patrón de conducta
  (abandonar el final por tiempo, contestar al azar). Así el "no sabe" es
  aritmético y auditable, no una actuación del modelo.
- La sección de personalidad tampoco: se arma desde los rasgos reales del perfil
  y se le aplican DISTORSIONES con nombre (deseabilidad social, aquiescencia,
  refugio en el centro). Como sé qué sesgo inyecté, puedo comparar contra lo que
  el instrumento detectó — ground truth de verdad.
- Solo el chat lo responde Gemini en el papel de la persona, con un guion que
  incluye explícitamente en qué miente o se contradice y en qué es honesta.

## Limitaciones, dichas de frente

- 5 casos ficticios no dan potencia estadística. Sirven para leer CÓMO cambia la
  conversación, no para afirmar una mejora.
- Circularidad parcial: quien responde el chat y quien recomienda son el mismo
  modelo. Entre ambos media la calificación aritmética del psicométrico, que el
  modelo no controla.
- Las respuestas del chat se cachean por perfil y brazo, pero dependen de la
  pregunta recibida, así que el caché solo sirve para reanudar una corrida
  interrumpida, no para reproducir la corrida exacta.

## Uso

    uv run python experimento_psicometrico.py --self-check   # sin red
    uv run python experimento_psicometrico.py --hojas        # solo califica el psicométrico (sin red)
    uv run python experimento_psicometrico.py                # corre el A/B (gasta cuota)
    uv run python experimento_psicometrico.py --perfil Kevin # un solo perfil
"""

import argparse
import glob
import json
import os
import random

from dotenv import load_dotenv

# ANTES de importar app.recomendar: resuelve MODELO/MODELO_FINAL con os.getenv al
# importarse (mismo tropiezo que en experimento_cip.py).
load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import preguntas, psicometrico, recomendar  # noqa: E402
from app.filtro import preseleccionar  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_psicometrico_resultados.json")

DEPARTAMENTO = "Quetzaltenango"

# --- Los 5 perfiles -------------------------------------------------------
#
# aptitud: probabilidad de acertar cada ítem de la sección (0-1).
# abandona: cuántos ítems finales de esa sección deja EN BLANCO.
# rasgos: nivel honesto 1..5 de cada rasgo de `psicometrico.RASGOS`.
# distorsiones: sesgos que se aplican a la hoja de personalidad (ver `_hoja`).
# guion: cómo responde el chat — dónde es honesto y dónde no.

PERFILES = [
    {
        "nombre": "Kevin",
        "area_esperada": "informática",
        "claves": ["sistemas", "informátic", "software", "comput"],
        "contexto": (
            "17 años, quinto bachillerato en computación en Quetzaltenango. Arma "
            "PCs y le pagan por reparar celulares. Programa poco pero se defiende. "
            "Reprobó matemática dos bimestres y le da vergüenza admitirlo: en el "
            "colegio lo etiquetaron como 'el de las computadoras' y siente que "
            "tiene que sonar bueno en números."
        ),
        "aptitud": {"logico": 0.75, "verbal": 0.45, "numerico": 0.40},
        "abandona": {"numerico": 4},
        "rasgos": {"organizacion": 2, "liderazgo": 2, "estabilidad": 3,
                   "apertura": 5, "interpersonal": 3, "logro": 4},
        "distorsiones": ["deseabilidad"],
        "guion": (
            "Es honesto sobre lo que le gusta: la tecnología, armar cosas, "
            "trabajar solo con audífonos. MIENTE en dos temas: (1) si le "
            "preguntan por matemáticas, números o cálculo dice que se le dan "
            "bien, porque le avergüenza reconocer que las reprueba; (2) si le "
            "preguntan si le gusta liderar o exponer, dice que sí 'para no verse "
            "mal', aunque en realidad lo evita. Usa palabras simples, respuestas "
            "cortas, a veces suelta 'no sé, tal vez'."
        ),
    },
    {
        "nombre": "Dulce",
        "area_esperada": "salud",
        "claves": ["enfermer", "médic", "psicolog", "fisioterap", "nutric",
                   "odontolog", "clínic", "radiolog"],
        "contexto": (
            "16 años, de una aldea cerca de Cantel. Su mamá es comadrona y en la "
            "casa se da por hecho que ella será enfermera; a ella le gusta cuidar "
            "gente, eso es verdad. Pero lo que de verdad la engancha es dibujar y "
            "editar videos para el TikTok del colegio, y nunca lo dice en voz "
            "alta porque en su casa 'eso no es carrera'."
        ),
        "aptitud": {"logico": 0.55, "verbal": 0.70, "numerico": 0.45},
        "abandona": {},
        "rasgos": {"organizacion": 4, "liderazgo": 2, "estabilidad": 3,
                   "apertura": 5, "interpersonal": 5, "logro": 4},
        "distorsiones": ["deseabilidad", "aquiescencia"],
        "guion": (
            "Repite el discurso de la casa: cuando le preguntan qué quiere, dice "
            "'ayudar a la gente, algo de salud'. Es honesta en que le importa la "
            "gente y en que no le gustan los números. SE DELATA sin querer: si "
            "una pregunta la deja hablar de un sábado libre, de un proyecto que "
            "disfrutó o de qué haría sin que nadie opine, ahí SÍ dice que dibuja, "
            "edita videos y hace los carteles del colegio, y se le nota el "
            "entusiasmo. Si le preguntan directo '¿te gusta el arte?' lo minimiza "
            "('es solo un pasatiempo')."
        ),
    },
    {
        "nombre": "Brandon",
        "area_esperada": "indefinido",
        "claves": [],
        "contexto": (
            "15 años, no tiene idea de qué quiere y le da igual el test: lo hace "
            "porque lo pusieron en el colegio. No es tonto, es que no le interesa "
            "y va rápido para terminar."
        ),
        "aptitud": {"logico": 0.30, "verbal": 0.35, "numerico": 0.25},
        "abandona": {"verbal": 8, "numerico": 12},
        "rasgos": {"organizacion": 3, "liderazgo": 3, "estabilidad": 3,
                   "apertura": 3, "interpersonal": 3, "logro": 2},
        "distorsiones": ["centro"],
        "guion": (
            "Responde con desgana y lo más corto posible: 'no sé', 'igual', "
            "'cualquiera', 'lo que sea'. Si la pregunta es de opción múltiple "
            "elige casi al azar, sin criterio, y puede elegir cosas que se "
            "contradicen entre una pregunta y otra. NO inventa una vocación: si "
            "le insisten, dice que no ha pensado en eso. Solo si le preguntan por "
            "algo concreto que hace en su tiempo libre admite que juega fútbol y "
            "videojuegos."
        ),
    },
    {
        "nombre": "Melany",
        "area_esperada": "administración/contaduría",
        "claves": ["administra", "empresa", "contad", "audit", "mercadot",
                   "market", "comercio", "econom", "finanz"],
        "contexto": (
            "17 años, perito contador, ayuda en la tienda de sus papás y lleva "
            "las cuentas desde los 14. Es muy ordenada y competitiva. Está "
            "convencida de que quiere 'algo de leyes' porque una prima abogada le "
            "va bien económicamente, aunque cuando habla de su día a día todo lo "
            "que disfruta es de números, inventario y orden."
        ),
        "aptitud": {"logico": 0.70, "verbal": 0.65, "numerico": 0.85},
        "abandona": {},
        "rasgos": {"organizacion": 5, "liderazgo": 4, "estabilidad": 4,
                   "apertura": 2, "interpersonal": 3, "logro": 5},
        "distorsiones": [],
        "guion": (
            "Es articulada y responde con seguridad. Cuando le preguntan por su "
            "meta menciona 'derecho' o 'leyes' porque es lo que decidió que suena "
            "mejor y da dinero. Pero es HONESTA en todo lo demás: dice que le "
            "gusta que las cuentas cuadren, que odia improvisar, que le aburre "
            "discutir y leer textos largos, que prefiere una oficina ordenada. No "
            "se da cuenta de la contradicción; si se la señalan, la justifica "
            "('puedo aprender')."
        ),
    },
    {
        "nombre": "Josué",
        "area_esperada": "agronomía/forestal",
        "claves": ["agronom", "forestal", "ambient", "agrícola", "veterinar",
                   "zootec", "tierra", "natural"],
        "contexto": (
            "18 años, trabaja con su papá en la milpa los fines de semana y sabe "
            "de suelos y de cuándo sembrar. En el colegio le va regular. Le "
            "avergüenza el campo: cree que decir 'quiero trabajar la tierra' es "
            "decir que no llegó a más, así que en público habla de 'ingeniería'."
        ),
        "aptitud": {"logico": 0.55, "verbal": 0.40, "numerico": 0.60},
        "abandona": {"verbal": 3},
        "rasgos": {"organizacion": 4, "liderazgo": 3, "estabilidad": 5,
                   "apertura": 3, "interpersonal": 4, "logro": 4},
        "distorsiones": ["aquiescencia"],
        "guion": (
            "Al principio se vende como alguien de 'ingeniería' y de 'máquinas', "
            "sin dar detalles, porque le da pena el campo. Es honesto en el "
            "resto: dice que no aguanta estar encerrado, que se levanta temprano, "
            "que prefiere trabajos donde vea el resultado con sus manos. Si una "
            "pregunta toca lo que hace los fines de semana, la naturaleza, la "
            "lluvia o los cultivos, se suelta y habla con detalle y orgullo de la "
            "milpa, del maíz y de los suelos."
        ),
    },
]


# --- Simulación de la hoja del psicométrico (sin IA, reproducible) --------

def _hoja(perfil: dict, semilla: int = 7) -> dict:
    """Devuelve {id_item: valor} para los 100 ítems, según los rasgos reales del
    perfil, su aptitud por sección y las distorsiones que se le inyectan.

    Es aritmético a propósito: como sé qué sesgo metí, puedo comparar contra lo
    que `psicometrico.calificar()` detecta. Si esto lo generara la IA, el
    "ground truth" sería una actuación y no habría nada que verificar."""
    rnd = random.Random(f"{perfil['nombre']}-{semilla}")
    hoja = {}

    # Personalidad: el nivel honesto del rasgo, con ±1 de ruido (nadie responde
    # su propio perfil de forma perfectamente consistente).
    for i, _, rasgo, signo in psicometrico.PERSONALIDAD:
        nivel = perfil["rasgos"][rasgo] + rnd.choice([-1, 0, 0, 1])
        nivel = min(5, max(1, nivel))
        # signo -1 = ítem invertido: para expresar el mismo nivel hay que marcar
        # el valor espejo. Un alumno honesto lee y lo hace; los sesgos de abajo
        # son justamente los que rompen esto.
        hoja[i] = nivel if signo == 1 else 6 - nivel

    d = perfil["distorsiones"]
    if "deseabilidad" in d:
        # Quiere quedar bien: marca el máximo en todo lo que suena a virtud.
        for i in psicometrico.ITEMS_DESEABILIDAD:
            hoja[i] = 5 if psicometrico.SIGNO[i] == 1 else 1
    if "aquiescencia" in d:
        # Marca "de acuerdo" sin leer si el ítem estaba invertido. Es el sesgo
        # que los ítems invertidos existen para cazar.
        for i, _, _, signo in psicometrico.PERSONALIDAD:
            if signo == -1 and rnd.random() < 0.7:
                hoja[i] = 4
    if "centro" in d:
        # Se refugia en "Neutral" para terminar rápido.
        for i, *_ in psicometrico.PERSONALIDAD:
            if rnd.random() < 0.6:
                hoja[i] = 3

    # Objetivas: acierta EXACTAMENTE la proporción `aptitud` de lo que intenta;
    # cuáles falla es lo aleatorio. Se fija el número y no la probabilidad de
    # cada ítem porque con 20 ítems la lotería binomial movía a un perfil dos
    # bandas del baremo (medido: la misma Dulce de aptitud 0.55 sacaba entre 5 y
    # 17 aciertos según la semilla), y entonces el experimento estaría midiendo
    # la semilla. Los últimos `abandona` ítems quedan en blanco.
    for cat in ("logico", "verbal", "numerico"):
        items = [(i, ok) for i, c, _, _, ok in psicometrico.OBJETIVAS if c == cat]
        intenta = items[:len(items) - perfil["abandona"].get(cat, 0)]
        buenas = set(rnd.sample(range(len(intenta)), round(perfil["aptitud"][cat] * len(intenta))))
        for n, (i, ok) in enumerate(intenta):
            hoja[i] = ok if n in buenas else rnd.choice([x for x in range(4) if x != ok])
    return hoja


# --- El puente: resultado del psicométrico -> texto para el prompt --------

def perfil_texto(p: dict) -> str:
    """Traduce los puntajes a un bloque que el chat puede leer.

    Va con las alertas de validez incluidas: si el protocolo es poco consistente
    o el alumno se quedó en el centro, la IA tiene que saber que ese perfil se
    lee con reservas, no tratarlo como un hecho."""
    per = p["personalidad"]
    lineas = ["PERFIL MEDIDO CON EXAMEN PSICOMÉTRICO (100 ítems, ya calificado):",
              "Rasgos (0 = polo bajo, 100 = polo alto; no hay puntaje bueno ni malo):"]
    lineas += [f"- {psicometrico.RASGOS[k]}: {v['puntaje']}/100"
               for k, v in per["rasgos"].items()]
    lineas.append("Aptitudes (percentil con su etiqueta ya calculada, respétala):")
    for cat in ("logico", "verbal", "numerico"):
        c = p[cat]
        lineas.append(
            f"- {psicometrico.CATEGORIAS[cat]}: {c['correctas']}/{c['total']} correctas, "
            f"{c['intentadas']} intentadas, percentil {c['percentil']} "
            f"({psicometrico._banda(c['percentil'])})"
        )

    avisos = []
    if per["consistencia"]["pct"] < psicometrico.CONSISTENCIA_MINIMA:
        avisos.append(f"consistencia {per['consistencia']['pct']}% (POCO CONSISTENTE: "
                      "trata estos rasgos como provisionales y verifícalos preguntando)")
    if per["deseabilidad_social"]["alerta"]:
        avisos.append("marcó TODAS las virtudes al máximo (puede estar respondiendo lo "
                      "que queda bien; desconfía de los rasgos altos y busca ejemplos concretos)")
    if per["tendencia_central"]["alerta"]:
        avisos.append(f"{per['tendencia_central']['pct']}% de respuestas 'Neutral' "
                      "(el perfil informa poco; las preguntas tendrán que hacer casi todo el trabajo)")
    lineas.append("VALIDEZ: " + ("; ".join(avisos) if avisos else
                                 "sin alertas, el perfil se puede leer con confianza") + ".")
    return "\n".join(lineas)


# El psicométrico mide rasgos y aptitudes: eso cubre 3 de las 7 dimensiones del
# chat. Las 4 restantes son las que ninguna prueba de aptitud contesta y son
# justo las vocacionales.
CUBIERTAS_POR_EL_TEST = ("personalidad", "habilidades", "estilo_cognitivo")

ADENDA_SYSTEM = (
    "\n\nCONTEXTO ADICIONAL DE ESTE MODO: el estudiante YA respondió un examen "
    "psicométrico de 100 ítems y su perfil MEDIDO viene en el mensaje del "
    "usuario. NO vuelvas a preguntar por su personalidad, sus habilidades ni su "
    "forma de razonar: eso ya está medido, y preguntarlo otra vez desperdicia un "
    "turno. Usa esos datos para dos cosas: (1) personalizar la pregunta (puedes "
    "aludir a lo medido en la frase de apertura, con tacto y sin dar cifras ni "
    "sonar a diagnóstico), y (2) CONTRASTAR: si lo que el estudiante dice "
    "contradice lo medido, pregunta algo que aclare esa tensión y anótalo en "
    "'alerta_contradiccion'. Si la sección VALIDEZ trae alertas, trata los "
    "rasgos como hipótesis a verificar, no como hechos.\n"
    "No hay preguntas iniciales fijas en este modo: tus preguntas son lo único "
    "que hay, así que apunta directo a intereses, valores, entorno y motivaciones."
)


def _siguiente_pregunta_psico(respuestas, carreras, bloque, cobertura):
    """Brazo NUEVO. Es `preguntas.siguiente_pregunta` con dos cambios: el bloque
    del psicométrico entra al prompt, y la cobertura arranca con las 3
    dimensiones que el instrumento ya midió marcadas como cubiertas.

    Vive aquí y no en `app/preguntas.py` para no tocar el flujo de producción."""
    candidatas = preseleccionar(respuestas, carreras)
    hechas = sum(1 for d in preguntas.DIMENSIONES
                 if cobertura[d] and d not in CUBIERTAS_POR_EL_TEST)
    pendientes = [d for d in ("intereses", "valores", "entorno", "motivaciones")
                  if not cobertura[d]]

    variable = (
        f"{bloque}\n\n"
        f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{preguntas._historial(respuestas)}\n\n"
        f"COBERTURA DE DIMENSIONES (estado real, no lo infieras del historial): "
        f"{preguntas._texto_cobertura(cobertura)}.\n"
        f"Llevas {hechas} pregunta(s) adaptativa(s) de mínimo {preguntas.MIN_ADAPTATIVAS} "
        f"y máximo {preguntas.MAX_ADAPTATIVAS}. "
        + (f"Dimensiones prioritarias AÚN PENDIENTES: {', '.join(pendientes)} — tu "
           "siguiente pregunta DEBE apuntar a una de estas (usa ese valor exacto en "
           "'dimension_objetivo'). terminado DEBE ser false.\n"
           if pendientes and hechas < preguntas.MAX_ADAPTATIVAS
           else "Todas las dimensiones prioritarias ya están cubiertas; puedes "
                "terminar si el ranking ya es claro.\n")
    )
    resp = recomendar.generar(
        model=recomendar.MODELO,
        system=preguntas.SYSTEM + ADENDA_SYSTEM,
        catalogo=("CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
                  f"{recomendar._catalogo_texto(candidatas)}"),
        variable=variable,
        schema=preguntas.SiguientePaso,
        temperature=0.5,
    )
    paso = preguntas.SiguientePaso.model_validate_json(recomendar._texto_seguro(resp))
    if paso.dimension_objetivo:
        cobertura[paso.dimension_objetivo] = 1
    return paso, recomendar.uso_tokens(resp, recomendar.MODELO)


# --- La persona respondiendo el chat (1 llamada por pregunta) -------------

class RespuestaAlumno(BaseModel):
    respuesta: str


SYSTEM_ALUMNO = (
    "Actúas como un estudiante guatemalteco de secundaria respondiendo a un "
    "orientador vocacional. Respondes SOLO como ese estudiante, en primera "
    "persona, en español de Guatemala, con lenguaje de adolescente: frases "
    "cortas, informales, nada de vocabulario adulto ni de listas.\n"
    "Sigue el GUION al pie de la letra, incluso en lo que el estudiante "
    "distorsiona: si el guion dice que en cierto tema no dice la verdad, NO la "
    "digas, aunque el orientador pregunte directo. Un alumno real no es "
    "coherente al 100%.\n"
    "Si la pregunta es de opción múltiple, contesta con el texto de la opción o "
    "las opciones que elegiría (puedes elegir varias si se permite) y, si te "
    "nace, una frase corta explicando. Si es de sí/no, contesta 'Sí' o 'No' y "
    "una frase. Si es abierta, 1 a 3 frases como máximo."
)


def _responder(perfil: dict, pregunta: str, contexto_previo: str) -> str:
    resp = recomendar.generar(
        model=recomendar.MODELO,
        system=SYSTEM_ALUMNO,
        catalogo="",
        variable=(f"ESTUDIANTE: {perfil['nombre']}, {perfil['contexto']}\n\n"
                  f"GUION DE SINCERIDAD: {perfil['guion']}\n\n"
                  f"LO QUE YA DIJISTE EN ESTA CONVERSACIÓN:\n{contexto_previo or '(nada aún)'}\n\n"
                  f"PREGUNTA DEL ORIENTADOR:\n{pregunta}"),
        schema=RespuestaAlumno,
        temperature=0.9,  # alto a propósito: un alumno real no es determinista
    )
    return RespuestaAlumno.model_validate_json(recomendar._texto_seguro(resp)).respuesta.strip()


# Las 4 preguntas fijas de hoy (copiadas de frontend/src/Chat.jsx). Solo las usa
# el brazo VIEJO; el NUEVO existe justamente para no hacerlas.
FIJAS = [
    ("impacto", "¿Qué tipo de impacto te gustaría tener en el mundo? (puedes elegir varios)",
     ["Ayudar, enseñar o cuidar a las personas", "Defender la justicia y resolver conflictos",
      "Liderar, organizar negocios o usar tecnología y números",
      "Trabajar con la naturaleza, el campo o el ambiente",
      "Comunicar, crear, diseñar o investigar la realidad",
      "Construir, diseñar o hacer que las cosas funcionen"]),
    ("estilo", "¿Cómo prefieres trabajar? (puedes elegir varias)",
     ["Con personas, en trato directo", "Analizando datos, ideas y lógica",
      "De forma práctica, con las manos", "Al aire libre y en movimiento"]),
    ("entorno", "¿Dónde te imaginas trabajando? (puedes elegir varios)",
     ["En una oficina o empresa", "En un hospital, clínica o consultorio",
      "Al aire libre, en el campo o la naturaleza", "En un laboratorio o taller técnico",
      "En un aula o centro educativo", "En una obra, con máquinas o herramientas",
      "En medios, un estudio creativo o diseñando", "Con la comunidad, ayudando a personas"]),
    ("gustos", "¿Qué temas te apasionan? Elige los que quieras (o agrega el tuyo).",
     ["Matemáticas y números", "Tecnología y computación", "Salud y cuidar personas",
      "Biología y naturaleza", "Química y laboratorio", "Leyes, justicia y debate",
      "Negocios, dinero y emprender", "Arte, diseño y creatividad",
      "Comunicación, escritura y medios", "Enseñar y educar", "Psicología y comportamiento",
      "Medio ambiente y agricultura", "Construcción, máquinas y cómo funcionan las cosas",
      "Gastronomía, turismo y hotelería", "Historia, sociedad y cultura"]),
]


# --- Catálogo (desde los JSON, sin Postgres) ------------------------------

class _Carrera:
    def __init__(self, nombre, universidad, centro, departamento, perfil, grupo, sello=None):
        self.nombre, self.universidad, self.centro = nombre, universidad, centro
        self.departamento, self.perfil, self.perfil_grupo, self.sello = departamento, perfil, grupo, sello


def catalogo():
    compartidos = json.load(open(os.path.join(DATA, "perfiles_compartidos.json"), encoding="utf-8"))
    out = []
    for archivo in sorted(glob.glob(os.path.join(DATA, "carreras_*.json"))):
        d = json.load(open(archivo, encoding="utf-8"))
        for c in d["carreras"]:
            pid = c.get("perfil_id")
            out.append(_Carrera(c["nombre"], d["universidad"], d["centro"], d["departamento"],
                                compartidos[pid] if pid else c["perfil"], pid, c.get("sello")))
    return out


# --- Los dos brazos -------------------------------------------------------

def _texto_pregunta(paso) -> str:
    t = paso.pregunta_texto
    if paso.pregunta_tipo == "opcion":
        t += "\nOpciones: " + " / ".join(o.label for o in paso.opciones)
        if paso.multiple:
            t += "\n(puedes elegir varias)"
    elif paso.pregunta_tipo == "sino":
        t += "\n(responde Sí o No)"
    return t


def _conversar(perfil, cat, respuestas, avanzar, log):
    """Bucle común: pide pregunta -> la persona responde -> repite. `avanzar` es
    lo único que cambia entre brazos."""
    tokens = 0
    for _ in range(preguntas.MAX_ADAPTATIVAS):
        paso, uso = avanzar(respuestas)
        tokens += uso["total_tokens"]
        if paso.terminado:
            log.append({"terminado": True, "ranking": [r.model_dump() for r in paso.ranking]})
            break
        texto = _texto_pregunta(paso)
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        respuesta = _responder(perfil, texto, previo)
        respuestas[paso.pregunta_texto] = respuesta
        log.append({
            "dimension": paso.dimension_objetivo, "tipo": paso.pregunta_tipo,
            "pregunta": paso.pregunta_texto,
            "opciones": [o.label for o in paso.opciones],
            "respuesta": respuesta,
            "alerta_contradiccion": paso.alerta_contradiccion,
            "ranking": [r.model_dump() for r in paso.ranking],
        })
        print(f"    [{paso.dimension_objetivo or '-'}] {paso.pregunta_texto[:70]}")
        print(f"       -> {respuesta[:90]}")
    return tokens


def brazo_viejo(perfil, cat):
    """Flujo actual: 4 fijas + adaptativas, sin psicométrico."""
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    tokens = 0
    for clave, texto, opciones in FIJAS:
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}",
                       "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre"))
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})
        print(f"    [fija:{clave}] -> {r[:90]}")
    sid = f"viejo-{perfil['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    tokens += _conversar(perfil, cat, respuestas,
                         lambda r: preguntas.siguiente_pregunta(r, cat, sid), log)
    res, uso = recomendar.recomendar(respuestas, cat)
    return res, respuestas, log, tokens + uso["total_tokens"]


def brazo_nuevo(perfil, cat, puntajes):
    """Flujo propuesto: psicométrico primero, cero preguntas fijas."""
    bloque = perfil_texto(puntajes)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    cobertura = {d: (1 if d in CUBIERTAS_POR_EL_TEST else 0) for d in preguntas.DIMENSIONES}
    tokens = _conversar(perfil, cat, respuestas,
                        lambda r: _siguiente_pregunta_psico(r, cat, bloque, cobertura), log)
    # La recomendación también recibe lo medido: si no, el instrumento solo
    # habría servido para elegir preguntas y se perdería en el último paso.
    res, uso = recomendar.recomendar({**respuestas, "perfil_psicometrico": bloque}, cat)
    return res, respuestas, log, tokens + uso["total_tokens"]


def acierta(carrera, claves):
    c = carrera.lower()
    return any(k in c for k in claves)


def correr(solo=None):
    cat = catalogo()
    perfiles = [p for p in PERFILES if not solo or p["nombre"].lower() == solo.lower()]
    # Reanudable: una corrida completa son ~90 llamadas y basta un 503 de Gemini
    # a la mitad para tirarla. Los perfiles ya terminados se conservan y se
    # saltan; volver a correr el script retoma donde se quedó.
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    print(f"Catálogo: {len(cat)} registros carrera-sede · {len(perfiles)} perfiles"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")
    for perfil in perfiles:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']} ({perfil['area_esperada']})")
        puntajes = psicometrico.calificar(_hoja(perfil))
        per = puntajes["personalidad"]
        print(f"  psicométrico: consistencia {per['consistencia']['pct']}%, "
              f"deseabilidad {per['deseabilidad_social']['pct']}%"
              f"{' ALERTA' if per['deseabilidad_social']['alerta'] else ''}, "
              f"neutral {per['tendencia_central']['pct']}%"
              f"{' ALERTA' if per['tendencia_central']['alerta'] else ''} · "
              + ", ".join(f"{c[:3]} p{puntajes[c]['percentil']}"
                          for c in ("logico", "verbal", "numerico")))
        try:
            print("  --- VIEJO")
            r_v, resp_v, log_v, tok_v = brazo_viejo(perfil, cat)
            print("  --- NUEVO")
            r_n, resp_n, log_n, tok_n = brazo_nuevo(perfil, cat, puntajes)
        except Exception as e:  # 503/429 de Gemini: no tirar los perfiles ya hechos
            print(f"  ABORTADO ({type(e).__name__}: {str(e)[:90]}) — se reintenta al volver a correr\n")
            continue
        tv, tn = r_v.carreras[0], r_n.carreras[0]
        print(f"  VIEJO top1: {tv.carrera} ({tv.afinidad}%) · confianza {r_v.confianza}%")
        print(f"  NUEVO top1: {tn.carrera} ({tn.afinidad}%) · confianza {r_n.confianza}%\n")
        salida.append({
            "perfil": perfil["nombre"],
            "contexto": perfil["contexto"],
            "guion": perfil["guion"],
            "area_esperada": perfil["area_esperada"],
            "distorsiones_inyectadas": perfil["distorsiones"],
            "aptitud_real": perfil["aptitud"],
            "abandona": perfil["abandona"],
            "rasgos_reales": perfil["rasgos"],
            "psicometrico": puntajes,
            "bloque_prompt": perfil_texto(puntajes),
            "viejo": {"log": log_v, "respuestas": resp_v, "tokens": tok_v,
                      "confianza": r_v.confianza, "confianza_nota": r_v.confianza_nota,
                      "top": [c.model_dump() for c in r_v.carreras[:3]],
                      "ok": acierta(tv.carrera, perfil["claves"]) if perfil["claves"] else None},
            "nuevo": {"log": log_n, "respuestas": resp_n, "tokens": tok_n,
                      "confianza": r_n.confianza, "confianza_nota": r_n.confianza_nota,
                      "top": [c.model_dump() for c in r_n.carreras[:3]],
                      "ok": acierta(tn.carrera, perfil["claves"]) if perfil["claves"] else None},
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Resultados en {SALIDA}")
    # Este script llama a recomendar.generar() directo, sin pasar por FastAPI, así
    # que su consumo NO queda en la tabla uso_tokens: el contador en memoria es el
    # único registro del gasto (ver decisions/gemini-costos-y-caching.md).
    print(recomendar.resumen_gasto())


def _self_check():
    cat = catalogo()
    assert len(cat) == 202, len(cat)
    assert len(PERFILES) == 5 and len({p["nombre"] for p in PERFILES}) == 5
    for p in PERFILES:
        assert set(p["rasgos"]) == set(psicometrico.RASGOS), p["nombre"]
        if p["claves"]:
            assert [c for c in cat if acierta(c.nombre, p["claves"])], \
                f"{p['nombre']}: ninguna carrera del catálogo casa con sus claves"

    # La hoja simulada tiene que ser reproducible y respetar el abandono.
    kevin = next(p for p in PERFILES if p["nombre"] == "Kevin")
    assert _hoja(kevin) == _hoja(kevin)
    num = [i for i, c, *_ in psicometrico.OBJETIVAS if c == "numerico"]
    assert sum(1 for i in num if i in _hoja(kevin)) == len(num) - 4  # abandonó 4

    # Cada distorsión inyectada tiene que ser DETECTABLE por el instrumento: si
    # no, el experimento no estaría midiendo nada de validez.
    p_kevin = psicometrico.calificar(_hoja(kevin))["personalidad"]
    assert p_kevin["deseabilidad_social"]["alerta"], "deseabilidad inyectada no detectada"
    brandon = next(p for p in PERFILES if p["nombre"] == "Brandon")
    assert psicometrico.calificar(_hoja(brandon))["personalidad"]["tendencia_central"]["alerta"], \
        "refugio en el centro no detectado"
    # La aquiescencia (marcar "de acuerdo" sin leer si el ítem estaba invertido)
    # NO la detecta este instrumento: medido con el mismo perfil y la misma
    # semilla, con y sin el sesgo, la consistencia sube en vez de bajar. Ninguno
    # de los 6 pares de consistencia enfrenta un ítem directo con su invertido,
    # así que el sesgo pasa limpio. Se afirma aquí como techo conocido: si algún
    # día se agregan ítems paráfrasis al banco (ver el ponytail de
    # psicometrico.py), este assert falla y hay que reescribir el hallazgo.
    josue = next(p for p in PERFILES if p["nombre"] == "Josué")
    sin_sesgo = dict(josue, distorsiones=[])
    con = psicometrico.calificar(_hoja(josue))["personalidad"]["consistencia"]["pct"]
    sin = psicometrico.calificar(_hoja(sin_sesgo))["personalidad"]["consistencia"]["pct"]
    assert con >= sin, f"la aquiescencia ya se detecta ({sin}% -> {con}%): actualizar el informe"

    # El puente tiene que avisar de la validez, no solo soltar números.
    txt = perfil_texto(psicometrico.calificar(_hoja(brandon)))
    assert "VALIDEZ" in txt and "Neutral" in txt
    assert "PERFIL MEDIDO" in txt

    # El brazo NUEVO no puede arrancar preguntando lo que el test ya midió.
    cob = {d: (1 if d in CUBIERTAS_POR_EL_TEST else 0) for d in preguntas.DIMENSIONES}
    assert [d for d in preguntas.DIMENSIONES if not cob[d]] == \
        ["intereses", "valores", "entorno", "motivaciones"]
    print(f"self-check OK — {len(cat)} carreras, {len(PERFILES)} perfiles, "
          "distorsiones inyectadas y detectadas")


def _hojas():
    """Califica las 5 hojas simuladas sin gastar cuota: sirve para ver qué
    detecta el instrumento antes de pagar las llamadas del chat."""
    for p in PERFILES:
        s = psicometrico.calificar(_hoja(p))
        per = s["personalidad"]
        print(f"\n{p['nombre']} — inyectado: {p['distorsiones'] or 'nada'}")
        print("  rasgos: " + ", ".join(f"{k} {v['puntaje']}" for k, v in per["rasgos"].items()))
        print(f"  consistencia {per['consistencia']['pct']}% "
              f"({len(per['consistencia']['contradicciones'])} contradicciones) · "
              f"deseabilidad {per['deseabilidad_social']['pct']}%"
              f"{' ALERTA' if per['deseabilidad_social']['alerta'] else ''} · "
              f"neutral {per['tendencia_central']['pct']}%"
              f"{' ALERTA' if per['tendencia_central']['alerta'] else ''}")
        for c in ("logico", "verbal", "numerico"):
            x = s[c]
            print(f"  {c}: {x['correctas']}/{x['total']} correctas, {x['intentadas']} intentadas, "
                  f"percentil {x['percentil']} ({psicometrico._banda(x['percentil'])})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    ap.add_argument("--hojas", action="store_true", help="califica las hojas simuladas, sin red")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.hojas:
        _hojas()
    else:
        correr(a.perfil)
