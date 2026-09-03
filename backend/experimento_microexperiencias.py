"""Re-medición de las microexperiencias, con juez de coherencia y control.

En 2026-07-25 se implementó, midió y revirtió un cambio de prompt: preguntar por
ACTIVIDADES concretas ("¿qué tan agradable te parece atender pacientes?") en vez
de materias o gustos abstractos. Midió 6/10 contra 10/10 y se descartó
(`experiments/microexperiencias.md`).

## Por qué se vuelve a medir

Aquel veredicto salió con el criterio de `claves`: acierta si el top-1 cae en el
área que se fijó de antemano. Hoy sabemos que ese criterio no distingue una
recomendación distinta pero igual de sensata de una equivocada. Y mirando la
tabla de entonces, **3 de los 4 fallos tenían la carrera esperada en el puesto
2**: Ana recibió Trabajo Social con Psicología Clínica de #2, Lucía recibió
Trabajo Social con Periodismo de #2, Roberto recibió Sistemas con Contaduría de
#2. Bajo un juez de coherencia eso probablemente sean empates, no fallos.

## Qué se prueba, y qué no

El cambio original tenía dos pasos. **Solo se prueba el paso 1** (el estilo de
ítem), porque el paso 2 (devolverle el ranking al modelo para que desempate) ya
existe hoy en producción como el guard de `MARGEN_DESEMPATE`. Probar el paso 1
solo es además mejor diseño: el diagnóstico de entonces atribuyó 2 de los 4
fallos al estilo de ítem y 2 a alargar la conversación.

**El prompt es una RECONSTRUCCIÓN** desde la descripción del documento; el
original no quedó versionado. Así que esto no refuta el 6/10, mide una réplica.

## Brazos

- **A (producción):** el SYSTEM tal cual está hoy.
- **B:** el mismo, más el bloque de microexperiencias.
- **C (control):** A otra vez, con la misma entrada. Todo lo que difiera entre
  A y C es ruido, y es la vara para leer A contra B.

## Uso

    uv run python experimento_microexperiencias.py --self-check
    uv run python experimento_microexperiencias.py
"""

import argparse
import json
import os
import random

from dotenv import load_dotenv

load_dotenv()

from app import preguntas, recomendar  # noqa: E402
from cobertura_banco import banco as banco_actual  # noqa: E402
from experimento_banco import _gastado  # noqa: E402
from experimento_desempate import (  # noqa: E402
    DATA,
    PERSONAS as P_DESEMPATE,
    _fijas,
    _juzgar,
    _texto_pregunta,
)
from experimento_filtro import _top  # noqa: E402
from experimento_psicometrico import DEPARTAMENTO, _responder, catalogo  # noqa: E402

SALIDA = os.path.join(DATA, "experimento_microexperiencias_resultados.json")

TOPE_USD = 0.09

# Reconstrucción del paso 1 desde experiments/microexperiencias.md §1.
MICROEXPERIENCIAS = (
    "\n\nESTILO DE ÍTEM (obligatorio, reemplaza cualquier indicación anterior "
    "sobre cómo redactar la pregunta):\n"
    "- PROHIBIDO preguntar por materias escolares o por gustos abstractos "
    "('¿te gustan las matemáticas?', '¿te interesa la salud?').\n"
    "- Cada pregunta describe una MICROEXPERIENCIA: un rato concreto de una "
    "jornada real. Di qué haría la persona, con quién, dónde y por cuánto "
    "tiempo. Incluye la parte incómoda cuando la haya (turnos de noche, "
    "lluvia, papeleo, esperar, repetir lo mismo).\n"
    "- Aproximadamente 1 de cada 3 preguntas va en forma de RECHAZO ('¿qué "
    "tanto te molestaría...?'), porque lo que alguien no aguanta descarta más "
    "rápido que lo que le gusta.\n"
    "- Usa OPCIONES GRADUADAS en vez de Sí/No: 'Me encantaría' / 'Lo haría sin "
    "problema' / 'Lo aguantaría un rato' / 'No me veo ahí'.\n"
    "- Ejemplos del estilo buscado: 'Pasar la mañana tomándole signos vitales a "
    "diez pacientes seguidos, uno de ellos molesto'; 'Estar tres horas "
    "revisando un contrato línea por línea para encontrar una cláusula mal "
    "puesta'; 'Salir a las cinco de la mañana a medir un terreno con lluvia'.\n"
)

PERSONAS = [p for p in P_DESEMPATE
            if p["nombre"] in ("Rosa", "Wendy", "Elmer", "Mynor")]


def _conversar(persona, cat, respuestas, sid, extra_system):
    """Las adaptativas. `extra_system` se suma al SYSTEM solo en el brazo B."""
    original = preguntas.SYSTEM
    if extra_system:
        preguntas.SYSTEM = original + extra_system
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    try:
        for _ in range(preguntas.MAX_ADAPTATIVAS):
            paso, _u = preguntas.siguiente_pregunta(respuestas, cat, sid)
            if paso.terminado:
                break
            previo = "\n".join(f"P: {k}\nR: {v}"
                               for k, v in respuestas.items() if k != "nombre")
            respuestas[paso.pregunta_texto] = _responder(
                persona, _texto_pregunta(paso), previo)
    finally:
        preguntas.SYSTEM = original


