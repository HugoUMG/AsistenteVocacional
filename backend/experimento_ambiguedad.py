"""¿Las adaptativas sirven SOLO cuando las respuestas fijas dejan el perfil ambiguo?

Viene de `adaptativas-desempate.md`: con n=32 la ventaja del brazo con
adaptativas no fue significativa (17-9-6, p=0.17), pero **el efecto estaba
concentrado**. En Kevin, Ixchel y Mynor el brazo con adaptativas ganó las 4
réplicas; en Katherine perdió 3 de 4; en las otras cuatro personas no hubo
diferencia. La hipótesis que salió de ahí:

    las adaptativas pesan cuando las 4 preguntas fijas dejan el perfil ambiguo
    entre áreas, y no pesan cuando las fijas ya fijaron el área.

## Las dos mitades, y por qué no valen lo mismo

**A) Sobre los 32 casos que ya existen (barato).** Un clasificador CIEGO puntúa
la ambigüedad mirando SOLO las 4 respuestas fijas: no ve a la persona, no ve las
adaptativas, no ve las recomendaciones y no ve quién ganó. Después se cruza con
el resultado.

Esto es **exploratorio y no confirma nada**: la hipótesis salió de estos mismos
datos, así que encontrarla de nuevo acá era esperable. Sirve para describir y
para ver si el clasificador siquiera separa algo.

**B) Personas nuevas clasificadas ANTES de correr (lo que sí puede confirmar).**
Tres diseñadas ambiguas (intereses repartidos entre dos campos distintos) y tres
diseñadas claras (intereses concentrados). La etiqueta va en el código, fija,
antes de ver un solo resultado.

Con el presupuesto que queda son 6 personas × 2 réplicas = 12 casos. **Es poco y
no va a alcanzar significancia.** Se corre igual porque una predicción hecha de
antemano que falla informa más que un promedio que no llega, pero el resultado
hay que leerlo como señal, no como prueba.

## Uso

    uv run python experimento_ambiguedad.py --self-check
    uv run python experimento_ambiguedad.py --clasificar   # parte A, sobre lo ya corrido
    uv run python experimento_ambiguedad.py                # parte B, personas nuevas
"""

import argparse
import json
import os
import random

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import recomendar  # noqa: E402
from cobertura_banco import banco as banco_actual  # noqa: E402
from experimento_banco import _gastado  # noqa: E402
from experimento_desempate import (  # noqa: E402
    DATA,
    SALIDA as SALIDA_DESEMPATE,
    _brazo_a,
    _fijas,
    _juzgar,
)
from experimento_filtro import _top  # noqa: E402
from experimento_psicometrico import DEPARTAMENTO, catalogo  # noqa: E402

SALIDA = os.path.join(DATA, "experimento_ambiguedad_resultados.json")
CLASIF = os.path.join(DATA, "experimento_ambiguedad_clasificacion.json")

TOPE_USD = 0.15


# --- Parte B: personas con la etiqueta puesta ANTES de correr -------------
#
# 'ambigua' es la predicción, y se fija acá. Si al final las ambiguas no se
# comportan distinto de las claras, la hipótesis falla y eso se escribe.

