"""Prioriza el catálogo con el perfil RIASEC del alumno, antes de Gemini.

EXPERIMENTAL. Apagado por defecto: se activa con `HOLLAND_EN_RECOMENDACION=1` en
`backend/.env`. Con el flag apagado, `recomendar()` se comporta exactamente como
hoy. Ver `experiments/holland-estructura.md`.

## Por qué existe

El bloque de texto con el resultado de Holland en el prompt **no mueve la
recomendación**: medido, en 5 de 6 corridas el top-1 fue de otra área que la más
alta del perfil (`experiments/holland-en-chat.md` §5.2). Un bloque de prosa es
contexto, no peso. Si Holland tiene que pesar, entra como **estructura**: cada
carrera con su vector RIASEC y el catálogo ordenado por afinidad.

Los vectores los produce `codificar_holland.py` desde O*NET — la misma fuente
que califica el test del alumno, no un modelo inventándolos. Esa es la ventaja
que el CIP no tenía.

## Cómo se mide la afinidad

**Correlación** entre los seis puntajes del alumno (0-40) y los seis de la
carrera (0-100), no producto punto: lo que orienta es el CONTRASTE entre áreas,
no el nivel general. Sin centrar, una carrera con las seis áreas altas le gana a
todas para cualquier alumno.

Una carrera sin codificar recibe 0.0 — el centro del rango, ni premiada ni
castigada: un hueco de datos no es culpa del estudiante.

## Prioriza, no filtra: por defecto NO corta

`cip_filtro` cortaba en 30. Acá el corte viene apagado (`TOP_HOLLAND = 0`) porque
medirlo mostró que se lleva por delante la carrera correcta — ver el comentario
de la constante y `experiments/holland-estructura.md`. Ordenar sin cortar es
prioridad real (Gemini lee el catálogo en ese orden) sin poder excluir a nadie,
que es lo que `filtro.py` ya documenta para `/recommend`.

Self-check: `uv run python -m app.holland_filtro`
"""

import json
import os
from pathlib import Path

_RUTA = Path(__file__).resolve().parents[1] / "data" / "holland_catalogo.json"
VECTORES = json.loads(_RUTA.read_text(encoding="utf-8")) if _RUTA.exists() else {}

# 0 = ordenar SIN cortar, y es el default a propósito. Medido antes de correr el
# A/B: con un corte en 30 registros, el catálogo ordenado por afinidad deja fuera
# la carrera correcta del perfil artístico (Diseño Gráfico cae al puesto 59,
# porque su vector es A+E+C y la alumna es A+S). Es el mismo accidente que ya
# había dejado apagado el recorte al sector. Ordenar sin cortar conserva la
# prioridad —Gemini lee el catálogo en ese orden— sin poder excluir a nadie.
# Ver experiments/holland-estructura.md.
TOP_HOLLAND = int(os.getenv("HOLLAND_TOP", "0"))
LETRAS = "RIASEC"


def activo() -> bool:
    """Se lee en cada llamada, no al importar: apagarlo no exige reiniciar."""
    return os.getenv("HOLLAND_EN_RECOMENDACION", "0") == "1"


def _clave(carrera) -> str:
    """Misma convención que `cip_filtro._clave` y que la codificación."""
    return getattr(carrera, "perfil_grupo", None) or f"{carrera.centro}::{carrera.nombre}"


def vector_de(carrera) -> dict | None:
    e = VECTORES.get(_clave(carrera))
    return e["vector"] if e else None


def _correlacion(a: dict, b: dict) -> float:
    """Correlación de Pearson entre dos vectores RIASEC (-1 a 1)."""
    xs = [float(a.get(l, 0)) for l in LETRAS]
    ys = [float(b.get(l, 0)) for l in LETRAS]
    mx, my = sum(xs) / 6, sum(ys) / 6
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = (sum(x * x for x in dx) ** 0.5) * (sum(y * y for y in dy) ** 0.5)
    # Un perfil perfectamente plano no tiene contraste que correlacionar.
    return 0.0 if den == 0 else sum(x * y for x, y in zip(dx, dy)) / den


def afinidad(carrera, puntajes: dict[str, int]) -> float:
    """Qué tan afín es una carrera al perfil RIASEC del alumno, de -1 a 1.

    `puntajes` es {letra: 0-40}, los seis del Interest Profiler.
    """
    v = vector_de(carrera)
    return 0.0 if v is None else _correlacion(puntajes, v)


def priorizar(carreras: list, puntajes: dict[str, int], top: int | None = None) -> list:
    """Ordena el catálogo por afinidad RIASEC. Corta en `top`; 0 = sin cortar."""
    top = TOP_HOLLAND if top is None else top
    ordenadas = sorted(carreras, key=lambda c: afinidad(c, puntajes), reverse=True)
    return ordenadas[:top] if top else ordenadas


def _self_check():
    class _C:
        def __init__(self, nombre, grupo=None, centro="X"):
            self.nombre, self.perfil_grupo, self.centro = nombre, grupo, centro

    assert len(VECTORES) >= 80, f"catálogo RIASEC incompleto: {len(VECTORES)}"
    assert all(len(v["vector"]) == 6 and len(v["codigo"]) == 3 for v in VECTORES.values())

    assert _clave(_C("Médico", "medico_cirujano")) == "medico_cirujano"
    assert _clave(_C("Economía", None, "CUNOC")) == "CUNOC::Economía"

    # La correlación mira el contraste, no el nivel: el mismo perfil escalado da 1.
    v = {"R": 10, "I": 20, "A": 30, "S": 40, "E": 5, "C": 15}
    assert abs(_correlacion(v, {l: x * 2 for l, x in v.items()}) - 1.0) < 1e-9
    assert abs(_correlacion(v, {l: 50 for l in LETRAS})) < 1e-9  # carrera plana: neutral
    assert _correlacion(v, {l: -x for l, x in v.items()}) < -0.99

    med = _C("Médico y Cirujano", "medico_cirujano")
    dis = _C("Publicidad con Especialidad en Diseño Gráfico", "diseno_grafico")
    assert vector_de(med) and vector_de(dis), "faltan las dos carreras del self-check"
    artista = {"R": 12, "I": 10, "A": 39, "S": 38, "E": 10, "C": 19}  # el perfil de Dulce
    cientifico = {"R": 20, "I": 39, "A": 5, "S": 30, "E": 10, "C": 20}
    assert afinidad(dis, artista) > afinidad(med, artista)
    assert afinidad(med, cientifico) > afinidad(dis, cientifico)
    # Sin codificar = 0.0, ni arriba ni abajo del todo.
    assert afinidad(_C("Inventada", "no_existe"), artista) == 0.0
    lista = [med, dis, _C("Inventada", "no_existe")]
    assert priorizar(lista, artista, top=2)[0] is dis
    assert len(priorizar(lista, artista, top=99)) == 3
    assert len(priorizar(lista, artista, top=0)) == 3  # 0 = sin cortar

    print(f"holland_filtro self-check OK — {len(VECTORES)} carreras con vector RIASEC, "
          f"flag {'ACTIVO' if activo() else 'apagado'}, TOP_HOLLAND={TOP_HOLLAND}")


if __name__ == "__main__":
    _self_check()
