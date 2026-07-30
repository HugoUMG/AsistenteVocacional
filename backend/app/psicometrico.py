"""Examen psicométrico de 100 ítems en 4 categorías (personalidad, razonamiento
lógico, verbal y numérico). Vive APARTE del chat vocacional: no alimenta la
recomendación de carreras ni comparte prompts con ella.

El banco de preguntas y la CLAVE DE RESPUESTAS viven aquí, en el backend: el
frontend solo recibe enunciados y opciones (sin cuál es la correcta), así que no
se puede leer la clave desde las devtools del navegador.

Self-check sin API: uv run python -m app.psicometrico
"""

import os
import re

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.recomendar import ANTI_INYECCION, MODELO_FINAL, TONO, _texto_seguro, uso_tokens

# --- Parte 1: personalidad y comportamiento (ítems 1-40) ---
# (id, enunciado, rasgo, signo). signo -1 = ítem invertido: estar "totalmente de
# acuerdo" resta al rasgo (sirve para detectar quien marca todo igual sin leer).
ESCALA = [
    "Totalmente en desacuerdo",
    "En desacuerdo",
    "Neutral",
    "De acuerdo",
    "Totalmente de acuerdo",
]  # se envían como valor 1..5

RASGOS = {
    "organizacion": "Orden, planificación y atención al detalle",
    "liderazgo": "Iniciativa, exposición social y autonomía",
    "estabilidad": "Manejo de la presión, la crítica y la frustración",
    "apertura": "Adaptación al cambio, creatividad y gusto por lo nuevo",
    "interpersonal": "Empatía, colaboración y clima de equipo",
    "logro": "Esfuerzo, responsabilidad y orientación a resultados",
}

PERSONALIDAD = [
    (1, "Prefiero terminar una tarea antes de empezar otra.", "organizacion", 1),
    (2, "Me siento cómodo liderando grupos de trabajo grandes.", "liderazgo", 1),
    (3, "El desorden en mi espacio de trabajo me distrae fácilmente.", "organizacion", 1),
    (4, "Prefiero seguir instrucciones claras antes que improvisar.", "apertura", -1),
    (5, "Mantengo la calma incluso en situaciones de mucha presión.", "estabilidad", 1),
    (6, "Me resulta fácil entender los sentimientos de mis compañeros.", "interpersonal", 1),
    (7, "Disfruto resolver problemas complejos y abstractos.", "apertura", 1),
    (8, "Prefiero planificar mi día al detalle antes de empezarlo.", "organizacion", 1),
    (9, "Me adapto rápidamente a los cambios de planes de última hora.", "apertura", 1),
    (10, "Suelo tomar la iniciativa en las reuniones de equipo.", "liderazgo", 1),
    (11, "Me frustro cuando las cosas no salen como las planeé.", "estabilidad", -1),
    (12, "Considero que las reglas estrictas limitan mi creatividad.", "apertura", 1),
    (13, "Rara vez me guardo mis opiniones si no estoy de acuerdo con el grupo.", "liderazgo", 1),
    (14, "Me considero una persona más práctica que teórica.", "apertura", -1),
    (15, "Prefiero trabajar de forma individual que en equipo.", "interpersonal", -1),
    (16, "Dedico tiempo a analizar mis errores para no repetirlos.", "logro", 1),
    (17, "Me entusiasma aprender a usar nuevas tecnologías o herramientas.", "apertura", 1),
    (18, "Suelo postergar las tareas que me resultan aburridas.", "logro", -1),
    (19, "Tomo decisiones basadas en datos y lógica, no en emociones.", "organizacion", 1),
    (20, "Me siento cómodo hablando en público ante una gran audiencia.", "liderazgo", 1),
    (21, "Me afecta mucho que me critiquen, aunque sea para ayudarme a mejorar.", "estabilidad", -1),
    (22, "Prefiero entregar algo bien hecho aunque me tome más tiempo.", "organizacion", 1),
    (23, "Me resulta fácil entablar conversación con personas desconocidas.", "liderazgo", 1),
    (24, "Suelo mantener una actitud optimista ante las dificultades.", "estabilidad", 1),
    (25, "Prefiero que mis días se parezcan entre sí antes que estar llenos de cambios.", "apertura", -1),
    (26, "Me aseguro de revisar mi trabajo varias veces antes de entregarlo.", "organizacion", 1),
    (27, "Puedo trabajar eficazmente con personas que piensan distinto a mí.", "interpersonal", 1),
    (28, "Si tengo un problema con un compañero, lo hablo directamente con él.", "interpersonal", 1),
    (29, "Me aburro rápidamente si lo que hago se vuelve repetitivo.", "apertura", 1),
    (30, "Creo que a uno le va bien más por el esfuerzo que por la suerte.", "logro", 1),
    (31, "Me cuesta decir “no” cuando me piden ayuda con tareas adicionales.", "liderazgo", -1),
    (32, "Me organizo bien cuando tengo poco tiempo para entregar algo.", "estabilidad", 1),
    (33, "Me esfuerzo por ser el mejor en lo que hago, incluso de forma competitiva.", "logro", 1),
    (34, "Prefiero que alguien con más experiencia revise constantemente lo que hago.", "liderazgo", -1),
    (35, "Encuentro soluciones creativas a problemas comunes.", "apertura", 1),
    (36, "Me siento responsable de mantener un buen clima en el equipo.", "interpersonal", 1),
    (37, "Pierdo la paciencia cuando los demás van más lento que yo.", "estabilidad", -1),
    (38, "Sé separar mis asuntos personales de mis responsabilidades.", "estabilidad", 1),
    (39, "Me motiva asumir proyectos de alta responsabilidad.", "logro", 1),
    (40, "Me siento satisfecho con lo que he logrado hasta ahora.", "estabilidad", 1),
]