PERSONAS = [
    # --- AMBIGUAS: la vida reparte sus intereses entre dos campos distintos ---
    {
        "nombre": "Brenda", "ambigua": True,
        "contexto": (
            "18 anios, termino el diversificado. Trabaja medio tiempo en la "
            "farmacia de la esquina y le gusta explicarle a la gente como tomarse "
            "las cosas; la buscan a ella. Pero tambien lleva la caja y se dio "
            "cuenta de que es buena viendo que producto conviene pedir y cual no "
            "se vende. Le gustan las dos partes y no sabe cual pesa mas."),
        "guion": ("Habla de tu vida como es, con las dos partes. No nombres "
                  "carreras ni digas que quieres estudiar algo especifico."),
    },
    {
        "nombre": "Osmar", "ambigua": True,
        "contexto": (
            "19 anios. Ayuda a su papa en la milpa desde chiquito y conoce el "
            "terreno, las lluvias y las plagas. Al mismo tiempo es el que arregla "
            "la bomba de agua y el motor cuando se descomponen, y le entretiene "
            "mas eso que sembrar. En la casa no se ponen de acuerdo sobre para que "
            "es mejor."),
        "guion": ("Habla de tu vida como es, con las dos partes. No nombres "
                  "carreras ni digas que quieres estudiar algo especifico."),
    },
    {
        "nombre": "Lucia", "ambigua": True,
        "contexto": (
            "17 anios, quinto bachillerato. Es la que escribe los discursos del "
            "colegio y le sale facil convencer a la gente cuando habla en publico. "
            "Tambien es la que consuela a sus amigas cuando estan mal y siempre "
            "termina escuchando problemas ajenos. No sabe si lo suyo es hablarle a "
            "mucha gente o a una sola."),
        "guion": ("Habla de tu vida como es, con las dos partes. No nombres "
                  "carreras ni digas que quieres estudiar algo especifico."),
    },
    # --- CLARAS: todo apunta al mismo campo ---
    {
        "nombre": "Fredy", "ambigua": False,
        "contexto": (
            "18 anios. Desde los 14 anda con su tio en las obras y ya sabe leer un "
            "plano y calcular cuanto material lleva una losa. Le gusta ver el "
            "edificio parado al final y saber que aguanta. Los fines de semana "
            "dibuja casas en un cuaderno. Todo lo que le gusta es de eso."),
        "guion": ("Habla de tu vida como es. No nombres carreras ni digas que "
                  "quieres estudiar algo especifico."),
    },
    {
        "nombre": "Sandra", "ambigua": False,
        "contexto": (
            "17 anios, quinto bachillerato. Le fascina el cuerpo humano desde que "
            "vio un documental, y se sabe los huesos de memoria. Pasa horas viendo "
            "casos raros y explicandoselos a sus companieras. Cuando alguien se "
            "lastima en el colegio ella es la primera en llegar y sabe que hacer. "
            "No le interesa nada que no sea eso."),
        "guion": ("Habla de tu vida como es. No nombres carreras ni digas que "
                  "quieres estudiar algo especifico."),
    },
    {
        "nombre": "Julio", "ambigua": False,
        "contexto": (
            "19 anios. Lleva tres anios llevando las cuentas del negocio de su "
            "familia, hizo el sistema de facturacion en una hoja de calculo y "
            "descubrio dos veces que un proveedor les estaba cobrando de mas. Le "
            "cuadra que los numeros cierren y le molesta el desorden. Es lo unico "
            "que le entretiene de verdad."),
        "guion": ("Habla de tu vida como es. No nombres carreras ni digas que "
                  "quieres estudiar algo especifico."),
    },
]


# --- Parte A: el clasificador ciego ---------------------------------------

class Ambiguedad(BaseModel):
    campos: list[str]     # campos profesionales a los que apuntan las respuestas
    ambigua: bool         # ¿apuntan a más de un campo con peso parecido?
    porque: str


SYSTEM_AMBIGUEDAD = (
    "Eres un orientador vocacional. Te dan SOLO las respuestas que un estudiante "
    "marcó en cuatro preguntas de opción múltiple de un test vocacional. No sabes "
    "nada más de él.\n\n"
    "Tu tarea es decir hacia qué campo o campos profesionales apuntan esas "
    "respuestas, y si apuntan a UNO solo con claridad o a VARIOS con peso "
    "parecido.\n\n"
    "- 'campos': los campos a los que apuntan, en una o dos palabras cada uno "
    "(p. ej. 'salud', 'educación', 'ingeniería', 'negocios', 'derecho', 'arte').\n"
    "- 'ambigua': true si hay dos o más campos distintos con peso parecido, de "
    "modo que estas respuestas por sí solas NO alcanzan para elegir. false si "
    "las respuestas apuntan claramente a un solo campo.\n"
    "- 'porque': una frase.\n"
    "- Español. No menciones carreras concretas ni que eres una IA."
)


