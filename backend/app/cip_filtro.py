"""Prioriza el catálogo con el perfil CIP del estudiante, antes de Gemini.

EXPERIMENTAL. Apagado por defecto: se activa con `CIP_EN_RECOMENDACION=1` en
`backend/.env`. Mientras esté apagado, `recomendar()` se comporta exactamente
como antes, así que revertir es poner la variable en 0 (o borrarla) — no hay que
deshacer código. Ver `experiments/cip-en-recomendacion.md`.

## Qué cambia

Hoy Gemini recibe el catálogo completo y el perfil en texto del chat, y decide.
Con esto, el recorte de candidatas sale del **percentil del instrumento**: si el
alumno puntúa alto en Biosanitaria (VII), las carreras VII suben; las de escalas
donde puntuó bajo, bajan. Gemini sigue redactando y ordenando el top final, pero
ya no elige el conjunto sobre el que trabaja.

## Por qué priorizar y no filtrar duro

`filtro.py` documenta que `recommend()` a propósito NO recorta, para no excluir
una carrera válida de la respuesta final. Aquí se conserva ese criterio: se
**ordena por congruencia y se corta en TOP_CIP**, que es holgado (30 de 90
perfiles). Un recorte agresivo haría el sistema más "auditable" y más frágil a la
vez: bastaría un percentil mal calibrado para que la carrera correcta no llegue
nunca a Gemini.
"""

import json
import os
from pathlib import Path

_RUTA = Path(__file__).resolve().parents[1] / "data" / "tests" / "cip_catalogo.json"
if not _RUTA.exists():  # el archivo real vive en data/, no en data/tests/
    _RUTA = Path(__file__).resolve().parents[1] / "data" / "cip_catalogo.json"

CODIGOS = json.loads(_RUTA.read_text(encoding="utf-8"))

TOP_CIP = int(os.getenv("CIP_TOP", "30"))
# La escala secundaria pesa la mitad: es un área relevante de la carrera, no la
# que define su actividad cotidiana.
PESO_SECUNDARIA = 0.5


def activo() -> bool:
    """Lee el flag en cada llamada, no al importar: así se puede apagar sin
    reiniciar el backend cuando el experimento vaya mal."""
    return os.getenv("CIP_EN_RECOMENDACION", "0") == "1"


def _clave(carrera) -> str | None:
    """La clave con que se codificó esta carrera. `perfil_grupo` es el mismo
    `perfil_id` que usa `perfiles_compartidos.json`; si no lo tiene, el perfil
    era inline y la clave se armó con centro y nombre."""
    if getattr(carrera, "perfil_grupo", None):
        return carrera.perfil_grupo
    return f"{carrera.centro}::{carrera.nombre}"


def codigo_de(carrera) -> dict | None:
    """{'principal', 'secundaria'} de una carrera, o None si no está codificada."""
    return CODIGOS.get(_clave(carrera))


def congruencia(carrera, percentiles: dict[str, int]) -> float:
    """Qué tan afín es una carrera al perfil CIP del estudiante.

    `percentiles` es {romano: 0-100}. Una carrera sin codificar devuelve el
    percentil medio: no se la premia ni se la castiga por un hueco de datos que
    no es culpa del estudiante.
    """
    cod = codigo_de(carrera)
    if not cod:
        return 50.0
    puntaje = float(percentiles.get(cod["principal"], 50))
    if cod["secundaria"]:
        puntaje += PESO_SECUNDARIA * percentiles.get(cod["secundaria"], 50)
    return puntaje


def priorizar(carreras: list, percentiles: dict[str, int], top: int = None) -> list:
    """Ordena el catálogo por congruencia con el perfil CIP y corta en `top`."""
    top = TOP_CIP if top is None else top
    ordenadas = sorted(carreras, key=lambda c: congruencia(c, percentiles), reverse=True)
    return ordenadas[:top]


