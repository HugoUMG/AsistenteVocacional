"""¿Para qué sirven las 4 preguntas adaptativas?

`experiments/adaptativas-desempate.md` lleva desde el 2026-08-21 sin ejecutar. La
pregunta: todo lo medido dice que el sistema acierta el ÁREA; lo que nadie ha
medido es si las adaptativas sirven para elegir DENTRO del área, entre carreras
de pensum parecido.

Se ejecuta ahora con el diseño de `experimento_banco.py` (personas sin carrera
fijada + juez ciego por coherencia), porque el diseño original del documento
puntuaba con `claves` y eso no puede contestar esta pregunta: si el brazo sin
adaptativas propone una hermana igual de sensata, `claves` la cuenta como
acierto o como fallo según la subcadena, no según si tiene lógica.

## Brazos

- **A (producción):** 4 fijas + las adaptativas + recomendación.
- **B:** 4 fijas + recomendación. **Cero adaptativas.**

Mismo perfil, misma persona simulada. Si las adaptativas no aportan, las dos
listas deberían ser igual de coherentes y el chat se podría acortar.

## Las tres medidas

1. **Coherencia**, con juez ciego, igual que en el banco.
2. **¿Cambió el top-1, y cambió DENTRO del área o de área?** Lo clasifica el
   mismo juez, que ve las dos listas sin saber cuál es cuál. Cambiar de área ya
   se sabe que lo mueven; lo que se quiere saber es lo otro.
3. **El guard del desempate, en vivo.** Sobre los cierres del brazo A: ¿salen
   con la #1 separada de la #2 por al menos `MARGEN_DESEMPATE`? Antes del guard,
   12 de 32 cierres (37%) quedaban empatados. Y cuando el guard fuerza una
   pregunta más, ¿esa pregunta separa a las dos, o las sube por igual? Esto se
   lee de los rankings intermedios, sin gastar una llamada extra.

## Uso

    uv run python experimento_desempate.py --self-check
    uv run python experimento_desempate.py --rondas 2
"""

import argparse
import json
import os
import random

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import preguntas, recomendar  # noqa: E402
from cobertura_banco import banco as banco_actual  # noqa: E402
from experimento_banco import (  # noqa: E402
    ORDEN,
    PERSONAS as PERSONAS_BANCO,
    _gastado,
    _marcar,
)
from experimento_filtro import _top  # noqa: E402
from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    _responder,
    _texto_pregunta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data", "tests")
SALIDA = os.path.join(DATA, "experimento_desempate_resultados.json")
LECTURA = os.path.join(DATA, "experimento_desempate_para_leer.md")

TOPE_USD = 0.45  # de los $0.50 autorizados, con margen

# Las 6 personas del A/B del banco (ya validadas: no nombran carreras) más dos
# que caen en áreas con hermanas de verdad, que es donde la pregunta tiene
# sentido: gastronomía tiene 3 carreras casi iguales y sistemas tiene 5.
PERSONAS = PERSONAS_BANCO + [
    {
        "nombre": "Mynor",
        "contexto": (
            "18 anios, termino el diversificado. Desde chiquito cocina en la casa y "
            "ahora vende comida los fines de semana afuera del estadio con su "
            "hermano; el inventa los platos y su hermano cobra. Le gusta que la "
            "gente le diga que esta rico y anda pensando en como hacer que rinda "
            "mas. Suenia con tener su propio local algun dia."),
        "guion": ("Habla de tu vida como es. No nombres carreras ni digas que "
                  "quieres estudiar algo especifico."),
    },
    {
        "nombre": "Katherine",
        "contexto": (
            "17 anios, quinto bachillerato. Le hizo una pagina web al negocio de su "
            "tio y le cobro. Se pasa las tardes viendo tutoriales y probando cosas "
            "hasta que le salen. Le gusta cuando algo que estaba roto por fin "
            "funciona. Tambien es la que lleva las cuentas del negocio familiar en "
            "una hoja de calculo que ella misma armo."),
        "guion": ("Habla de tu vida como es. No nombres carreras ni digas que "
                  "quieres estudiar algo especifico."),
    },
]


class JuicioDesempate(BaseModel):
    coherencia_1: int
    porque_1: str
    coherencia_2: int
    porque_2: str
    mejor: str            # "1" | "2" | "empate"
    porque_mejor: str
    misma_area: bool      # ¿los dos top-1 son del mismo campo?
    area: str             # nombre corto del área del top-1 de la lista 1


