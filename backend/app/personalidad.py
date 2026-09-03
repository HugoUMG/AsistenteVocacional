"""Test corto (48 ítems) de personalidad, valores y estilo cognitivo: se
responde ANTES del chat (modo opcional, como Holland) para que esas 3 de las 7
dimensiones vocacionales (ver `preguntas.DIMENSIONES`) ya lleguen cubiertas y
el chat necesite menos preguntas adaptativas.

Sin llamada a Gemini: califica por reglas, igual que Holland. Reusa el mismo
formato y los 6 rasgos de personalidad ya validados en `psicometrico.py` (no
se reinventan), y agrega 2 dimensiones nuevas: valores y estilo cognitivo.

NO delimita el catálogo. Eso ya se probó dos veces (CIP y el catálogo
codificado con RIASEC de Holland) y las dos veces cortó carreras correctas
del ranking; ver docs/holland.md. Este test solo aporta CONTEXTO al prompt y
adelanta cobertura, igual que hace `holland.bloque()`.

⚠️ Pendiente de medir (regla 4 del proyecto): falta correr el experimento que
confirme que precargar esta cobertura no empeora el top-1 del chat, igual que
se hizo con Holland (`experiments/holland-en-chat.md`). Ver
`experiments/personalidad-en-chat.md` cuando exista.

Self-check sin API: uv run python -m app.personalidad
"""

from app.psicometrico import ESCALA, PERSONALIDAD, RASGOS

# --- Personalidad: subconjunto de 4 ítems por rasgo, reusando texto e id
# original de psicometrico.PERSONALIDAD (mismo banco validado, sin reescribir).
_IDS_PERSONALIDAD = {
    "organizacion": [1, 3, 8, 22],
    "liderazgo": [2, 10, 20, 23],
    "estabilidad": [5, 24, 32, 21],
    "apertura": [7, 9, 17, 4],
    "interpersonal": [6, 27, 36, 15],
    "logro": [16, 30, 18, 39],
}
_POR_ID = {i: (t, r, s) for i, t, r, s in PERSONALIDAD}

# --- Valores: qué le importa en una profesión ---
RASGOS_VALORES = {
    "ayuda_social": "Que el trabajo sirva directamente a otras personas",
    "seguridad_economica": "Estabilidad y sueldo seguro por encima del riesgo",
    "autonomia_creativa": "Libertad para proponer ideas propias, sin un molde fijo",
    "justicia": "Que las cosas se hagan de forma justa y pareja para todos",
}
_VALORES = [
    ("Me da satisfacción sentir que mi trabajo ayuda directamente a otras personas.", "ayuda_social", 1),
    ("Elegiría un trabajo con menor sueldo si eso significa apoyar a quienes lo necesitan.", "ayuda_social", 1),
    ("Me interesa más ayudar a alguien en concreto que resolver un problema abstracto.", "ayuda_social", 1),
    ("Prefiero una carrera con salida laboral segura antes que una arriesgada.", "seguridad_economica", 1),
    ("Me preocupa más la estabilidad económica de un trabajo que lo emocionante que sea.", "seguridad_economica", 1),
    ("Un buen sueldo es más importante para mí que disfrutar cada tarea del día.", "seguridad_economica", 1),
    ("Prefiero trabajos donde pueda proponer mis propias ideas antes que seguir un manual.", "autonomia_creativa", 1),
    ("Me atrae más un trabajo flexible que uno con horario y reglas fijas.", "autonomia_creativa", 1),
    ("Valoro más la libertad para crear que seguir un proceso ya establecido.", "autonomia_creativa", 1),
    ("Me indigna ver que alguien reciba un trato injusto, aunque no me afecte a mí.", "justicia", 1),
    ("Creo que las reglas deben aplicarse igual para todos, sin excepciones.", "justicia", 1),
    ("Me interesa que mi futuro trabajo contribuya a que las cosas sean más justas.", "justicia", 1),
]

# --- Estilo cognitivo: cómo piensa (gana el rasgo con mayor puntaje) ---
RASGOS_ESTILO = {
    "logico_estructurado": "Lógico y estructurado: pasos ordenados, procesos claros",
    "creativo_intuitivo": "Creativo e intuitivo: ideas nuevas, se guía por corazonadas",
    "practico_manual": "Práctico y manual: aprende haciendo, resultados concretos",
    "analitico_critico": "Analítico y crítico: cuestiona, compara y sopesa antes de decidir",
}
_ESTILO = [
    ("Prefiero resolver problemas siguiendo pasos ordenados y comprobables.", "logico_estructurado", 1),
    ("Me gusta que las cosas tengan una explicación lógica y clara.", "logico_estructurado", 1),
    ("Disfruto armar o seguir procedimientos paso a paso.", "logico_estructurado", 1),
    ("Prefiero dejarme guiar por la intuición antes que por un método fijo.", "creativo_intuitivo", 1),
    ("Se me ocurren ideas nuevas con facilidad, aunque no sepa explicarlas del todo.", "creativo_intuitivo", 1),
    ("Disfruto imaginar posibilidades distintas a lo que ya existe.", "creativo_intuitivo", 1),
    ("Aprendo mejor haciendo algo con mis manos que leyendo sobre ello.", "practico_manual", 1),
    ("Prefiero construir o arreglar cosas antes que hablar sobre cómo hacerlas.", "practico_manual", 1),
    ("Me gusta ver resultados concretos de lo que hago, no solo ideas.", "practico_manual", 1),
    ("Me gusta cuestionar la información antes de aceptarla como cierta.", "analitico_critico", 1),
    ("Disfruto comparar distintos puntos de vista antes de decidir algo.", "analitico_critico", 1),
    ("Prefiero analizar los pros y contras antes de tomar una decisión.", "analitico_critico", 1),
]