# Pares de consistencia: cada uno debe ser una CASI-PARÁFRASIS o un opuesto
# directo del MISMO rasgo, nunca dos ideas solo "relacionadas". Si no, se acusa
# de mentiroso a quien responde honesto: "prefiero trabajar solo" y "puedo
# trabajar con quien piensa distinto" son ambas verdad a la vez (preferencia vs.
# capacidad), y ese par (15↔27) marcaba contradicción siempre.
#
# ponytail: TECHO CONOCIDO — este es un índice de COHERENCIA, no una escala de
# sinceridad validada. El banco de 40 ítems no contiene paráfrasis literales, así
# que cualquier par puede divergir de forma legítima en los extremos (medido: los
# 6 marcan contradicción si se responde 5 en uno y 1 en el otro, aunque sea
# honesto). Por eso UNA contradicción no significa nada — deja el índice en 83%,
# por encima del umbral — y hacen falta 2+ para que baje. Si algún día se quiere
# una escala de mentira de verdad, hay que AGREGAR ítems paráfrasis al banco
# (p. ej. "reviso antes de entregar" ↔ "suelo entregar sin revisar"), no
# recombinar estos.
#   4↔12  necesidad de estructura (instrucciones claras / las reglas me limitan)
#   25↔29 tolerancia a la repetición (prefiero rutina / me aburre lo repetitivo)
#   9↔11  reacción al plan roto (me adapto / me frustro)
#   2↔20  comodidad ante mucha gente (liderar grupos / hablar en público)
#   22↔26 calidad por encima de la prisa (priorizo calidad / reviso varias veces)
#   5↔24  temple ante la dificultad (mantengo la calma / sigo optimista)
PARES_CONSISTENCIA = [(4, 12), (25, 29), (9, 11), (2, 20), (22, 26), (5, 24)]

# Ítems socialmente deseables: decir "totalmente de acuerdo" en TODOS es la
# respuesta que "queda bien". La alerta exige el máximo en TODOS (no en 6 de 8):
# con 6 se acusaba al 21% de alumnos honestos y responsables, medido sobre 300
# perfiles simulados. ponytail: umbral calibrado a mano; una escala de mentira
# real usa afirmaciones improbables ("nunca he llegado tarde"), no virtudes
# normales — cambiar si alguna vez se baremea de verdad.
ITEMS_DESEABILIDAD = [5, 6, 16, 24, 26, 27, 30, 36]