SYSTEM_JUEZ = (
    "Eres un orientador vocacional con experiencia evaluando el trabajo de otros "
    "orientadores. Te dan la descripción de un estudiante y DOS listas de carreras "
    "recomendadas para él, hechas por dos orientadores distintos.\n\n"
    "Tu tarea NO es adivinar qué carrera 'debería' salir. Es juzgar, para cada "
    "lista, qué tan COHERENTE es con la persona descrita: ¿se explica a partir de "
    "lo que disfruta, de cómo es y de lo que se le da bien?\n\n"
    "Reglas:\n"
    "- Dos listas distintas pueden ser AMBAS coherentes. Si es así, pon 'empate'.\n"
    "- No premies que una lista sea más específica o más larga por sí sola.\n"
    "- 'coherencia_1'/'coherencia_2': entero de 1 a 5.\n"
    "- 'porque_1'/'porque_2': 2 o 3 frases citando lo concreto del perfil.\n"
    "- 'mejor': exactamente '1', '2' o 'empate'.\n"
    "- 'misma_area': true si la PRIMERA carrera de las dos listas pertenece al "
    "mismo campo profesional (p. ej. las dos son de salud, o las dos de "
    "ingeniería, o las dos de educación), aunque sean carreras distintas. false "
    "si son campos distintos.\n"
    "- 'area': nombre corto del campo de la primera carrera de la lista 1 "
    "(p. ej. 'salud', 'educación', 'ingeniería', 'derecho', 'negocios').\n"
    "- Español. No menciones que eres una IA."
)


def _juzgar(persona, l1, l2):
    def fmt(l):
        return "\n".join(f"  {i}. {c['carrera']} ({c['afinidad']}%)"
                         for i, c in enumerate(l, 1))
    resp = recomendar.generar(
        model=recomendar.MODELO, system=SYSTEM_JUEZ, catalogo="",
        variable=(f"ESTUDIANTE:\n{persona['contexto']}\n\n"
                  f"LISTA 1:\n{fmt(l1)}\n\nLISTA 2:\n{fmt(l2)}"),
        schema=JuicioDesempate, temperature=0.2)
    return JuicioDesempate.model_validate_json(recomendar._texto_seguro(resp))


def _fijas(persona, banco):
    """Las 4 preguntas fijas. Idénticas en los dos brazos."""
    respuestas = {"nombre": persona["nombre"], "departamento": DEPARTAMENTO}
    for clave in ORDEN:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        elegidas, _otro = _marcar(persona, clave, banco[clave], previo)
        respuestas[clave] = elegidas
    return respuestas


def _brecha(ranking):
    """Puntos entre la #1 y la #2 del ranking provisional."""
    if len(ranking) < 2:
        return None
    return ranking[0].afinidad - ranking[1].afinidad


def _brazo_a(persona, cat, respuestas, sid):
    """Producción: adaptativas hasta que el modelo cierre (con el guard activo)."""
    pasos = []
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    for _ in range(preguntas.MAX_ADAPTATIVAS):
        paso, _uso = preguntas.siguiente_pregunta(respuestas, cat, sid)
        r = [x.model_dump() for x in paso.ranking]
        pasos.append({"terminado": paso.terminado, "ranking": r,
                      "brecha": _brecha(paso.ranking),
                      "dimension": paso.dimension_objetivo,
                      "pregunta": paso.pregunta_texto})
        if paso.terminado:
            break
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        resp = _responder(persona, _texto_pregunta(paso), previo)
        respuestas[paso.pregunta_texto] = resp
        pasos[-1]["respuesta"] = resp
    return pasos


def _etiquetas(rondas):
    """Nombres de ronda. Único lugar donde se decide cómo se llama una ronda."""
    return [f"R{i}" for i in range(1, rondas + 1)]


