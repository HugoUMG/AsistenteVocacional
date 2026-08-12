"""CIP — Cuestionario de Intereses Profesionales (216 ítems, 18 campos).

Instrumento real, con baremos publicados. A diferencia de `psicometrico.py`,
este SÍ está pensado para alimentar la recomendación: mide intereses, que es
justo lo que el chat venía estimando por su cuenta.

ponytail: AUTORIZACIÓN PENDIENTE — el manual lo facilitó una estudiante de
psicología, no la profesional colegiada, y al 2026-08-11 no hay permiso de uso
ni supervisión formalizada. El módulo califica, pero no se conecta a ningún
endpoint ni se aplica a estudiantes hasta tener ese permiso por escrito. Ver
`documento-tesis/formatos-etica.md`.

Cero IA: la calificación es aritmética auditable. Suma por campo → puntuación
directa (12-60) → percentil según el baremo de edad y sexo. Eso es lo que
convierte la recomendación en algo defendible ante un tribunal.

El banco de ítems y los baremos viven en `data/tests/`. Aquí solo la mecánica.

Self-check sin API: uv run python -m app.cip
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


_ITEMS = _leer(_DATOS / "cip_items.json")
_BAREMOS = json.loads((_DATOS / "cip_baremos.json").read_text(encoding="utf-8"))

CAMPOS = _ITEMS["campos"]
ITEMS = _ITEMS["items"]
ESCALA = _ITEMS["_escala"]
N_CAMPOS = len(CAMPOS)          # 18
N_ITEMS = len(ITEMS)            # 216
POR_CAMPO = N_ITEMS // N_CAMPOS  # 12 ítems por campo → directa entre 12 y 60

# El cuadernillo recorre los campos en ciclo. No hay tabla de correspondencia
# que mantener: es una fórmula, y el self-check la contrasta contra el cuadernillo.
def campo_de(item: int) -> int:
    """Número de campo (1-18) al que pertenece el ítem (1-216)."""
    return (item - 1) % N_CAMPOS + 1


def grupo_edad(edad: int) -> tuple[str, bool]:
    """Devuelve (clave del baremo, si la edad quedó fuera del rango tipificado)."""
    if edad <= 15:
        return "14-15", edad < 14
    if edad == 16:
        return "16", False
    if edad == 17:
        return "17", False
    return "18-19", edad > 19


def percentil(directa: int, edad: int, sexo: str = "ambos") -> int:
    """Percentil de una puntuación directa. El baremo tope es 58+."""
    grupo, _ = grupo_edad(edad)
    tabla = _BAREMOS["grupos"][grupo][sexo]
    return tabla[58 - min(directa, 58)]


def preguntas() -> dict:
    """Lo que necesita el frontend para presentar el test."""
    return {
        "escala": ESCALA,
        "campos": CAMPOS,
        "items": [{"n": i + 1, "texto": t} for i, t in enumerate(ITEMS)],
        "sin_limite_tiempo": True,
    }


def calificar(respuestas: dict[int, int], edad: int, sexo: str = "ambos") -> dict:
    """Califica el CIP completo.

    `respuestas` es {número de ítem: 1-5}. El manual es explícito: no valen
    ceros ni seises, y no puede quedar ninguna cuestión sin responder, así que
    ambas cosas son error de entrada y no algo que se rellene por defecto.
    """
    if sexo not in ("ambos", "masculino", "femenino"):
        raise ValueError(f"sexo no válido: {sexo!r}")
    faltan = [n for n in range(1, N_ITEMS + 1) if n not in respuestas]
    if faltan:
        raise ValueError(f"faltan {len(faltan)} ítems por responder: {faltan[:10]}")
    malos = {n: v for n, v in respuestas.items() if not (isinstance(v, int) and 1 <= v <= 5)}
    if malos:
        raise ValueError(f"respuestas fuera de la escala 1-5: {dict(list(malos.items())[:10])}")

    grupo, fuera_baremo = grupo_edad(edad)
    directas = [0] * N_CAMPOS
    for n, v in respuestas.items():
        directas[campo_de(n) - 1] += v

    perfil = []
    for campo in CAMPOS:
        d = directas[campo["n"] - 1]
        perfil.append({
            "campo": campo["n"],
            "nombre": campo["nombre"],
            "profesiones": campo["profesiones"],
            "directa": d,
            "percentil": percentil(d, edad, sexo),
        })
    orden = sorted(perfil, key=lambda c: (-c["percentil"], -c["directa"], c["campo"]))

    return {
        "perfil": perfil,                       # en orden de campo, para la gráfica
        "dominantes": [c["campo"] for c in orden[:3]],
        "patron": _patron(perfil),
        "baremo": {"grupo": grupo, "sexo": sexo, "n": _BAREMOS["grupos"][grupo]["n"][sexo],
                   "fuera_de_rango": fuera_baremo},
    }


# Los tres casos típicos que describe el manual en "criterios de interpretación".
# ponytail: cortes en percentil 75/25 y conteos fijos, no una regla del manual —
# el manual los describe en prosa. Si la licenciada afina los cortes al revisar
# los primeros casos reales, se cambian aquí y nada más.
def _patron(perfil: list[dict]) -> dict:
    altos = [c["campo"] for c in perfil if c["percentil"] >= 75]
    bajos = [c["campo"] for c in perfil if c["percentil"] <= 25]
    if len(altos) >= 9:
        clave, nota = "disperso", ("Puntuaciones altas en la mayoría de campos: falta contraste. "
                                   "El consejo orientador es arriesgado; conviene entrevista.")
    elif not altos:
        clave, nota = "indefinido", ("Ningún campo destaca. Puede ser un joven muy selectivo o una "
                                     "fase de indecisión o inhibición: revisar en entrevista.")
    elif len(altos) <= 3:
        clave, nota = "definido", "Atracción marcada por uno o pocos campos concretos."
    else:
        clave, nota = "nucleo", "Intereses firmes en un núcleo de campos afines, sin concretar aún en uno."
    return {"clave": clave, "nota": nota, "altos": altos, "bajos": bajos}


def erratas_baremos() -> list[str]:
    """Tramos no monótonos en los baremos impresos (a más puntos, menos percentil).

    No se corrigen automáticamente: se listan para que la profesional decida.
    """
    fallos = []
    for grupo, tablas in _BAREMOS["grupos"].items():
        for sexo in ("ambos", "masculino", "femenino"):
            pcs = tablas[sexo]
            for i in range(len(pcs) - 1):
                if pcs[i] < pcs[i + 1]:
                    fallos.append(f"{grupo}/{sexo}: X={58 - i} da Pc {pcs[i]}, "
                                  f"pero X={57 - i} da Pc {pcs[i + 1]}")
    return fallos


def _self_check():
    assert N_ITEMS == 216 and N_CAMPOS == 18 and POR_CAMPO == 12
    assert len(set(ITEMS)) == N_ITEMS, "hay ítems duplicados en la transcripción"
    assert all(t.strip().endswith(".") for t in ITEMS), "algún ítem quedó truncado"

    # Cada campo recibe exactamente 12 ítems.
    reparto = [0] * N_CAMPOS
    for n in range(1, N_ITEMS + 1):
        reparto[campo_de(n) - 1] += 1
    assert reparto == [POR_CAMPO] * N_CAMPOS, reparto

    # La fórmula del ciclo contra el cuadernillo: ítems verificados a mano,
    # repartidos por las cuatro páginas de ítems. Si alguien reordena el banco,
    # esto truena antes de que se califique mal a un alumno.
    for n, campo in [(1, 1), (4, 4), (8, 8), (18, 18), (34, 16), (36, 18),
                     (54, 18), (76, 4), (92, 2), (102, 12), (108, 18),
                     (126, 18), (164, 2), (170, 8), (184, 4), (202, 4), (216, 18)]:
        assert campo_de(n) == campo, f"ítem {n}: esperaba campo {campo}, dio {campo_de(n)}"

    # Todos los baremos tienen las 47 filas de X=58 a X=12.
    for grupo, tablas in _BAREMOS["grupos"].items():
        for sexo in ("ambos", "masculino", "femenino"):
            assert len(tablas[sexo]) == 47, (grupo, sexo, len(tablas[sexo]))

    # Calificación: todo en 3 deja las 18 directas en 36 y el mismo percentil.
    r = calificar({n: 3 for n in range(1, N_ITEMS + 1)}, edad=17)
    assert all(c["directa"] == 36 for c in r["perfil"])
    assert len({c["percentil"] for c in r["perfil"]}) == 1
    assert r["patron"]["clave"] == "indefinido"

    # Un interés marcado en Sanidad (campo 4) tiene que salir primero y arriba.
    r = calificar({n: (5 if campo_de(n) == 4 else 1) for n in range(1, N_ITEMS + 1)}, edad=17)
    sanidad = r["perfil"][3]
    assert sanidad["nombre"] == "Sanidad" and sanidad["directa"] == 60
    assert r["dominantes"][0] == 4 and sanidad["percentil"] == 99
    assert r["patron"]["clave"] == "definido"
    assert all(c["directa"] == 12 for c in r["perfil"] if c["campo"] != 4)

    # Todo en 5 es el caso "poco crítico" del manual, no un perfil de 18 vocaciones.
    assert calificar({n: 5 for n in range(1, N_ITEMS + 1)}, edad=17)["patron"]["clave"] == "disperso"

    # El baremo depende de edad y sexo: la misma directa no da el mismo percentil.
    assert percentil(40, 14) != percentil(40, 18)
    assert percentil(30, 17, "masculino") != percentil(30, 17, "femenino")
    assert percentil(60, 17) == percentil(58, 17) == 99, "el tope 58+ debe saturar"

    # Entradas inválidas se rechazan, no se rellenan.
    for malo in ({n: 3 for n in range(1, N_ITEMS)},            # falta el 216
                 {n: 0 for n in range(1, N_ITEMS + 1)},        # el manual: no valen ceros
                 {n: 6 for n in range(1, N_ITEMS + 1)}):       # ni seises
        try:
            calificar(malo, edad=17)
        except ValueError:
            pass
        else:
            raise AssertionError("aceptó respuestas inválidas")

    errs = erratas_baremos()
    print(f"CIP self-check OK — {N_ITEMS} ítems, {N_CAMPOS} campos, "
          f"4 baremos × 3 columnas, calificación consistente")
    if errs:
        print(f"\n  {len(errs)} tramo(s) no monótonos en los baremos IMPRESOS "
              f"(transcritos tal cual, pendientes de consulta):")
        for e in errs:
            print(f"    - {e}")


if __name__ == "__main__":
    _self_check()