# --- Partes 2-4: reactivos con respuesta correcta (ítems 41-100) ---
# (id, categoría, enunciado, opciones, índice de la correcta)
OBJETIVAS = [
    # Parte 2: razonamiento lógico y abstracto
    (41, "logico", "¿Qué número sigue en la secuencia: 2, 4, 8, 16, 32, …?", ["48", "60", "64", "128"], 2),
    (42, "logico", "Si A es más alto que B, y B es más alto que C, ¿quién es el más bajo?", ["A", "B", "C", "No se puede saber"], 2),
    (43, "logico", "¿Qué número continúa la serie: 5, 10, 8, 13, 11, 16, …?", ["12", "14", "18", "21"], 1),
    (44, "logico", "Si todos los mamíferos tienen sangre caliente y una ballena es un mamífero, ¿la ballena tiene sangre caliente?", ["Sí", "No", "Solo algunas", "No se puede saber"], 0),
    (45, "logico", "Completa la serie de letras: A, C, E, G, …", ["H", "I", "J", "K"], 1),
    (46, "logico", "¿Qué número sigue en la secuencia: 1, 3, 6, 10, 15, …?", ["18", "20", "21", "25"], 2),
    (47, "logico", "Si un reloj marca las 3:15, ¿cuántos grados mide el ángulo entre las manecillas?", ["0 grados", "7.5 grados", "15 grados", "30 grados"], 1),
    (48, "logico", "Completa la secuencia numérica: 100, 90, 81, 73, …", ["64", "65", "66", "68"], 2),
    (49, "logico", "Si el lunes es el primer día, ¿cuál es el quinto día posterior al miércoles?", ["Sábado", "Domingo", "Lunes", "Martes"], 2),
    (50, "logico", "Encuentra el número que falta: 3, 9, 27, …, 243.", ["54", "72", "81", "108"], 2),
    (51, "logico", "Si inviertes la palabra “ROMA”, obtienes “AMOR”. Si inviertes “ZORRO”, obtienes…", ["ORROZ", "ROZOR", "ORZOR", "OZZOR"], 0),
    (52, "logico", "¿Qué figura continúa el patrón: círculo, cuadrado, círculo, triángulo, círculo, …?", ["Círculo", "Cuadrado", "Triángulo", "Pentágono"], 1),
    (53, "logico", "Si un cubo tiene 6 caras, ¿cuántas aristas tiene?", ["6", "8", "12", "16"], 2),
    (54, "logico", "¿Qué letra continúa la serie: Z, X, V, T, …?", ["S", "R", "Q", "P"], 1),
    (55, "logico", "Si no todos los pájaros vuelan y el pingüino es un pájaro, ¿vuela el pingüino?", ["Sí, todos los pájaros vuelan", "No necesariamente", "Sí, pero solo distancias cortas", "La premisa es falsa"], 1),
    (56, "logico", "Siguiendo la regla de elevar al cuadrado: 2 es a 4 como 3 es a…", ["5", "6", "9", "12"], 2),
    (57, "logico", "Encuentra el intruso: triángulo, cuadrado, círculo, pentágono.", ["Triángulo", "Cuadrado", "Círculo", "Pentágono"], 2),
    (58, "logico", "¿Qué número sigue la serie: 2, 3, 5, 7, 11, …?", ["12", "13", "14", "15"], 1),
    (59, "logico", "Si ayer fue martes, ¿qué día será pasado mañana?", ["Jueves", "Viernes", "Sábado", "Domingo"], 1),
    (60, "logico", "¿Qué número falta en la secuencia: 80, 40, 20, …, 5?", ["8", "10", "12", "15"], 1),
    # Parte 3: razonamiento verbal y comprensión
    (61, "verbal", "¿Cuál es el sinónimo de la palabra “efímero”?", ["Pasajero", "Eterno", "Profundo", "Sólido"], 0),
    (62, "verbal", "¿Cuál es el antónimo de la palabra “altruista”?", ["Generoso", "Egoísta", "Solidario", "Amable"], 1),
    (63, "verbal", "Completa la analogía: sol es a día como luna es a…", ["Estrella", "Noche", "Cielo", "Sombra"], 1),
    (64, "verbal", "¿Cuál es el sinónimo de “genuino”?", ["Falso", "Auténtico", "Común", "Costoso"], 1),
    (65, "verbal", "Completa la frase: el candidato demostró una gran _______ durante la entrevista.", ["Elocuencia", "Indiferencia", "Torpeza", "Distracción"], 0),
    (66, "verbal", "¿Cuál es el antónimo de “optimista”?", ["Alegre", "Pesimista", "Confiado", "Realista"], 1),
    (67, "verbal", "Completa la analogía: timón es a barco como volante es a…", ["Camino", "Automóvil", "Motor", "Rueda"], 1),
    (68, "verbal", "¿Qué palabra no pertenece al grupo: manzana, pera, plátano, zanahoria?", ["Manzana", "Pera", "Plátano", "Zanahoria"], 3),
    (69, "verbal", "¿Cuál es el sinónimo de “mitigar”?", ["Aliviar", "Agravar", "Ocultar", "Provocar"], 0),
    (70, "verbal", "¿Cuál es el antónimo de “éxito”?", ["Logro", "Fracaso", "Meta", "Triunfo"], 1),
    (71, "verbal", "Completa la analogía: médico es a hospital como profesor es a…", ["Libro", "Escuela", "Alumno", "Pizarra"], 1),
    (72, "verbal", "¿Qué palabra significa “que habla mucho y con soltura”?", ["Locuaz", "Parco", "Tímido", "Sagaz"], 0),
    (73, "verbal", "¿Cuál es el antónimo de “rígido”?", ["Firme", "Flexible", "Duro", "Estricto"], 1),
    (74, "verbal", "Completa la frase: a pesar de los obstáculos, la empresa logró su…", ["Objetivo", "Fracaso", "Renuncia", "Retraso"], 0),
    (75, "verbal", "¿Qué palabra no pertenece al grupo: carpintero, médico, herramienta, ingeniero?", ["Carpintero", "Médico", "Herramienta", "Ingeniero"], 2),
    (76, "verbal", "¿Cuál es el sinónimo de “innovar”?", ["Repetir", "Renovar", "Conservar", "Copiar"], 1),
    (77, "verbal", "Completa la analogía: hojas son a árbol como páginas son a…", ["Tinta", "Libro", "Papel", "Letra"], 1),
    (78, "verbal", "¿Cuál es el antónimo de “opulencia”?", ["Riqueza", "Pobreza", "Abundancia", "Lujo"], 1),
    (79, "verbal", "¿Qué palabra define la acción de “poner orden y limpieza”?", ["Organizar", "Improvisar", "Acumular", "Descuidar"], 0),
    (80, "verbal", "¿Cuál es el sinónimo de “esmero”?", ["Descuido", "Dedicación", "Prisa", "Rutina"], 1),
    # Parte 4: razonamiento numérico y matemático
    (81, "numerico", "Si un producto cuesta $120 y tiene un 20% de descuento, ¿cuánto pagas?", ["$84", "$90", "$96", "$100"], 2),
    (82, "numerico", "¿Cuánto es el 15% de 200?", ["15", "25", "30", "35"], 2),
    (83, "numerico", "Si tres camiones transportan 12 toneladas, ¿cuántas toneladas transportan seis camiones?", ["18", "20", "24", "36"], 2),
    (84, "numerico", "Resuelve la operación: (4 × 5) + (12 / 3) = …", ["20", "22", "24", "28"], 2),
    (85, "numerico", "Si un tren viaja a 80 km/h, ¿cuánto tiempo tarda en recorrer 240 km?", ["2 horas", "2.5 horas", "3 horas", "4 horas"], 2),
    (86, "numerico", "¿Cuál es el promedio de los números 10, 20, 30 y 40?", ["20", "25", "30", "35"], 1),
    (87, "numerico", "Si cuatro secretarias escriben 4 cartas en 4 minutos, ¿cuánto tarda una secretaria en escribir una carta?", ["1 minuto", "2 minutos", "4 minutos", "16 minutos"], 2),
    (88, "numerico", "Un artículo sube de $50 a $60. ¿Qué porcentaje aumentó?", ["10%", "15%", "20%", "25%"], 2),
    (89, "numerico", "Resuelve la operación: 150 − (25 × 4) = …", ["25", "50", "75", "100"], 1),
    (90, "numerico", "Si una oficina tiene 40 empleados y el 60% son mujeres, ¿cuántos hombres hay?", ["14", "16", "20", "24"], 1),
    (91, "numerico", "Si guardas $5 semanales, ¿cuánto dinero tendrás en un año completo (52 semanas)?", ["$200", "$240", "$260", "$280"], 2),
    (92, "numerico", "¿Cuánto es la mitad de la cuarta parte de 80?", ["5", "10", "16", "20"], 1),
    (93, "numerico", "Si un pantalón y una camisa cuestan $110 en total, y el pantalón cuesta $100 más que la camisa, ¿cuánto cuesta la camisa?", ["$5", "$10", "$50", "$55"], 0),
    (94, "numerico", "Resuelve: 8 + 4 × 2 = …", ["12", "16", "20", "24"], 1),
    (95, "numerico", "Si una máquina produce 15 piezas por minuto, ¿cuántas produce en una hora?", ["150", "450", "900", "1500"], 2),
    (96, "numerico", "¿Cuál es el resultado de sumar el doble de 15 más el triple de 10?", ["45", "50", "60", "75"], 2),
    (97, "numerico", "Si gastas un tercio de tu sueldo de $900, ¿cuánto dinero te queda?", ["$300", "$450", "$600", "$700"], 2),
    (98, "numerico", "Un equipo de fútbol ganó 12 partidos de 20 jugados. ¿Qué porcentaje de partidos ganó?", ["40%", "50%", "60%", "70%"], 2),
    (99, "numerico", "Resuelve la siguiente operación: (50 / 2) × (6 − 4) = …", ["25", "50", "75", "100"], 1),
    (100, "numerico", "Si una cisterna se llena a un ritmo de 5 litros por minuto, ¿cuántos litros tendrá tras media hora?", ["75", "100", "150", "300"], 2),
]