DIMENSIONES = ("personalidad", "valores", "estilo_cognitivo")

# ITEMS: (id local 1..48, enunciado, dimension, rasgo, signo). Los ids de
# personalidad son los originales de psicometrico.PERSONALIDAD (para no
# duplicar texto); valores/estilo usan ids nuevos 100+.
ITEMS: list[tuple[int, str, str, str, int]] = []
for rasgo, ids in _IDS_PERSONALIDAD.items():
    for i in ids:
        t, r, s = _POR_ID[i]
        assert r == rasgo
        ITEMS.append((i, t, "personalidad", rasgo, s))
for n, (t, r, s) in enumerate(_VALORES):
    ITEMS.append((200 + n, t, "valores", r, s))
for n, (t, r, s) in enumerate(_ESTILO):
    ITEMS.append((300 + n, t, "estilo_cognitivo", r, s))

RASGOS_TODOS = {**RASGOS, **RASGOS_VALORES, **RASGOS_ESTILO}


def preguntas() -> dict:
    """Banco para el frontend: id, texto y dimensión (sin rasgo/signo, es
    detalle interno del scoring)."""
    return {
        "escala": ESCALA,
        "dimensiones": DIMENSIONES,
        "preguntas": [
            {"id": i, "dimension": d, "texto": t} for i, t, d, _, _ in ITEMS
        ],
    }


def valida(respuestas: dict[int, int]) -> bool:
    """Frontera de confianza: los 48 ítems respondidos, valores 1-5."""
    ids = {i for i, *_ in ITEMS}
    return set(respuestas) == ids and all(1 <= v <= 5 for v in respuestas.values())


def _puntaje_rasgo(respuestas: dict[int, int], dimension: str) -> dict[str, int]:
    items_dim = [(i, r, s) for i, _, d, r, s in ITEMS if d == dimension]
    rasgos = sorted({r for _, r, _ in items_dim})
    salida = {}
    for rasgo in rasgos:
        items = [(i, s) for i, r, s in items_dim if r == rasgo]
        crudo = sum(respuestas[i] if s == 1 else 6 - respuestas[i] for i, s in items)
        salida[rasgo] = round((crudo - len(items)) / (4 * len(items)) * 100)
    return salida


def calificar(respuestas: dict[int, int]) -> dict:
    """respuestas: {id_item: 1..5}. Devuelve puntaje 0-100 por rasgo en cada
    una de las 3 dimensiones, más el estilo cognitivo dominante."""
    personalidad = _puntaje_rasgo(respuestas, "personalidad")
    valores = _puntaje_rasgo(respuestas, "valores")
    estilo = _puntaje_rasgo(respuestas, "estilo_cognitivo")
    return {
        "personalidad": personalidad,
        "valores": valores,
        "estilo_cognitivo": estilo,
        "estilo_dominante": max(estilo, key=estilo.get),
    }


def bloque(puntajes: dict) -> str:
    """Texto que ve Gemini cuando el alumno hizo este test antes del chat.
    Mismo rol que `holland.bloque()`: da contexto, no filtra el catálogo."""
    def _lineas(titulo: str, rasgos: dict, etiquetas: dict) -> list[str]:
        orden = sorted(rasgos, key=lambda r: -rasgos[r])
        out = [f"{titulo} (0 a 100; lo que orienta es el contraste entre rasgos):"]
        out += [f"- {etiquetas[r]}: {rasgos[r]}" for r in orden]
        return out

    lineas = [
        "PERFIL DE PERSONALIDAD, VALORES Y ESTILO COGNITIVO YA MEDIDO "
        "(test corto respondido antes del chat, ya calificado):",
        *_lineas("PERSONALIDAD", puntajes["personalidad"], RASGOS),
        *_lineas("VALORES", puntajes["valores"], RASGOS_VALORES),
        *_lineas("ESTILO COGNITIVO", puntajes["estilo_cognitivo"], RASGOS_ESTILO),
        f"Estilo cognitivo dominante: {RASGOS_ESTILO[puntajes['estilo_dominante']]}.",
    ]
    return "\n".join(lineas)


def _self_check():
    assert len(ITEMS) == 48, len(ITEMS)
    assert len({i for i, *_ in ITEMS}) == 48, "ids de ítems repetidos"
    for dim in DIMENSIONES:
        assert sum(1 for _, _, d, _, _ in ITEMS if d == dim) in (12, 24), dim

    alto = {i: 5 for i, *_ in ITEMS}
    p = calificar(alto)
    assert p["personalidad"]["organizacion"] == 100  # todo signo 1 en ese rasgo
    assert p["personalidad"]["apertura"] < 100  # tiene 1 ítem invertido (id 4)
    assert p["valores"]["ayuda_social"] == 100
    assert p["estilo_cognitivo"]["logico_estructurado"] == 100

    bajo = {i: 1 for i, *_ in ITEMS}
    assert calificar(bajo)["valores"]["justicia"] == 0

    assert valida(alto) and not valida({i: 5 for i, *_ in ITEMS[:47]})
    assert not valida({**alto, ITEMS[0][0]: 6})

    b = bloque(p)
    assert "PERSONALIDAD" in b and "VALORES" in b and "ESTILO COGNITIVO" in b
    assert RASGOS_ESTILO[p["estilo_dominante"]] in b

    print(f"personalidad self-check OK — {len(ITEMS)} ítems, 3 dimensiones, sin llamadas a Gemini")


if __name__ == "__main__":
    _self_check()