def _clasificar_fijas(fijas):
    texto = "\n".join(f"- {k}: {v}" for k, v in fijas.items()
                      if k not in ("nombre", "departamento"))
    resp = recomendar.generar(
        model=recomendar.MODELO, system=SYSTEM_AMBIGUEDAD, catalogo="",
        variable=f"RESPUESTAS MARCADAS:\n{texto}",
        schema=Ambiguedad, temperature=0.0)
    return Ambiguedad.model_validate_json(recomendar._texto_seguro(resp))


def clasificar():
    """Parte A: etiqueta los 32 casos ya corridos, a ciegas del resultado."""
    casos = json.load(open(SALIDA_DESEMPATE, encoding="utf-8"))["casos"]
    hechas = {}
    if os.path.exists(CLASIF):
        hechas = json.load(open(CLASIF, encoding="utf-8"))
    for c in casos:
        k = f"{c['ronda']}|{c['persona']}"
        if k in hechas:
            continue
        a = _clasificar_fijas(c["fijas"])
        hechas[k] = a.model_dump()
        json.dump(hechas, open(CLASIF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {k:16s} ambigua={a.ambigua}  campos={a.campos}  ${_gastado():.4f}")
    _reporte_a(casos, hechas)


def _reporte_a(casos, clas):
    print("\n" + "=" * 74)
    print("PARTE A · EXPLORATORIA: ambigüedad de las fijas vs. resultado")
    print("=" * 74)
    print("(la hipótesis salió de estos mismos datos: describe, no confirma)\n")
    grupos = {True: [], False: []}
    for c in casos:
        a = clas.get(f"{c['ronda']}|{c['persona']}")
        if a:
            grupos[a["ambigua"]].append(c)
    for amb in (True, False):
        g = grupos[amb]
        if not g:
            continue
        ga = sum(1 for x in g if x["gano"] == "A")
        gb = sum(1 for x in g if x["gano"] == "B")
        dif = sum(x["coherencia_A"] - x["coherencia_B"] for x in g) / len(g)
        cambia = sum(1 for x in g
                     if x["A_top3"][0]["carrera"] != x["B_top3"][0]["carrera"])
        print(f"  fijas {'AMBIGUAS' if amb else 'CLARAS  '} (n={len(g):2d}): "
              f"juez A {ga} · B {gb} · empate {len(g) - ga - gb}   "
              f"coherencia A-B {dif:+.2f}   top-1 cambia {cambia}/{len(g)}")
    print("\n  Por persona:")
    porp = {}
    for c in casos:
        a = clas.get(f"{c['ronda']}|{c['persona']}")
        if a:
            porp.setdefault(c["persona"], []).append(a["ambigua"])
    for p, v in porp.items():
        print(f"    {p:11s} clasificada ambigua en {sum(v)}/{len(v)} réplicas")


# --- Parte B: la corrida con etiqueta previa ------------------------------

def correr(replicas=2):
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    banco = banco_actual()
    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {(c["ronda"], c["persona"]): c
                  for c in json.load(open(SALIDA, encoding="utf-8"))["casos"]}
        print(f"Reanudando: {len(hechos)} casos hechos")
    casos = list(hechos.values())
    rnd = random.Random(20260825)

    for ronda in [f"R{i}" for i in range(1, replicas + 1)]:
        for p in PERSONAS:
            if (ronda, p["nombre"]) in hechos:
                continue
            if _gastado() >= TOPE_USD:
                print(f"!! tope ${TOPE_USD}; se detiene en {ronda}/{p['nombre']}")
                _reporte_b(casos)
                return casos
            print(f"\n=== {ronda} · {p['nombre']} "
                  f"({'AMBIGUA' if p['ambigua'] else 'CLARA'}, predicho) ===")
            base = _fijas(p, banco)
            respuestas_a = dict(base)
            pasos = _brazo_a(p, cat, respuestas_a, f"amb-{ronda}-{p['nombre']}")
            res_a, _u = recomendar.recomendar(respuestas_a, cat)
            res_b, _u = recomendar.recomendar(dict(base), cat)
            ta, tb = _top(res_a, 3), _top(res_b, 3)
            primero_es_a = rnd.random() < 0.5
            l1, l2 = (ta, tb) if primero_es_a else (tb, ta)
            j = _juzgar(p, l1, l2)
            gano = ("empate" if j.mejor == "empate"
                    else ("A" if (j.mejor == "1") == primero_es_a else "B"))
            caso = {"ronda": ronda, "persona": p["nombre"], "ambigua": p["ambigua"],
                    "contexto": p["contexto"], "fijas": base,
                    "adaptativas_hechas": len([x for x in pasos if not x["terminado"]]),
                    "A_top3": ta, "B_top3": tb, "primero_es_a": primero_es_a,
                    "juicio": j.model_dump(), "gano": gano,
                    "coherencia_A": j.coherencia_1 if primero_es_a else j.coherencia_2,
                    "coherencia_B": j.coherencia_2 if primero_es_a else j.coherencia_1}
            casos.append(caso)
            json.dump({"casos": casos}, open(SALIDA, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"    A: {ta[0]['carrera']}")
            print(f"    B: {tb[0]['carrera']}")
            print(f"    juez: {gano}  (A={caso['coherencia_A']} B={caso['coherencia_B']})"
                  f"  ${_gastado():.4f}")
    _reporte_b(casos)
    return casos


def _reporte_b(casos):
    print("\n" + "=" * 74)
    print("PARTE B · CONFIRMATORIA: personas etiquetadas ANTES de correr")
    print("=" * 74)
    if not casos:
        print("sin casos")
        return
    for amb in (True, False):
        g = [c for c in casos if c["ambigua"] == amb]
        if not g:
            continue
        ga = sum(1 for x in g if x["gano"] == "A")
        gb = sum(1 for x in g if x["gano"] == "B")
        dif = sum(x["coherencia_A"] - x["coherencia_B"] for x in g) / len(g)
        cambia = sum(1 for x in g
                     if x["A_top3"][0]["carrera"] != x["B_top3"][0]["carrera"])
        print(f"\n  Predichas {'AMBIGUAS' if amb else 'CLARAS'} (n={len(g)}):")
        print(f"    juez: A {ga} · B {gb} · empate {len(g) - ga - gb}")
        print(f"    coherencia A-B: {dif:+.2f}")
        print(f"    top-1 cambia con las adaptativas: {cambia}/{len(g)}")
        for x in g:
            print(f"      {x['ronda']} {x['persona']:9s} A={x['A_top3'][0]['carrera'][:30]:32s} "
                  f"B={x['B_top3'][0]['carrera'][:30]:32s} {x['gano']}")
    print(recomendar.resumen_gasto())
    print(f"\nGastado ${_gastado():.4f} de ${TOPE_USD}")


def _self_check():
    banco = banco_actual()
    amb = [p for p in PERSONAS if p["ambigua"]]
    cla = [p for p in PERSONAS if not p["ambigua"]]
    assert len(amb) == 3 and len(cla) == 3, "el diseño pide 3 y 3"
    # La etiqueta va puesta ANTES de correr: si falta en alguna, el experimento
    # dejaría de ser confirmatorio y no vale la pena gastarlo.
    for p in PERSONAS:
        assert isinstance(p.get("ambigua"), bool), f"{p['nombre']} sin etiqueta previa"
    pistas = ["ingenier", "licenciatur", "profesorado", "medicina", "enfermer",
              "carrera de", "quiero estudiar", "arquitect", "contad"]
    for p in PERSONAS:
        bajo = p["contexto"].lower()
        for x in pistas:
            assert x not in bajo, f"{p['nombre']} dirige el resultado con '{x}'"
        for etq in banco["gustos"]:
            assert etq.lower() not in bajo, f"{p['nombre']} repite la etiqueta '{etq}'"
    assert _gastado() == 0.0
    print(f"ok: {len(amb)} ambiguas y {len(cla)} claras, etiquetadas de antemano")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--clasificar", action="store_true")
    ap.add_argument("--replicas", type=int, default=2)
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.clasificar:
        clasificar()
    else:
        correr(a.replicas)