def texto_perfil(perfil: list[dict]) -> str:
    """El perfil CIP como dato duro para el prompt.

    Va ordenado de mayor a menor percentil y con la definición de cada área: sin
    ella, "Escala VIII: 85" no le dice nada al modelo. Solo se mandan las áreas
    con algo que decir (Pc >= 60 o <= 25); el medio es ruido que ocupa tokens.
    """
    altas = [e for e in perfil if e["percentil"] >= 60]
    bajas = [e for e in perfil if e["percentil"] <= 25]
    altas.sort(key=lambda e: -e["percentil"])
    bajas.sort(key=lambda e: e["percentil"])

    lineas = ["RESULTADO DEL CUESTIONARIO DE INTERESES PROFESIONALES (CIP).",
              "Percentiles obtenidos por el estudiante en un instrumento psicométrico.",
              "Este dato es medido, no inferido de la conversación: tiene prioridad",
              "sobre lo que el estudiante haya dicho de pasada en el chat.", ""]
    if altas:
        lineas.append("Áreas de interés ALTO:")
        lineas += [f"  - {e['nombre']} (percentil {e['percentil']}): {e['definicion']}"
                   for e in altas]
    else:
        lineas.append("Ninguna área destacó con claridad: el perfil de intereses es plano,")
        lineas.append("así que conviene una recomendación amplia y con confianza baja.")
    if bajas:
        lineas.append("")
        lineas.append("Áreas RECHAZADAS (no recomendar carreras centradas en ellas):")
        lineas += [f"  - {e['nombre']} (percentil {e['percentil']})" for e in bajas]
    return "\n".join(lineas)


def _self_check():
    class _C:
        def __init__(self, nombre, grupo=None, centro="X"):
            self.nombre, self.perfil_grupo, self.centro = nombre, grupo, centro

    assert len(CODIGOS) >= 80, f"catálogo CIP incompleto: {len(CODIGOS)}"
    assert all(v["principal"] for v in CODIGOS.values())

    # La clave sale de perfil_grupo si existe, y de centro::nombre si no.
    assert _clave(_C("Médico", "medico_cirujano")) == "medico_cirujano"
    assert _clave(_C("Economía", None, "CUNOC")) == "CUNOC::Economía"

    med = _C("Médico y Cirujano", "medico_cirujano")
    assert codigo_de(med)["principal"] == "VII"
    assert codigo_de(_C("Inventada", "no_existe")) is None

    # Un alumno alto en Biosanitaria prefiere Medicina sobre Contaduría.
    alto_vii = {"VII": 95, "X": 10}
    conta = _C("Contaduría", "contaduria")
    assert congruencia(med, alto_vii) > congruencia(conta, alto_vii)
    # ...y al revés con el perfil invertido.
    alto_x = {"VII": 10, "X": 95}
    assert congruencia(conta, alto_x) > congruencia(med, alto_x)
    # Una carrera sin codificar queda en el medio, ni premiada ni castigada.
    assert congruencia(_C("Inventada", "no_existe"), alto_vii) == 50.0

    # priorizar respeta el orden y el corte.
    lista = [conta, med, _C("Inventada", "no_existe")]
    assert priorizar(lista, alto_vii, top=2)[0] is med
    assert len(priorizar(lista, alto_vii, top=2)) == 2
    assert len(priorizar(lista, alto_vii, top=99)) == 3

    # El texto del prompt separa altas de bajas y omite el medio.
    perfil = [{"nombre": "Biosanitaria", "percentil": 92, "definicion": "salud"},
              {"nombre": "Cálculo", "percentil": 45, "definicion": "números"},
              {"nombre": "Musical", "percentil": 8, "definicion": "música"}]
    t = texto_perfil(perfil)
    assert "Biosanitaria (percentil 92)" in t and "RECHAZADAS" in t and "Musical" in t
    assert "Cálculo" not in t, "el rango medio no debería ocupar tokens"
    plano = texto_perfil([{"nombre": "X", "percentil": 50, "definicion": "d"}])
    assert "perfil de intereses es plano" in plano

    print(f"cip_filtro self-check OK — {len(CODIGOS)} carreras codificadas, "
          f"flag {'ACTIVO' if activo() else 'apagado'}, TOP_CIP={TOP_CIP}")


if __name__ == "__main__":
    _self_check()