CATEGORIAS = {
    "personalidad": "Perfil de personalidad y comportamiento",
    "logico": "Razonamiento lógico y abstracto",
    "verbal": "Razonamiento verbal y comprensión",
    "numerico": "Razonamiento numérico y matemático",
}

# Penalización estilo SHL: cada error resta 1/4 de punto SOLO en la sección
# numérica, para desincentivar responder al azar contra el reloj. Lógico y
# verbal no penalizan (criterio de puntuación directa).
PENALIZACION = {"numerico": 0.25}

# ponytail: baremo ILUSTRATIVO (anclas % de aciertos → percentil, interpolado),
# no una muestra normativa real. Para usarlo en decisiones reales hay que
# baremar con una población de referencia y sustituir esta tabla.
# El ancla del 25% vale 2 y no 10 porque 25% ES EL PISO DE AZAR: con 4 opciones,
# adivinar las 20 preguntas da ~5 aciertos. Antes ese piso salía como "percentil
# 12", que se leía como un desempeño real cuando no lo era.
_BAREMO = [(0, 1), (25, 2), (40, 25), (55, 50), (70, 75), (85, 90), (100, 99)]

# Etiquetas del percentil, para que la IA no tenga que interpretarlo sola (en
# pruebas llamó "desempeño promedio" a un percentil 25).
_BANDAS = [(10, "muy bajo, en el rango del azar"), (25, "bajo"),
           (45, "medio-bajo"), (60, "promedio"), (80, "alto"), (101, "muy alto")]

