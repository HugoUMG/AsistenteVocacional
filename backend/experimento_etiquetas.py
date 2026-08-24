"""A/B de las 3 etiquetas acortadas: ¿mueven la recomendación?

Cambiaron 3 de las 25 etiquetas del banco (commit 62f2f39):

    Salud, cuidados y atención a pacientes  ->  Salud y cuidar pacientes
    Enseñanza, docencia y educación         ->  Enseñanza y docencia
    Psicología y comportamiento             ->  Psicología y conducta

Ya se verificó gratis que la cobertura del catálogo no se rompe
(`cobertura_banco.py`) y que un revisor las juzga equivalentes
(`verifica_etiquetas.py`). Falta lo que esas dos no pueden ver: si el texto más
corto mueve la recomendación.

## Por qué NO se usa el diseño de experimento_banco.py

Ahí cada brazo conversa por su cuenta y el alumno simulado marca lo que quiere.
Con 22 de 25 etiquetas idénticas, casi toda la diferencia entre brazos vendría
de que el alumno marcó chips distintos por azar (temperatura 0.9), no del
cambio que se quiere medir. Se gastaría el presupuesto midiendo ruido.

## El diseño que sí aísla el cambio

Las 4 preguntas fijas se contestan **una sola vez** y de ahí salen los dos
brazos, que difieren **solo en esas 3 cadenas de texto**:

- **A (antes):** las marcas con las etiquetas largas.
- **B (ahora):** las mismas marcas con las etiquetas cortas.

Todo lo demás (adaptativas y recomendación) corre igual en los dos. Así la
única variable es el texto de la etiqueta, que es exactamente la pregunta.

**Lo que este diseño NO mide:** si un alumno se reconoce distinto en la
etiqueta corta y por eso marca otra cosa. Eso es un efecto de interfaz, no de
señal, y necesitaría que el alumno eligiera de verdad. Queda fuera y se dice.

## Personas

Siete que tocan salud, educación o psicología (las áreas de las 3 etiquetas) y
Kevin como control: su perfil no roza ninguna, así que sus dos brazos deberían
salir iguales salvo por el ruido normal.

## Uso

    uv run python experimento_etiquetas.py --self-check
    uv run python experimento_etiquetas.py
"""

import argparse
import json
import os
import random

from dotenv import load_dotenv

load_dotenv()

from app import preguntas, recomendar  # noqa: E402
from cobertura_banco import banco as banco_actual  # noqa: E402
from experimento_ambiguedad import PERSONAS as P_AMBIG  # noqa: E402
from experimento_banco import PERSONAS as P_BANCO, _gastado  # noqa: E402
from experimento_desempate import (  # noqa: E402
    DATA,
    PERSONAS as P_DESEMPATE,
    _brazo_a,
    _fijas,
    _juzgar,
)
from experimento_filtro import _top  # noqa: E402
from experimento_psicometrico import DEPARTAMENTO, catalogo  # noqa: E402

SALIDA = os.path.join(DATA, "experimento_etiquetas_resultados.json")
LECTURA = os.path.join(DATA, "experimento_etiquetas_para_leer.md")

TOPE_USD = 0.13  # de los $0.15 autorizados, con margen

# corta (producción hoy) -> larga (como estaba antes)
REVERTIR = {
    "Salud y cuidar pacientes": "Salud, cuidados y atención a pacientes",
    "Enseñanza y docencia": "Enseñanza, docencia y educación",
    "Psicología y conducta": "Psicología y comportamiento",
}

_POR_NOMBRE = {p["nombre"]: p for p in P_DESEMPATE + P_BANCO + P_AMBIG}
# Siete que tocan salud / educación / psicología, más Kevin de control.
PERSONAS = [_POR_NOMBRE[n] for n in
            ("Rosa", "Diego", "Sandra", "Brenda", "Wendy", "Ixchel", "Lucia", "Kevin")]
CONTROL = "Kevin"


