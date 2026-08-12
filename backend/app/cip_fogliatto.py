"""CIP de Fogliatto — Cuestionario de Intereses Profesionales (150 ítems, 15 escalas).

Instrumento argentino, con clave de escalas y baremos de muestras latinoamericanas.
Es el que mejor se ajusta a la población guatemalteca de los tres candidatos
evaluados; el CIP español (`cip.py`) queda como alterno.

Cero IA: la calificación es aritmética auditable. El evaluado marca Desagrado (1),
Indiferencia (2) o Agrado (3) en cada ítem; se suman los ítems de cada escala y la
puntuación directa se convierte a percentil con el baremo. Eso es lo que hace la
recomendación defendible: el perfil sale de un instrumento, no del criterio del
modelo de lenguaje.

ponytail: AUTORIZACIÓN PENDIENTE — prototipo para revisión y aval del asesor y de la
profesional colegiada. No aplicar a estudiantes ni desplegar sin permiso escrito del
titular de los derechos y sin supervisión profesional formalizada. Ver
`documento-tesis/formatos-etica.md` y `documento-tesis/carta-autores-cip-r.md`.

Self-check sin API: uv run python -m app.cip_fogliatto
"""

import json
from pathlib import Path

_DATOS = Path(__file__).resolve().parents[1] / "data" / "tests"