# Cuántos "Neutral" de 40 hacen que el perfil deje de informar. Calibrado contra
# perfiles honestos simulados (ver el self-check): un alumno real con rasgos
# moderados usa el centro, pero no la mitad del test.
TENDENCIA_CENTRAL_MAXIMA = 20

# Mismo umbral que usa el badge del frontend: por debajo, el protocolo se
# considera poco consistente. Vive aquí para que la IA lea la MISMA conclusión
# que muestra la interfaz (antes la interfaz decía "alerta" y la IA "coherente").
CONSISTENCIA_MINIMA = 70


def _banda(percentil: int) -> str:
    return next(etiqueta for tope, etiqueta in _BANDAS if percentil < tope)


def _percentil(pct_aciertos: float) -> int:
    for (x0, y0), (x1, y1) in zip(_BAREMO, _BAREMO[1:]):
        if pct_aciertos <= x1:
            t = (pct_aciertos - x0) / (x1 - x0)
            return round(y0 + t * (y1 - y0))
    return 99


def preguntas() -> dict:
    """Banco de preguntas para el frontend, SIN la clave de respuestas."""
    return {
        "escala": ESCALA,
        "categorias": CATEGORIAS,
        "preguntas": [
            {"id": i, "categoria": "personalidad", "texto": t}
            for i, t, _, _ in PERSONALIDAD
        ]
        + [
            {"id": i, "categoria": cat, "texto": t, "opciones": ops}
            for i, cat, t, ops, _ in OBJETIVAS
        ],
    }


def _califica_personalidad(respuestas: dict) -> dict:
    """respuestas: {id_item: 1..5}. Devuelve perfil por rasgo (0-100),
    consistencia y deseabilidad social."""
    # Valor "orientado": en los ítems invertidos, 5 se convierte en 1.
    val = {}
    for i, _, _, signo in PERSONALIDAD:
        v = respuestas.get(i)
        if v is not None:
            val[i] = v if signo == 1 else 6 - v

    rasgos = {}
    for clave in RASGOS:
        items = [i for i, _, r, _ in PERSONALIDAD if r == clave and i in val]
        if items:
            crudo = sum(val[i] for i in items)
            rasgos[clave] = {
                "puntaje": round((crudo - len(items)) / (4 * len(items)) * 100),
                "items": len(items),
            }

    pares = [(a, b) for a, b in PARES_CONSISTENCIA if a in val and b in val]
    diffs = [abs(val[a] - val[b]) for a, b in pares]
    contradicciones = [
        [a, b] for (a, b), d in zip(pares, diffs) if d >= 3
    ]  # 3+ puntos de brecha en la misma idea = contradicción
    consistencia = round(sum(1 - d / 4 for d in diffs) / len(diffs) * 100) if diffs else 0

    des = [val[i] for i in ITEMS_DESEABILIDAD if i in val]
    # Tendencia central: quien contesta "Neutral" a todo sacaba coherencia 100% y
    # los 6 rasgos clavados en 50 — el patrón más evasivo posible obtenía la mejor
    # nota de sinceridad. No se toca la coherencia (son cosas distintas): se marca
    # aparte, porque lo que falla ahí no es la consistencia sino que el protocolo
    # no informa nada.
    neutrales = sum(1 for i, _, _, _ in PERSONALIDAD if respuestas.get(i) == 3)
    return {
        "rasgos": rasgos,
        "tendencia_central": {
            "pct": round(neutrales / len(PERSONALIDAD) * 100),
            "alerta": neutrales >= TENDENCIA_CENTRAL_MAXIMA,
        },
        "consistencia": {"pct": consistencia, "contradicciones": contradicciones},
        "deseabilidad_social": {
            "pct": round(sum(des) / (5 * len(des)) * 100) if des else 0,
            # Marcar el máximo en TODAS las virtudes = perfil "demasiado bueno".
            "alerta": len(des) == len(ITEMS_DESEABILIDAD) and all(v == 5 for v in des),
        },
        "respondidas": len(val),
        "total": len(PERSONALIDAD),
    }