def correr():
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    banco = banco_actual()
    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {c["persona"]: c for c in json.load(open(SALIDA, encoding="utf-8"))["casos"]}
    casos = list(hechos.values())
    rnd = random.Random(20260827)

    for p in PERSONAS:
        if p["nombre"] in hechos:
            continue
        if _gastado() >= TOPE_USD:
            print(f"!! tope ${TOPE_USD}; se detiene en {p['nombre']}")
            break
        print(f"\n=== {p['nombre']} ===")
        base = _fijas(p, banco)

        tops = {}
        preguntas_por_brazo = {}
        for brazo, extra in (("A", None), ("B", MICROEXPERIENCIAS), ("C", None)):
            r = dict(base)
            _conversar(p, cat, r, f"micro-{brazo}-{p['nombre']}", extra)
            preguntas_por_brazo[brazo] = [k for k in r if k not in base]
            rec, _u = recomendar.recomendar(r, cat)
            tops[brazo] = _top(rec, 3)

        pa = rnd.random() < 0.5
        l1, l2 = (tops["A"], tops["B"]) if pa else (tops["B"], tops["A"])
        j = _juzgar(p, l1, l2)
        gano = ("empate" if j.mejor == "empate"
                else ("A" if (j.mejor == "1") == pa else "B"))

        pc = rnd.random() < 0.5
        c1, c2 = (tops["A"], tops["C"]) if pc else (tops["C"], tops["A"])
        jc = _juzgar(p, c1, c2)

        caso = {"persona": p["nombre"], "contexto": p["contexto"], "fijas": base,
                "A_top3": tops["A"], "B_top3": tops["B"], "C_top3": tops["C"],
                "preguntas": preguntas_por_brazo, "primero_es_a": pa,
                "juicio": j.model_dump(), "gano": gano,
                "coherencia_A": j.coherencia_1 if pa else j.coherencia_2,
                "coherencia_B": j.coherencia_2 if pa else j.coherencia_1,
                "control_top1_igual": tops["A"][0]["carrera"] == tops["C"][0]["carrera"],
                "control_empate_juez": jc.mejor == "empate",
                "control_dif_coherencia": abs(jc.coherencia_1 - jc.coherencia_2)}
        casos.append(caso)
        json.dump({"casos": casos}, open(SALIDA, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"    A (producción):       {tops['A'][0]['carrera']}")
        print(f"    B (microexperiencias):{tops['B'][0]['carrera']}")
        print(f"    C (control, = que A): {tops['C'][0]['carrera']}"
              f"  {'igual' if caso['control_top1_igual'] else '<< DISTINTO: ruido'}")
        print(f"    juez: {gano}   ${_gastado():.4f}")

    _reporte(casos)
    return casos


def _reporte(casos):
    print("\n" + "=" * 72)
    print("MICROEXPERIENCIAS, RE-MEDIDAS CON JUEZ DE COHERENCIA Y CONTROL")
    print("=" * 72)
    if not casos:
        print("sin casos")
        return
    n = len(casos)
    dist = sum(1 for c in casos if not c["control_top1_igual"])
    noemp = sum(1 for c in casos if not c["control_empate_juez"])
    difc = sum(c["control_dif_coherencia"] for c in casos) / n
    print(f"\nPISO DE RUIDO - control: A contra A repetido, misma entrada (n={n})")
    print(f"  Top-1 distinto pese a la entrada idéntica: {dist}/{n}")
    print(f"  El juez prefirió una de las dos: {noemp}/{n}")
    print(f"  Diferencia media de coherencia entre corridas iguales: {difc:.2f}")

    ga = sum(1 for c in casos if c["gano"] == "A")
    gb = sum(1 for c in casos if c["gano"] == "B")
    dif = sum(c["coherencia_B"] - c["coherencia_A"] for c in casos) / n
    cambia = sum(1 for c in casos
                 if c["A_top3"][0]["carrera"] != c["B_top3"][0]["carrera"])
    print(f"\nTRATAMIENTO - A (producción) contra B (microexperiencias), n={n}")
    print(f"  juez: A {ga} · B {gb} · empate {n - ga - gb}")
    print(f"  coherencia B-A: {dif:+.2f}   (el ruido mide {difc:.2f})")
    print(f"  top-1 distinto: {cambia}/{n}   (el ruido mide {dist}/{n})")
    print("\n  >> Si tratamiento y ruido dan parecido, este experimento NO puede")
    print("     contestar la pregunta con esta n, y decirlo es el resultado.")

    print("\nDetalle:")
    for c in casos:
        print(f"  {c['persona']:9s} A={c['A_top3'][0]['carrera'][:28]:30s} "
              f"B={c['B_top3'][0]['carrera'][:28]:30s} "
              f"C={c['C_top3'][0]['carrera'][:28]:30s} {c['gano']}")
        for q in c["preguntas"]["B"][:2]:
            print(f"      [B] {q[:96]}")
    print(recomendar.resumen_gasto())
    print(f"\nGastado ${_gastado():.4f} de ${TOPE_USD}")


def _self_check():
    assert len(PERSONAS) == 4, [p["nombre"] for p in PERSONAS]
    assert "MICROEXPERIENCIA" in MICROEXPERIENCIAS
    assert "graduadas" in MICROEXPERIENCIAS.lower()
    # El SYSTEM se restaura aunque el brazo B falle a media conversación: si no,
    # el brazo C heredaría el prompt de B y el control mediría cualquier cosa.
    original = preguntas.SYSTEM
    try:
        preguntas.SYSTEM = original + MICROEXPERIENCIAS
        raise RuntimeError("falla simulada")
    except RuntimeError:
        preguntas.SYSTEM = original
    assert preguntas.SYSTEM == original, "el SYSTEM tiene que quedar como estaba"
    assert MICROEXPERIENCIAS not in preguntas.SYSTEM
    assert _gastado() == 0.0
    print("ok: 4 personas, prompt reconstruido, SYSTEM se restaura")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    _self_check() if a.self_check else correr()