def _leer(ruta):
    """Los bancos de ítems no viajan en el repo (ver .gitignore): reproducen un
    instrumento con derechos de autor cuya autorización está pendiente. Sin este
    aviso, un clon nuevo moría con un FileNotFoundError que no explica nada."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta.name}. El banco de ítems no se versiona por derechos de "
            f"autor del instrumento. Copia el archivo real a {ruta.parent} con ese "
            f"nombre; la estructura que espera el código está en {ruta.name}.example."
        )
    return json.loads(ruta.read_text(encoding="utf-8"))


_ITEMS = _leer(_DATOS / "cip_fogliatto_items.json")
_BAREMOS = json.loads((_DATOS / "cip_fogliatto_baremos.json").read_text(encoding="utf-8"))

ESCALAS = _ITEMS["escalas"]
ITEMS = _ITEMS["items"]
N_ITEMS = len(ITEMS)  # 150

# Desagrado / Indiferencia / Agrado. El manual no admite ítems sin responder.
VALOR = {"D": 1, "I": 2, "A": 3}

# {número de ítem: romano de su escala}, derivado de la clave del manual.
_ESCALA_DE = {n: e["romano"] for e in ESCALAS for n in e["items"]}

# La muestra de referencia por defecto es la de secundarios de distintas regiones del
# país: es la más cercana a estudiantes de diversificado de Quetzaltenango y
# Totonicapán, más que la de la ciudad de Córdoba o la de ingresantes universitarios.
MUESTRA_DEFAULT = "secundarios-regiones"


def _tabla(sexo: str, muestra: str) -> dict:
    for tb in _BAREMOS["tablas"].values():
        if tb["sexo"] == sexo and tb["muestra"] == muestra:
            return tb
    raise ValueError(f"no hay baremo para sexo={sexo!r}, muestra={muestra!r}")


def percentil(directa: int, escala: str, sexo: str, muestra: str = MUESTRA_DEFAULT) -> int:
    """Percentil de una puntuación directa en una escala.

    El baremo da, por percentil, la puntuación mínima que lo alcanza. El percentil del
    evaluado es el mayor cuyo corte no supera su puntuación.
    """
    tb = _tabla(sexo, muestra)
    cortes = tb["cortes"][escala]
    for pc, corte in zip(tb["percentiles"], cortes):
        if directa >= corte:
            return pc
    return tb["percentiles"][-1]


def preguntas() -> dict:
    """Lo que necesita el frontend para presentar el test."""
    return {
        "escala_respuesta": _ITEMS["_escala"],
        "escalas": [{k: e[k] for k in ("n", "romano", "nombre", "definicion")} for e in ESCALAS],
        "items": [{"n": i + 1, "texto": t} for i, t in enumerate(ITEMS)],
        "sin_limite_tiempo": True,
    }


def calificar(respuestas: dict[int, str], sexo: str,
              muestra: str = MUESTRA_DEFAULT) -> dict:
    """Califica el CIP completo.

    `respuestas` es {número de ítem: "D" | "I" | "A"}. El manual es explícito en que
    no puede quedar ningún ítem sin responder, así que una respuesta faltante es error
    de entrada y no algo que se rellene con un valor por defecto.
    """
    if sexo not in ("masculino", "femenino"):
        # El instrumento solo trae baremos por sexo; no hay tabla combinada. Es una
        # limitación del baremo original, no una decisión de diseño de este módulo.
        raise ValueError(f"sexo no válido: {sexo!r}")
    faltan = [n for n in range(1, N_ITEMS + 1) if n not in respuestas]
    if faltan:
        raise ValueError(f"faltan {len(faltan)} ítems por responder: {faltan[:10]}")
    malos = {n: v for n, v in respuestas.items() if v not in VALOR}
    if malos:
        raise ValueError(f"respuestas fuera de la escala D/I/A: {dict(list(malos.items())[:10])}")

    directas: dict[str, int] = {}
    conteo: dict[str, dict[str, int]] = {}
    for n, v in respuestas.items():
        rom = _ESCALA_DE[n]
        directas[rom] = directas.get(rom, 0) + VALOR[v]
        c = conteo.setdefault(rom, {"D": 0, "I": 0, "A": 0})
        c[v] += 1

    perfil = []
    for e in ESCALAS:
        rom = e["romano"]
        perfil.append({
            "escala": e["n"],
            "romano": rom,
            "nombre": e["nombre"],
            "definicion": e["definicion"],
            "n_items": len(e["items"]),
            "directa": directas[rom],
            "percentil": percentil(directas[rom], rom, sexo, muestra),
            "conteo": conteo[rom],
        })
    orden = sorted(perfil, key=lambda c: (-c["percentil"], -c["directa"], c["escala"]))
    tb = _tabla(sexo, muestra)

    return {
        "perfil": perfil,                          # en orden de escala, para la gráfica
        "dominantes": [c["escala"] for c in orden[:3]],
        "patron": _patron(perfil),
        "baremo": {"sexo": sexo, "muestra": muestra, "n": tb["n"]},
    }


# ponytail: cortes en percentil 75/25 y conteos fijos. El manual describe estos casos
# en prosa, no con umbrales; si la profesional que supervise los afina al revisar los
# primeros casos reales, se cambian aquí y en ninguna otra parte.
def _patron(perfil: list[dict]) -> dict:
    altos = [c["escala"] for c in perfil if c["percentil"] >= 75]
    bajos = [c["escala"] for c in perfil if c["percentil"] <= 25]
    if len(altos) >= 8:
        clave, nota = "disperso", ("Puntuaciones altas en la mayoría de las escalas: falta "
                                   "contraste. El consejo orientador es arriesgado; conviene "
                                   "entrevista.")
    elif not altos:
        clave, nota = "indefinido", ("Ninguna escala destaca. Puede tratarse de un joven muy "
                                     "selectivo o de una fase de indecisión: revisar en "
                                     "entrevista.")
    elif len(altos) <= 3:
        clave, nota = "definido", "Atracción marcada por una o pocas áreas concretas."
    else:
        clave, nota = "nucleo", ("Intereses firmes en un núcleo de áreas afines, sin concretar "
                                 "todavía en una.")
    return {"clave": clave, "nota": nota, "altos": altos, "bajos": bajos}


def sinceridad(respuestas: dict[int, str]) -> dict:
    """Control de calidad de las respuestas.

    El CIP no trae escala de deseabilidad social ni pares de consistencia, así que un
    protocolo contestado sin leer produce un perfil inservible y el instrumento no
    avisa. Esto no lo convierte en otro test: solo evita que un perfil plano llegue al
    tablero como si fuera una recomendación.
    """
    total = len(respuestas)
    conteo = {v: sum(1 for r in respuestas.values() if r == v) for v in VALOR}
    dominante = max(conteo, key=conteo.get)
    pct = round(100 * conteo[dominante] / total) if total else 0
    # Rachas de la misma respuesta seguidas, en el orden del cuadernillo.
    racha = mayor = 0
    previo = None
    for n in sorted(respuestas):
        racha = racha + 1 if respuestas[n] == previo else 1
        previo = respuestas[n]
        mayor = max(mayor, racha)
    alerta = pct >= 80 or mayor >= 25
    return {"reparto": conteo, "dominante": dominante, "pct_dominante": pct,
            "racha_maxima": mayor, "alerta": alerta,
            "nota": ("El patrón de respuestas sugiere que el cuestionario no se contestó "
                     "con atención; conviene verificarlo antes de usar el perfil."
                     if alerta else "Sin indicios de respuesta descuidada.")}


def _self_check():
    assert N_ITEMS == 150 and len(ESCALAS) == 15
    assert len(set(ITEMS)) == N_ITEMS, "hay ítems duplicados en la transcripción"
    assert all(t.strip().endswith(".") for t in ITEMS), "algún ítem quedó truncado"

    # La clave del manual cubre los 150 ítems, una sola vez cada uno.
    assert sorted(_ESCALA_DE) == list(range(1, N_ITEMS + 1))
    assert sum(len(e["items"]) for e in ESCALAS) == N_ITEMS

    # Asignaciones verificadas a mano contra el protocolo impreso, una por escala.
    for n, rom in [(4, "I"), (12, "II"), (7, "III"), (11, "IV"), (15, "V"), (8, "VI"),
                   (9, "VII"), (21, "VIII"), (3, "IX"), (13, "X"), (19, "XI"),
                   (28, "XII"), (1, "XIII"), (2, "XIV"), (33, "XV")]:
        assert _ESCALA_DE[n] == rom, f"ítem {n}: esperaba {rom}, dio {_ESCALA_DE[n]}"

    # Los tres protocolos resueltos del manual, que fijan la equivalencia D=1/I=2/A=3.
    # (escala, D, I, A, puntuación directa impresa)
    for rom, d, i, a, esperado in [("V", 10, 0, 0, 10), ("VIII", 5, 3, 2, 17),
                                   ("IX", 4, 1, 4, 18), ("VII", 9, 0, 1, 12),
                                   ("I", 4, 0, 5, 19)]:
        n_items = len(next(e for e in ESCALAS if e["romano"] == rom)["items"])
        assert d + i + a == n_items, (rom, d, i, a, n_items)
        assert d * 1 + i * 2 + a * 3 == esperado, rom

    # Todo Desagrado deja cada escala en su mínimo (n ítems × 1) y todo Agrado en 3n.
    for resp, factor in (("D", 1), ("A", 3)):
        r = calificar({n: resp for n in range(1, N_ITEMS + 1)}, sexo="femenino")
        for c in r["perfil"]:
            assert c["directa"] == c["n_items"] * factor, (c["romano"], c["directa"])
    assert calificar({n: "D" for n in range(1, N_ITEMS + 1)},
                     sexo="femenino")["patron"]["clave"] == "indefinido"
    assert calificar({n: "A" for n in range(1, N_ITEMS + 1)},
                     sexo="femenino")["patron"]["clave"] == "disperso"

    # Un interés marcado en Biosanitaria (VII) tiene que salir primero y arriba.
    r = calificar({n: ("A" if _ESCALA_DE[n] == "VII" else "D") for n in range(1, N_ITEMS + 1)},
                  sexo="masculino")
    vii = next(c for c in r["perfil"] if c["romano"] == "VII")
    assert vii["nombre"] == "Biosanitaria" and vii["directa"] == 30
    assert r["dominantes"][0] == vii["escala"] and vii["percentil"] == 99
    assert r["patron"]["clave"] == "definido"

    # El baremo importa: la misma directa no rinde igual en distinto sexo ni muestra.
    assert percentil(20, "IV", "masculino") != percentil(20, "IV", "femenino")
    assert (percentil(20, "I", "masculino", "secundarios-cordoba")
            != percentil(20, "I", "masculino", "ingresantes-cordoba"))
    # Y una puntuación por debajo del corte más bajo cae en el percentil mínimo.
    assert percentil(8, "XV", "femenino") == 1

    # Entradas inválidas se rechazan, no se rellenan.
    for malo, sexo in (({n: "A" for n in range(1, N_ITEMS)}, "femenino"),
                       ({n: "X" for n in range(1, N_ITEMS + 1)}, "femenino"),
                       ({n: "A" for n in range(1, N_ITEMS + 1)}, "ambos")):
        try:
            calificar(malo, sexo=sexo)
        except ValueError:
            pass
        else:
            raise AssertionError("aceptó una entrada inválida")

    # Control de sinceridad: todo igual alerta; un patrón repartido, no.
    assert sinceridad({n: "A" for n in range(1, N_ITEMS + 1)})["alerta"] is True
    variado = {n: "DIA"[n % 3] for n in range(1, N_ITEMS + 1)}
    assert sinceridad(variado)["alerta"] is False
    # ...y una racha larga alerta aunque el reparto global se vea sano.
    racha = dict(variado)
    racha.update({n: "A" for n in range(1, 31)})
    assert sinceridad(racha)["alerta"] is True

    print(f"CIP-Fogliatto self-check OK — {N_ITEMS} ítems, {len(ESCALAS)} escalas, "
          f"6 baremos, calificación D=1/I=2/A=3 consistente con el manual")


if __name__ == "__main__":
    _self_check()