def correr(rondas=2):
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    banco = banco_actual()

    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {(c["ronda"], c["persona"]): c
                  for c in json.load(open(SALIDA, encoding="utf-8"))["casos"]}
        print(f"Reanudando: {len(hechos)} casos hechos")
    casos = list(hechos.values())
    rnd = random.Random(20260824)

    for ronda in _etiquetas(rondas):
        for p in PERSONAS:
            # La clave DEBE construirse igual que al guardar. Antes acá iba el
            # entero de la ronda y en el archivo el string "R1", así que nunca
            # coincidía: al reanudar volvía a correr todo y duplicaba casos
            # (y gastaba de nuevo). Por eso la etiqueta se calcula en un solo
            # lugar, _etiquetas(), y se usa la misma para comparar y para
            # guardar.
            if (ronda, p["nombre"]) in hechos:
                continue
            if _gastado() >= TOPE_USD:
                print(f"!! tope ${TOPE_USD} alcanzado; se detiene en {ronda}/{p['nombre']}")
                _reporte(casos)
                return casos
            print(f"\n=== R{ronda} · {p['nombre']} ===")
            # Las fijas se contestan UNA vez y se comparten: así la única
            # diferencia entre brazos son las adaptativas, no el arranque.
            base = _fijas(p, banco)
            print("    fijas:", base.get("gustos", "")[:88])

            respuestas_a = dict(base)
            pasos = _brazo_a(p, cat, respuestas_a, f"des-{ronda}-{p['nombre']}")
            res_a, _u = recomendar.recomendar(respuestas_a, cat)
            res_b, _u = recomendar.recomendar(dict(base), cat)
            ta, tb = _top(res_a, 3), _top(res_b, 3)

            primero_es_a = rnd.random() < 0.5
            l1, l2 = (ta, tb) if primero_es_a else (tb, ta)
            j = _juzgar(p, l1, l2)
            gano = ("empate" if j.mejor == "empate"
                    else ("A" if (j.mejor == "1") == primero_es_a else "B"))

            hechas = len([x for x in pasos if not x["terminado"]])
            cierre = pasos[-1] if pasos else {}
            caso = {
                "ronda": ronda, "persona": p["nombre"], "contexto": p["contexto"],
                "fijas": base, "pasos": pasos, "adaptativas_hechas": hechas,
                "brecha_cierre": cierre.get("brecha"),
                "A_top3": ta, "B_top3": tb, "primero_es_a": primero_es_a,
                "juicio": j.model_dump(), "gano": gano,
                "coherencia_A": j.coherencia_1 if primero_es_a else j.coherencia_2,
                "coherencia_B": j.coherencia_2 if primero_es_a else j.coherencia_1,
            }
            casos.append(caso)
            json.dump({"casos": casos}, open(SALIDA, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"    A ({hechas} adaptativas): {ta[0]['carrera']}")
            print(f"    B (cero adaptativas):    {tb[0]['carrera']}")
            print(f"    juez: {gano}  misma_area={j.misma_area}  "
                  f"brecha_cierre={caso['brecha_cierre']}  ${_gastado():.4f}")
    _reporte(casos)
    return casos


def _reporte(casos):
    print("\n" + "=" * 78)
    print("¿PARA QUÉ SIRVEN LAS ADAPTATIVAS?")
    print("=" * 78)
    if not casos:
        print("sin casos")
        return
    n = len(casos)
    print(f"\n1) COHERENCIA (juez ciego, n={n})")
    ga = sum(1 for c in casos if c["gano"] == "A")
    gb = sum(1 for c in casos if c["gano"] == "B")
    ge = n - ga - gb
    print(f"   A (con adaptativas) {ga}   B (sin adaptativas) {gb}   empate {ge}")
    print(f"   Coherencia media: A {sum(c['coherencia_A'] for c in casos) / n:.2f}   "
          f"B {sum(c['coherencia_B'] for c in casos) / n:.2f}")

    print(f"\n2) ¿QUÉ MUEVEN LAS ADAPTATIVAS? (n={n})")
    distinto = [c for c in casos if c["A_top3"][0]["carrera"] != c["B_top3"][0]["carrera"]]
    dentro = [c for c in distinto if c["juicio"]["misma_area"]]
    fuera = [c for c in distinto if not c["juicio"]["misma_area"]]
    print(f"   Top-1 igual con y sin adaptativas: {n - len(distinto)}/{n}")
    print(f"   Top-1 distinto: {len(distinto)}/{n}")
    print(f"      de esos, DENTRO de la misma área: {len(dentro)}  <- la pregunta del experimento")
    print(f"      de esos, cambiando de área:       {len(fuera)}")

    print(f"\n3) EL GUARD DEL DESEMPATE EN VIVO (n={n})")
    cerrados = [c for c in casos if c["brecha_cierre"] is not None]
    empatados = [c for c in cerrados if c["brecha_cierre"] < preguntas.MARGEN_DESEMPATE]
    print(f"   Cierres con la #1 y la #2 separadas por >= {preguntas.MARGEN_DESEMPATE}: "
          f"{len(cerrados) - len(empatados)}/{len(cerrados)}")
    print(f"   Cierres todavía empatados: {len(empatados)}/{len(cerrados)}  "
          f"(antes del guard: 12/32 = 37%)")
    largos = [c for c in casos if c["adaptativas_hechas"] > preguntas.MIN_ADAPTATIVAS]
    print(f"   Sesiones que necesitaron pregunta extra: {len(largos)}/{n}")
    for c in largos:
        b = [x["brecha"] for x in c["pasos"] if x["brecha"] is not None]
        print(f"      {c['ronda']} {c['persona']:10s} {c['adaptativas_hechas']} adaptativas, "
              f"brechas {b}")

    print(f"\n4) DETALLE")
    for c in casos:
        marca = "" if c["A_top3"][0]["carrera"] == c["B_top3"][0]["carrera"] else \
                ("  <- cambia DENTRO del área" if c["juicio"]["misma_area"] else "  <- cambia de área")
        print(f"   {c['ronda']} {c['persona']:10s} A={c['A_top3'][0]['carrera'][:34]:36s} "
              f"B={c['B_top3'][0]['carrera'][:34]:36s} {c['gano']}{marca}")
    _escribir(casos)
    print(recomendar.resumen_gasto())
    print(f"\nGastado ${_gastado():.4f} de ${TOPE_USD}   ·   para leer: {LECTURA}")


def _escribir(casos):
    L = ["# ¿Para qué sirven las adaptativas? Material para leer", "",
         "Brazo A: producción (4 fijas + adaptativas). Brazo B: 4 fijas y directo",
         "a la recomendación. Mismas respuestas fijas en los dos.", ""]
    for c in casos:
        L += [f"## {c['ronda']} · {c['persona']}", "", c["contexto"], "",
              f"**Marcó:** {c['fijas'].get('gustos', '')}", "",
              f"**Adaptativas ({c['adaptativas_hechas']}):**", ""]
        for pa in c["pasos"]:
            if pa.get("pregunta"):
                L.append(f"- [{pa['dimension']}] {pa['pregunta']}")
                L.append(f"  - {pa.get('respuesta', '')}")
                L.append(f"  - ranking: " + ", ".join(
                    f"{r['carrera']} {r['afinidad']}" for r in pa["ranking"][:3]))
        L += ["", "| # | A (con adaptativas) | B (sin adaptativas) |", "|---|---|---|"]
        for i in range(3):
            a = c["A_top3"][i] if i < len(c["A_top3"]) else {"carrera": "", "afinidad": ""}
            b = c["B_top3"][i] if i < len(c["B_top3"]) else {"carrera": "", "afinidad": ""}
            L.append(f"| {i + 1} | {a['carrera']} ({a['afinidad']}%) | {b['carrera']} ({b['afinidad']}%) |")
        j = c["juicio"]
        pa_, pb_ = ((j["porque_1"], j["porque_2"]) if c["primero_es_a"]
                    else (j["porque_2"], j["porque_1"]))
        L += ["", f"**Juez ciego:** gana {c['gano']} · A={c['coherencia_A']} B={c['coherencia_B']} · "
                  f"misma área: {j['misma_area']} ({j['area']})", "",
              f"- Sobre A: {pa_}", f"- Sobre B: {pb_}", f"- Comparación: {j['porque_mejor']}", ""]
    open(LECTURA, "w", encoding="utf-8").write("\n".join(L))


def _self_check():
    banco = banco_actual()
    assert len(PERSONAS) == 8, f"se esperaban 8 personas, hay {len(PERSONAS)}"
    pistas = ["ingenier", "licenciatur", "profesorado", "medicina", "carrera de",
              "quiero estudiar", "gastronom", "chef", "sistemas"]
    for p in PERSONAS:
        bajo = p["contexto"].lower()
        for x in pistas:
            assert x not in bajo, f"{p['nombre']} dirige el resultado con '{x}'"
        for etq in banco["gustos"]:
            assert etq.lower() not in bajo, f"{p['nombre']} repite la etiqueta '{etq}'"

    class _R:
        def __init__(s, a): s.afinidad = a
    assert _brecha([_R(90), _R(40)]) == 50
    assert _brecha([_R(70), _R(70)]) == 0
    assert _brecha([_R(50)]) is None
    assert _brecha([]) is None
    # La reanudación: la clave con la que se compara tiene que ser la MISMA con
    # la que se guarda. Este es el bug que duplicó casos y gastó dos veces.
    assert _etiquetas(2) == ["R1", "R2"]
    guardado = {("R1", "Wendy"): {}}
    assert all((r, "Wendy") in guardado for r in _etiquetas(1)),         "la etiqueta de ronda debe coincidir con la guardada"
    assert ("R2", "Wendy") not in guardado  # la ronda que falta sí se corre

    # El desciframiento del ciego.
    for pa, mejor, esp in [(True, "1", "A"), (True, "2", "B"), (False, "1", "B"), (False, "2", "A")]:
        assert ("A" if (mejor == "1") == pa else "B") == esp
    print(f"ok: {len(PERSONAS)} personas, ninguna dirige el resultado")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--rondas", type=int, default=2)
    a = ap.parse_args()
    _self_check() if a.self_check else correr(a.rondas)