def _a_largas(respuestas):
    """Las mismas respuestas, con las 3 etiquetas cortas devueltas a su forma
    larga. Es lo ÚNICO que separa al brazo A del brazo B."""
    out = {}
    for k, v in respuestas.items():
        if isinstance(v, str):
            for corta, larga in REVERTIR.items():
                v = v.replace(corta, larga)
        out[k] = v
    return out


def correr():
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    banco = banco_actual()
    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {c["persona"]: c for c in json.load(open(SALIDA, encoding="utf-8"))["casos"]}
        print(f"Reanudando: {len(hechos)} casos hechos")
    casos = list(hechos.values())
    rnd = random.Random(20260826)

    for p in PERSONAS:
        if p["nombre"] in hechos:
            continue
        if _gastado() >= TOPE_USD:
            print(f"!! tope ${TOPE_USD}; se detiene en {p['nombre']}")
            break
        print(f"\n=== {p['nombre']}{' (control)' if p['nombre'] == CONTROL else ''} ===")

        # Las fijas, UNA vez, con el banco de hoy (etiquetas cortas).
        base_corta = _fijas(p, banco)
        base_larga = _a_largas(base_corta)
        toco = base_corta != base_larga
        print(f"    marcó: {base_corta.get('gustos', '')[:88]}")
        print(f"    ¿marcó alguna de las 3 etiquetas cambiadas? "
              f"{'SÍ' if toco else 'no (sus dos brazos son idénticos)'}")

        res = {}
        for brazo, base in (("A", base_larga), ("B", base_corta)):
            r = dict(base)
            _brazo_a(p, cat, r, f"etq-{brazo}-{p['nombre']}")
            rec, _u = recomendar.recomendar(r, cat)
            res[brazo] = _top(rec, 3)

        primero_es_a = rnd.random() < 0.5
        l1, l2 = (res["A"], res["B"]) if primero_es_a else (res["B"], res["A"])
        j = _juzgar(p, l1, l2)
        gano = ("empate" if j.mejor == "empate"
                else ("A" if (j.mejor == "1") == primero_es_a else "B"))

        caso = {"persona": p["nombre"], "control": p["nombre"] == CONTROL,
                "contexto": p["contexto"], "fijas_cortas": base_corta,
                "toco_etiqueta_cambiada": toco,
                "A_top3": res["A"], "B_top3": res["B"], "primero_es_a": primero_es_a,
                "juicio": j.model_dump(), "gano": gano,
                "coherencia_A": j.coherencia_1 if primero_es_a else j.coherencia_2,
                "coherencia_B": j.coherencia_2 if primero_es_a else j.coherencia_1}
        casos.append(caso)
        json.dump({"casos": casos}, open(SALIDA, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"    A (etiquetas largas): {res['A'][0]['carrera']}")
        print(f"    B (etiquetas cortas): {res['B'][0]['carrera']}")
        print(f"    juez: {gano}   ${_gastado():.4f}")

    _reporte(casos)
    return casos


def _reporte(casos):
    print("\n" + "=" * 74)
    print("A/B DE LAS 3 ETIQUETAS ACORTADAS")
    print("=" * 74)
    if not casos:
        print("sin casos")
        return
    afectados = [c for c in casos if c["toco_etiqueta_cambiada"]]
    print(f"\nCasos: {len(casos)}   ·   que marcaron alguna etiqueta cambiada: "
          f"{len(afectados)}")
    print("(en los que no la marcaron, los dos brazos reciben lo MISMO: sirven de\n"
          " termómetro del ruido, porque toda diferencia ahí es azar)")

    for grupo, etiqueta in ((afectados, "MARCARON UNA ETIQUETA CAMBIADA"),
                            ([c for c in casos if not c["toco_etiqueta_cambiada"]],
                             "NO LA MARCARON (ruido puro)")):
        if not grupo:
            continue
        ga = sum(1 for c in grupo if c["gano"] == "A")
        gb = sum(1 for c in grupo if c["gano"] == "B")
        igual = sum(1 for c in grupo
                    if c["A_top3"][0]["carrera"] == c["B_top3"][0]["carrera"])
        dif = sum(c["coherencia_A"] - c["coherencia_B"] for c in grupo) / len(grupo)
        print(f"\n  {etiqueta} (n={len(grupo)})")
        print(f"    juez: A {ga} · B {gb} · empate {len(grupo) - ga - gb}")
        print(f"    coherencia A-B: {dif:+.2f}")
        print(f"    top-1 IGUAL en los dos brazos: {igual}/{len(grupo)}")

    print("\n  Detalle:")
    for c in casos:
        marca = "=" if c["A_top3"][0]["carrera"] == c["B_top3"][0]["carrera"] else "≠"
        print(f"    {c['persona']:9s} {'[ctrl]' if c['control'] else '      '} "
              f"{'toca' if c['toco_etiqueta_cambiada'] else '  no'} {marca} "
              f"A={c['A_top3'][0]['carrera'][:30]:32s} B={c['B_top3'][0]['carrera'][:30]:32s} {c['gano']}")

    _escribir(casos)
    print(recomendar.resumen_gasto())
    print(f"\nGastado ${_gastado():.4f} de ${TOPE_USD}   ·   para leer: {LECTURA}")


def _escribir(casos):
    L = ["# A/B de las 3 etiquetas acortadas", "",
         "Brazo A: etiquetas largas. Brazo B: cortas. Las MISMAS marcas en los dos,",
         "así lo único que cambia son 3 cadenas de texto.", ""]
    for c in casos:
        L += [f"## {c['persona']}" + (" (control)" if c["control"] else ""), "",
              c["contexto"], "",
              f"**Marcó:** {c['fijas_cortas'].get('gustos', '')}", "",
              f"**Tocó una etiqueta cambiada:** {'sí' if c['toco_etiqueta_cambiada'] else 'no'}", "",
              "| # | A (largas) | B (cortas) |", "|---|---|---|"]
        for i in range(3):
            a = c["A_top3"][i] if i < len(c["A_top3"]) else {"carrera": "", "afinidad": ""}
            b = c["B_top3"][i] if i < len(c["B_top3"]) else {"carrera": "", "afinidad": ""}
            L.append(f"| {i + 1} | {a['carrera']} ({a['afinidad']}%) | {b['carrera']} ({b['afinidad']}%) |")
        j = c["juicio"]
        pa, pb = ((j["porque_1"], j["porque_2"]) if c["primero_es_a"]
                  else (j["porque_2"], j["porque_1"]))
        L += ["", f"**Juez ciego:** gana {c['gano']} · A={c['coherencia_A']} B={c['coherencia_B']}", "",
              f"- Sobre A: {pa}", f"- Sobre B: {pb}", ""]
    open(LECTURA, "w", encoding="utf-8").write("\n".join(L))


def _self_check():
    banco = banco_actual()
    # Las 3 cortas tienen que estar EN el banco de hoy, y las largas NO.
    for corta, larga in REVERTIR.items():
        assert corta in banco["gustos"], f"'{corta}' no está en el banco actual"
        assert larga not in banco["gustos"], f"'{larga}' sigue en el banco"
    assert len(PERSONAS) == 8 and any(p["nombre"] == CONTROL for p in PERSONAS)

    # _a_largas revierte solo lo que debe y no toca el resto.
    r = {"gustos": "Salud y cuidar pacientes, Química y laboratorio",
         "estilo": "Psicología y conducta", "nombre": "Ana", "edad": "17"}
    v = _a_largas(r)
    assert v["gustos"] == "Salud, cuidados y atención a pacientes, Química y laboratorio"
    assert v["estilo"] == "Psicología y comportamiento"
    assert v["nombre"] == "Ana" and v["edad"] == "17"
    # sin etiquetas cambiadas, los dos brazos quedan idénticos
    sin = {"gustos": "Química y laboratorio"}
    assert _a_largas(sin) == sin
    assert _gastado() == 0.0
    print("ok: 3 etiquetas a revertir, 8 personas, 1 de control")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    _self_check() if a.self_check else correr()