def _califica_categoria(cat: str, respuestas: dict, segundos: int | None) -> dict:
    items = [(i, correcta) for i, c, _, _, correcta in OBJETIVAS if c == cat]
    correctas = sum(1 for i, ok in items if respuestas.get(i) == ok)
    intentadas = sum(1 for i, _ in items if respuestas.get(i) is not None)
    incorrectas = intentadas - correctas
    puntaje = max(0.0, correctas - PENALIZACION.get(cat, 0) * incorrectas)
    return {
        "correctas": correctas,
        "intentadas": intentadas,
        "total": len(items),
        "puntaje": round(puntaje, 2),
        "penalizacion_por_error": PENALIZACION.get(cat, 0),
        # Velocidad vs. precisión: acertar 10 de 10 intentos vale más que 12 de 20.
        # None (no 0) si no intentó ninguna: sin intentos la precisión no existe,
        # y un "0%" se lee como "falló todas".
        "precision": round(correctas / intentadas * 100) if intentadas else None,
        "percentil": _percentil(puntaje / len(items) * 100),
        "segundos": segundos,
    }


def calificar(respuestas: dict, tiempos: dict | None = None) -> dict:
    """respuestas: {id_item (int): valor}. Personalidad = 1..5; el resto = índice
    de la opción elegida. tiempos: {categoria: segundos}."""
    tiempos = tiempos or {}
    return {
        "personalidad": _califica_personalidad(respuestas),
        "logico": _califica_categoria("logico", respuestas, tiempos.get("logico")),
        "verbal": _califica_categoria("verbal", respuestas, tiempos.get("verbal")),
        "numerico": _califica_categoria("numerico", respuestas, tiempos.get("numerico")),
    }


# --- Resumen con IA (1 llamada a Gemini, al terminar el examen) ---

class ResumenPsicometrico(BaseModel):
    personalidad: str
    logico: str
    verbal: str
    numerico: str
    fortalezas: list[str]
    a_desarrollar: list[str]
    cierre: str


SYSTEM_RESUMEN = (
    "Eres un psicólogo laboral que interpreta los resultados de un examen "
    "psicométrico de 100 ítems ya calificado. Recibes los PUNTAJES, no las "
    "respuestas: tu trabajo es explicarlos en lenguaje claro para el propio "
    "evaluado, un estudiante.\n"
    "- 'personalidad': 3 a 4 frases sobre su perfil de rasgos. NO hay rasgos "
    "buenos ni malos: describe el estilo de trabajo que sugiere el perfil. Sobre "
    "la coherencia: NO la menciones si el estado dice CONSISTENTE (una sola "
    "divergencia es normal en gente honesta y no significa nada); si dice POCO "
    "CONSISTENTE, dilo con tacto y sin acusar de mentir — la lectura es 'este "
    "perfil hay que tomarlo con reservas', no 'mentiste'. Igual con la alerta de "
    "deseabilidad social.\n"
    "- 'logico', 'verbal', 'numerico': 2 a 3 frases cada uno. Interpreta aciertos, "
    "precisión y percentil. CADA percentil viene con su etiqueta ya calculada "
    "(muy bajo / bajo / medio-bajo / promedio / alto / muy alto): RESPÉTALA, no "
    "la suavices ni la subas — un percentil 25 es bajo, no promedio. Si la "
    "etiqueta dice 'en el rango del azar', el resultado no distingue si supo o "
    "adivinó, y hay que decirlo. Si la precisión es baja frente a los intentos, "
    "menciona impulsividad; si intentó pocos ítems, menciona cautela o falta de "
    "tiempo.\n"
    "- 'fortalezas' y 'a_desarrollar': 2 a 4 frases cortas cada una, concretas y "
    "accionables.\n"
    "- 'cierre': 1 o 2 frases que conecten el perfil con el tipo de tareas o "
    "entornos donde suele rendir mejor alguien así.\n"
    "IMPORTANTE: este examen mide estilo y aptitudes, NO inteligencia ni valor "
    "personal, y no diagnostica nada. No prometas ni descartes carreras concretas.\n"
    "Español, cercano, sin emojis, sin viñetas.\n\n"
    + TONO
    + ANTI_INYECCION
)


def _puntajes_texto(p: dict) -> str:
    per = p["personalidad"]
    rasgos = "\n".join(
        f"- {RASGOS[k]}: {v['puntaje']}/100" for k, v in per["rasgos"].items()
    )
    partes = [
        "PERSONALIDAD (0 = polo bajo del rasgo, 100 = polo alto; no hay puntaje bueno o malo):",
        rasgos,
        f"- Índice de consistencia: {per['consistencia']['pct']}% "
        f"({len(per['consistencia']['contradicciones'])} contradicciones entre ítems "
        f"equivalentes) → "
        + ("CONSISTENTE: el perfil se puede leer con confianza"
           if per["consistencia"]["pct"] >= CONSISTENCIA_MINIMA
           else "POCO CONSISTENTE: dilo con tacto, el perfil se lee con reservas"),
        f"- Deseabilidad social: {per['deseabilidad_social']['pct']}%"
        + (" (ALERTA: respondió TODAS las virtudes al máximo)"
           if per["deseabilidad_social"]["alerta"] else ""),
        f"- Respuestas 'Neutral': {per['tendencia_central']['pct']}%"
        + (" (ALERTA: se quedó en el centro en casi todo, así que el perfil "
           "informa poco; invítalo a repetirlo comprometiéndose más con las "
           "respuestas, sin regañarlo)"
           if per["tendencia_central"]["alerta"] else ""),
    ]
    for cat in ("logico", "verbal", "numerico"):
        c = p[cat]
        t = f", {c['segundos']}s empleados" if c.get("segundos") else ""
        partes.append(
            f"\n{CATEGORIAS[cat].upper()}: {c['correctas']} correctas de {c['total']} "
            f"({c['intentadas']} intentadas, precisión "
            f"{c['precision'] if c['intentadas'] else 'no medible, no intentó ninguna'}"
            f"{'%' if c['intentadas'] else ''}), "
            f"puntaje {c['puntaje']}, percentil {c['percentil']} "
            f"({_banda(c['percentil'])}){t}"
        )
    return "\n".join(partes)


def resumen(puntajes: dict) -> tuple[ResumenPsicometrico, dict]:
    # ponytail: el cliente debe quedar en una variable con nombre (no encadenado
    # inline) — si no, el GC lo cierra a mitad de la llamada. Igual que extras.py.
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODELO_FINAL,
        contents=_puntajes_texto(puntajes),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_RESUMEN,
            response_mime_type="application/json",
            response_schema=ResumenPsicometrico,
            temperature=0.4,
        ),
    )
    return (
        ResumenPsicometrico.model_validate_json(_texto_seguro(resp)),
        uso_tokens(resp, MODELO_FINAL),
    )


SIGNO = {i: s for i, _, _, s in PERSONALIDAD}


def _self_check():
    """Verifica el banco y la calificación sin llamar a la API."""
    ids = [i for i, *_ in PERSONALIDAD] + [i for i, *_ in OBJETIVAS]
    assert ids == list(range(1, 101)), "faltan o se repiten ítems (deben ser 1..100)"
    for i, cat, _, ops, ok in OBJETIVAS:
        assert len(ops) == 4 and len(set(ops)) == 4, f"ítem {i}: opciones repetidas"
        assert 0 <= ok < 4, f"ítem {i}: índice de correcta fuera de rango"
        assert cat in CATEGORIAS
    assert "opciones" not in preguntas()["preguntas"][0], "personalidad no lleva opciones"
    assert all(
        "correcta" not in p for p in preguntas()["preguntas"]
    ), "el banco público NO debe exponer la clave"

    # Todo correcto en las objetivas + "totalmente de acuerdo" en todo.
    perfecto = {i: 5 for i, *_ in PERSONALIDAD}
    perfecto |= {i: ok for i, _, _, _, ok in OBJETIVAS}
    p = calificar(perfecto, {"logico": 300})
    for cat in ("logico", "verbal", "numerico"):
        assert p[cat]["correctas"] == 20 and p[cat]["precision"] == 100, cat
        assert p[cat]["percentil"] == 99, cat
    assert p["logico"]["segundos"] == 300
    # Marcar todo 5 se contradice en los ítems invertidos y dispara la alerta.
    assert p["personalidad"]["deseabilidad_social"]["alerta"] is True
    assert p["personalidad"]["consistencia"]["pct"] < 100
    assert p["personalidad"]["rasgos"]["organizacion"]["puntaje"] == 100
    assert p["personalidad"]["rasgos"]["apertura"]["puntaje"] < 100  # tiene invertidos

    # Todo mal en numérico: 20 errores penalizan a 0 (no negativo).
    malo = {i: (ok + 1) % 4 for i, c, _, _, ok in OBJETIVAS if c == "numerico"}
    p2 = calificar(malo)
    assert p2["numerico"]["puntaje"] == 0 and p2["numerico"]["precision"] == 0
    assert p2["logico"]["intentadas"] == 0 and p2["logico"]["percentil"] == 1
    # Sin intentos la precisión NO es 0% (eso se leería como "falló todas").
    assert p2["logico"]["precision"] is None
    assert p2["personalidad"]["respondidas"] == 0

    # Piso de azar: 4 opciones => adivinar da ~25% de aciertos, y eso NO puede
    # salir como un percentil que se lea como desempeño real.
    assert _percentil(25) <= 3, "el piso de azar se está premiando"
    assert _banda(_percentil(25)) == "muy bajo, en el rango del azar"
    assert _banda(25) == "medio-bajo" and _banda(50) == "promedio"
    assert _banda(99) == "muy alto"

    # Deseabilidad social: solo alerta con TODAS las virtudes al máximo. Con 7 de
    # 8 no, porque un alumno honesto y responsable llega ahí (se medía 21% de
    # falsos positivos con el umbral anterior de 6).
    casi = {i: 3 for i, *_ in PERSONALIDAD}
    casi |= {i: 5 for i in ITEMS_DESEABILIDAD[:7]}
    assert calificar(casi)["personalidad"]["deseabilidad_social"]["alerta"] is False
    casi[ITEMS_DESEABILIDAD[7]] = 5
    assert calificar(casi)["personalidad"]["deseabilidad_social"]["alerta"] is True

    # Tendencia central: "Neutral" en todo daba coherencia 100% y los 6 rasgos en
    # 50 — el patrón más evasivo salía como el más sincero. Ahora se marca.
    todo_neutral = calificar({i: 3 for i, *_ in PERSONALIDAD})["personalidad"]
    assert todo_neutral["tendencia_central"] == {"pct": 100, "alerta": True}
    assert set(r["puntaje"] for r in todo_neutral["rasgos"].values()) == {50}
    # ...pero un alumno con rasgos moderados NO puede caer en la alerta por usar
    # el centro de vez en cuando.
    moderado = {i: (3 if i % 3 == 0 else 4) for i, *_ in PERSONALIDAD}
    assert calificar(moderado)["personalidad"]["tendencia_central"]["alerta"] is False

    # Ningún ítem puede presuponer que el evaluado ya trabaja: el público son
    # estudiantes de 13-17 años. "mi jefe", "vida laboral", "logros profesionales"
    # no son contestables a esa edad y contaminaban el rasgo de estabilidad.
    laborales = re.compile(r"\b(laboral|jefe|profesional(es)?|plazos?|puesto|"
                           r"desempeño|empresa)\b", re.I)
    fuera = [i for i, t, _, _ in PERSONALIDAD if laborales.search(t)]
    assert not fuera, f"ítems que presuponen empleo previo: {fuera}"

    # Los pares de consistencia deben ser casi-paráfrasis: responder IGUAL en los
    # dos (ya orientados) nunca puede marcar contradicción.
    for a, b in PARES_CONSISTENCIA:
        for nivel in (1, 5):
            r = {i: 3 for i, *_ in PERSONALIDAD}
            r[a] = nivel if SIGNO[a] == 1 else 6 - nivel
            r[b] = nivel if SIGNO[b] == 1 else 6 - nivel
            c = calificar(r)["personalidad"]["consistencia"]
            assert [a, b] not in c["contradicciones"], f"par {(a, b)} acusa sin motivo"
    # ...y responder en polos opuestos SÍ debe marcarla.
    a, b = PARES_CONSISTENCIA[0]
    r = {i: 3 for i, *_ in PERSONALIDAD}
    r[a] = 5 if SIGNO[a] == 1 else 1
    r[b] = 1 if SIGNO[b] == 1 else 5
    assert [a, b] in calificar(r)["personalidad"]["consistencia"]["contradicciones"]

    # Velocidad vs. precisión: 10/10 debe puntuar mejor que 12/20 en numérico.
    cauto = {i: ok for i, c, _, _, ok in OBJETIVAS if c == "numerico"}
    ids_num = sorted(cauto)
    cauto = {i: cauto[i] for i in ids_num[:10]}
    impulsivo = {i: (ok if n < 12 else (ok + 1) % 4)
                 for n, (i, c, _, _, ok) in enumerate(
                     [o for o in OBJETIVAS if o[1] == "numerico"])}
    a = calificar(cauto)["numerico"]
    b = calificar(impulsivo)["numerico"]
    # La penalización deja ambos en el mismo puntaje (12 − 0.25×8 = 10): quien
    # decide es la precisión, que separa al cauto del impulsivo.
    assert a["puntaje"] == b["puntaje"] == 10, (a, b)
    assert a["precision"] == 100 and b["precision"] == 60
    print("psicometrico self-check OK — 100 ítems, calificación y baremo consistentes")


if __name__ == "__main__":
    _self_check()
