"""Experimento A/B: después del test de Holland, ¿el chat todavía necesita sus
4 preguntas fijas?

El modo que se quiere construir es "Holland y luego el chat": el alumno responde
los 60 ítems del O*NET Interest Profiler y el chat arranca con sus intereses YA
MEDIDOS por un instrumento oficial, para gastar sus turnos en averiguar qué
carrera CONCRETA del sector encaja, no en descubrir el sector.

La pregunta que decide el diseño es una sola: con Holland de entrada, ¿las 4
preguntas fijas siguen aportando o estorban?

## Brazos

Los dos van DESPUÉS de Holland y los dos reciben exactamente el mismo trato de
Holland (bloque corto en el prompt + recorte del catálogo al sector). Lo único
que cambia entre brazos son las preguntas fijas:

- **A — solo adaptativas.** Sin preguntas fijas. La cobertura arranca con
  `intereses` cubierta por el test; el chat tiene que cubrir todo lo demás
  (incluidos entorno y motivaciones, que en producción cubren las fijas).
- **B — fijas + adaptativas.** El flujo de producción tal cual, más Holland.

## Por qué estos dos perfiles

Son los dos casos del experimento anterior (`experimento_psicometrico.py`) donde
quitar las preguntas fijas hizo daño medible. Si Holland repara ese daño, se ve
aquí; si no lo repara ni siquiera con los intereses bien medidos, la pregunta
queda contestada:

- **Dulce** — con las fijas, los chips le dieron un canal barato para admitir el
  arte que en su casa no se nombra; sin ellas se quedó en el guion familiar y
  terminó en Enfermería. Holland mide justo lo que los chips destaparon.
- **Melany** — con las fijas declaró su plan ("leyes") y eso produjo la mejor
  alerta de contradicción de todo el proyecto; sin ellas el tema nunca apareció.
  Holland NO pregunta por planes, así que este perfil prueba si el chat sale a
  buscar ese dato por su cuenta.

## La hoja de Holland NO la responde Gemini

Es la lección de [experiments/cip-en-recomendacion.md]: allá el propio modelo
contestó 150 ítems haciéndose pasar por alguien, el perfil resultante no
representaba a la persona en 4 de 10 casos, y el A/B terminó midiendo "¿ayuda un
instrumento mal respondido?".

Acá la hoja se construye aritméticamente: a cada perfil se le fija su nivel real
de interés 1-5 por área RIASEC, y cada ítem se contesta con el nivel de SU área
(el dato `area` viene en el banco oficial) más ±1 de ruido. La califica la API de
O*NET, no este script. `--hojas` verifica que el código que devuelve O*NET
contenga el área dominante que se pretendía: si no, la hoja no representa a la
persona y el experimento no se corre.

Las dos hojas son HONESTAS a propósito. Se podría simular a una Dulce que
esconde el arte también en el test, pero eso sería amañar el brazo A para que
falle. Dándole a Holland su mejor caso, si el brazo A igual pierde el dato, el
hallazgo vale.

## Limitaciones, dichas de frente

- 2 perfiles ficticios no dan potencia estadística. Sirven para leer CÓMO cambia
  la conversación, no para afirmar una mejora.
- Circularidad parcial: quien responde el chat y quien recomienda son el mismo
  modelo. Entre ambos media la calificación de O*NET, que el modelo no controla.
- Las respuestas del chat salen a temperatura 0.9: dos corridas no son idénticas.

## Uso

    uv run python experimento_holland.py --self-check   # sin red
    uv run python experimento_holland.py --hojas        # califica las hojas en O*NET (sin Gemini)
    uv run python experimento_holland.py                # el A/B (gasta cuota de Gemini)
    uv run python experimento_holland.py --perfil Dulce # un solo perfil
"""

import argparse
import json
import os
import random
import re

from dotenv import load_dotenv

# ANTES de importar app.recomendar: resuelve MODELO/MODELO_FINAL con os.getenv al
# importarse (ver el tropiezo documentado en cip-en-recomendacion.md §8).
load_dotenv()

from app import holland, preguntas, recomendar  # noqa: E402
from app.filtro import preseleccionar  # noqa: E402

# Se reusa la maquinaria del experimento anterior (la persona respondiendo, el
# bucle de conversación, el catálogo desde JSON y las 4 fijas copiadas de
# Chat.jsx) para que los dos experimentos sean comparables y no haya dos copias
# del mismo alumno simulado.
from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    FIJAS,
    PERFILES,
    _conversar,
    _responder,
    acierta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_holland_resultados.json")

MAX_AREA = 40  # 10 ítems por área, hasta 4 puntos cada uno (escala 1-5, base 0)
ZONA = 4  # Job Zone 4 ≈ ocupaciones que piden carrera universitaria

# --- Los 2 perfiles -------------------------------------------------------
#
# `contexto` y `guion` se toman tal cual de experimento_psicometrico.PERFILES:
# es la misma persona, para poder contrastar con aquellas transcripciones.
# Lo que se agrega acá es `riasec`: su nivel HONESTO de interés 1-5 por área,
# que es lo que genera la hoja de 60 ítems.

RIASEC = {
    # Dulce: le gusta de verdad cuidar gente (S alto) y lo que la engancha es
    # dibujar y editar video (A alto). Nada de campo ni de laboratorio.
    "Dulce": {
        "riasec": {"R": 2, "I": 2, "A": 5, "S": 5, "E": 2, "C": 3},
        "area_dominante": "A",
        # El experimento anterior mostró que su "área esperada" es discutible
        # (salud es el guion de la casa, arte es lo suyo). Se registran las dos
        # y NO se resume en un marcador: ver el informe.
        "claves_casa": ["enfermer", "médic", "psicolog", "fisioterap", "nutric",
                        "odontolog", "clínic", "radiolog"],
        "claves_suyas": ["diseñ", "comunicac", "arte", "gráfic", "audiovisual",
                         "publicid", "period"],
    },
    # Melany: perito contador, lleva las cuentas de la tienda, ordenada y
    # competitiva (C alto, E alto). Su plan declarado —"leyes"— NO vive en
    # Holland: el instrumento no pregunta por planes.
    "Melany": {
        "riasec": {"R": 2, "I": 3, "A": 1, "S": 2, "E": 4, "C": 5},
        "area_dominante": "C",
        "claves_casa": ["jurídic", "derecho", "ley", "abogac"],
        "claves_suyas": ["administra", "empresa", "contad", "audit", "mercadot",
                         "market", "comercio", "econom", "finanz"],
    },
}


def perfiles():
    """Los perfiles del experimento anterior, con sus niveles RIASEC pegados."""
    return [{**p, **RIASEC[p["nombre"]]} for p in PERFILES if p["nombre"] in RIASEC]


# --- La hoja de Holland (sin IA, reproducible) ----------------------------

def hoja(banco: dict, niveles: dict, semilla: str) -> str:
    """Cadena de 60 dígitos: cada ítem contestado con el nivel de SU área ±1.

    El área de cada ítem la dice el banco oficial (`area`: realistic,
    investigative, ...), así que no hay que adivinar el orden de los ítems —
    y de hecho NO vienen en bloques de 10 por área, vienen intercalados.

    El ruido existe porque nadie contesta su propio perfil de forma perfecta;
    es determinista por semilla para que la corrida se pueda repetir."""
    rnd = random.Random(semilla)
    fila = []
    for p in sorted(banco["preguntas"], key=lambda q: q["index"]):
        n = niveles[p["area"][0].upper()] + rnd.choice([-1, 0, 0, 1])
        fila.append(str(min(5, max(1, n))))
    return "".join(fila)


# --- El puente: resultado de Holland -> texto para el prompt --------------

def bloque_texto(p: dict) -> str:
    """El bloque CORTO que ve la IA: código, los 6 puntajes y las ocupaciones.

    Corto a propósito: viaja en cada llamada de next-question. Los 60 ítems
    crudos no aportan nada que el puntaje no diga ya."""
    orden = sorted(p["areas"], key=lambda a: -a["score"])
    lineas = [
        "PERFIL DE INTERESES MEDIDO CON EL TEST DE HOLLAND "
        "(O*NET Interest Profiler, 60 ítems, ya calificado):",
        f"Código Holland: {p['codigo']} — sus tres áreas de mayor interés, de mayor a menor.",
        f"Puntaje por área (0 a {MAX_AREA}; lo que orienta es el contraste entre las seis):",
    ]
    lineas += [f"- {a['letra']} ({a['title']}): {a['score']}" for a in orden]
    lineas.append(
        "Ocupaciones de mejor ajuste según O*NET: "
        + ", ".join(c["title"] for c in p["carreras"][:8])
        + ". Son del mercado de EE. UU.: sirven para ver el TIPO de trabajo que le "
        "encaja, NO como catálogo (el catálogo real va aparte)."
    )
    return "\n".join(lineas)


def sector_texto(p: dict) -> str:
    """Texto con el que `filtro.py` recorta el catálogo al sector de Holland.

    Son las 3 áreas altas (título + descripción oficial) y los títulos de las
    ocupaciones afines, todo en español, que es lo que hace que el solapamiento
    de palabras contra el 'perfil' de cada carrera funcione sin código nuevo.

    ponytail: el recorte reusa `preseleccionar` tal cual, así que este texto
    compite en peso con las respuestas del chat y, por ser largo, las domina.
    Es lo que se quiere al principio de la conversación y discutible al final;
    si el informe muestra que el sector se cierra de más, el siguiente paso es
    ponderarlo (o recortar solo en las primeras N preguntas)."""
    altas = sorted(p["areas"], key=lambda a: -a["score"])[:3]
    partes = [f"{a['title']}. {a['description']}" for a in altas]
    partes.append(" ".join(c["title"] for c in p["carreras"]))
    return " ".join(partes)


def adenda_system(con_fijas: bool) -> str:
    base = (
        "\n\nCONTEXTO ADICIONAL DE ESTE MODO: el estudiante YA respondió el test de "
        "Holland (O*NET Interest Profiler) y su perfil de INTERESES MEDIDO viene en "
        "el mensaje del usuario. Sus intereses ya están medidos por un instrumento "
        "oficial, así que NO vuelvas a preguntarle en general 'qué te gusta': eso "
        "desperdicia un turno. Tu trabajo en este modo es OTRO: averiguar cuál "
        "carrera CONCRETA del catálogo, dentro del sector que sus intereses ya "
        "marcan, encaja mejor con él. Usa el perfil medido para dos cosas: "
        "(1) personalizar la apertura de la pregunta, con tacto, SIN dar cifras y "
        "sin sonar a diagnóstico; y (2) CONTRASTAR: si lo que el estudiante dice "
        "contradice lo medido, haz una pregunta que aclare esa tensión y anótalo en "
        "'alerta_contradiccion'."
    )
    if con_fijas:
        return base
    return base + (
        "\nEn este modo NO hay preguntas iniciales fijas: tus preguntas son lo único "
        "que hay. Además de la carrera concreta, tienes que cubrir tú mismo el "
        "entorno donde se imagina trabajando y qué lo motiva."
    )


# Holland mide intereses. Una sola de las 7 dimensiones del chat — es un
# instrumento de intereses, no de personalidad ni de aptitud.
CUBIERTAS_POR_HOLLAND = ("intereses",)


def _siguiente_pregunta(respuestas, carreras, ctx, cobertura):
    """`preguntas.siguiente_pregunta` con tres cambios: el bloque de Holland
    entra al prompt, el catálogo se recorta al sector de Holland, y la cobertura
    arranca con `intereses` ya cubierta.

    Vive aquí y no en `app/preguntas.py` para no tocar producción (regla 4)."""
    # El recorte al sector: el texto de Holland entra al pre-filtro como una
    # respuesta más, así que el catálogo llega a Gemini ya sesgado al sector.
    # Apagado por defecto — ver `--sector` y el aviso de `_recorte()`: medido
    # sobre el catálogo real, el recorte se lleva por delante las carreras
    # correctas de los dos perfiles, y con eso el A/B mediría el filtro y no las
    # preguntas fijas.
    entrada = {**respuestas, "_holland": ctx["sector"]} if ctx["sector"] else respuestas
    candidatas = preseleccionar(entrada, carreras)
    hechas = sum(1 for d in preguntas.DIMENSIONES
                 if cobertura[d] and d not in ctx["cubiertas_inicio"])
    pendientes = [d for d in ctx["prioritarias"] if not cobertura[d]]

    variable = (
        f"{ctx['bloque']}\n\n"
        f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{preguntas._historial(respuestas)}\n\n"
        f"COBERTURA DE DIMENSIONES (estado real, no lo infieras del historial): "
        f"{preguntas._texto_cobertura(cobertura)}.\n"
        f"Llevas {hechas} pregunta(s) adaptativa(s) de mínimo {preguntas.MIN_ADAPTATIVAS} "
        f"y máximo {preguntas.MAX_ADAPTATIVAS}. "
        + (f"Dimensiones prioritarias AÚN PENDIENTES: {', '.join(pendientes)} — tu "
           "siguiente pregunta DEBE apuntar a una de estas (usa ese valor exacto en "
           "'dimension_objetivo'). terminado DEBE ser false.\n"
           if pendientes and hechas < preguntas.MAX_ADAPTATIVAS
           else "Todas las dimensiones prioritarias ya están cubiertas; puedes "
                "terminar si el ranking ya es claro.\n")
    )
    resp = recomendar.generar(
        model=recomendar.MODELO,
        system=preguntas.SYSTEM + adenda_system(ctx["con_fijas"]),
        catalogo=("CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
                  f"{recomendar._catalogo_texto(candidatas)}"),
        variable=variable,
        schema=preguntas.SiguientePaso,
        temperature=0.5,
    )
    paso = preguntas.SiguientePaso.model_validate_json(recomendar._texto_seguro(resp))
    if paso.dimension_objetivo:
        cobertura[paso.dimension_objetivo] = 1
    # Métrica del recorte: si la carrera que le corresponde a esta persona se
    # cayó del sector, la IA ya no puede recomendarla por más que pregunte bien.
    ctx["recorte"].append({
        "candidatas": len(candidatas),
        "sobrevive_suya": bool([c for c in candidatas if acierta(c.nombre, ctx["claves_suyas"])]),
        "sobrevive_casa": bool([c for c in candidatas if acierta(c.nombre, ctx["claves_casa"])]),
    })
    return paso, recomendar.uso_tokens(resp, recomendar.MODELO)


# --- Los dos brazos -------------------------------------------------------

def _correr_brazo(perfil, cat, p_holland, con_fijas, sector):
    bloque = bloque_texto(p_holland)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    tokens = 0

    if con_fijas:
        for clave, texto, opciones in FIJAS:
            previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
            r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
            respuestas[clave] = r
            log.append({"fija": clave, "pregunta": texto, "respuesta": r})
            print(f"    [fija:{clave}] -> {r[:90]}")

    # Con fijas, entorno y motivaciones ya vienen tocadas (igual que producción);
    # sin fijas no las cubre nadie, así que el chat tiene que perseguirlas.
    cubiertas = set(CUBIERTAS_POR_HOLLAND) | ({"entorno", "motivaciones"} if con_fijas else set())
    cobertura = {d: (1 if d in cubiertas else 0) for d in preguntas.DIMENSIONES}
    ctx = {
        "bloque": bloque,
        "sector": sector_texto(p_holland) if sector else None,
        "con_fijas": con_fijas,
        "cubiertas_inicio": cubiertas,
        "prioritarias": [d for d in preguntas.DIMENSIONES if d not in cubiertas],
        "claves_suyas": perfil["claves_suyas"],
        "claves_casa": perfil["claves_casa"],
        "recorte": [],
    }
    tokens += _conversar(perfil, cat, respuestas,
                         lambda r: _siguiente_pregunta(r, cat, ctx, cobertura), log)
    # La recomendación final también recibe lo medido; el catálogo NO se recorta
    # ahí (filtro.py documenta por qué: no excluir una carrera válida del
    # resultado final, y el CIP ya midió peor priorizando el catálogo).
    res, uso = recomendar.recomendar({**respuestas, "perfil_holland": bloque}, cat)
    return res, respuestas, log, ctx["recorte"], tokens + uso["total_tokens"]


def _resultado(perfil, res, respuestas, log, recorte, tokens):
    top = res.carreras[0]
    return {
        "log": log, "respuestas": respuestas, "tokens": tokens,
        "confianza": res.confianza, "confianza_nota": res.confianza_nota,
        "top": [c.model_dump() for c in res.carreras[:3]],
        "alertas": [x["alerta_contradiccion"] for x in log if x.get("alerta_contradiccion")],
        "adaptativas": sum(1 for x in log if "dimension" in x),
        "recorte": recorte,
        "top1_area_suya": acierta(top.carrera, perfil["claves_suyas"]),
        "top1_area_casa": acierta(top.carrera, perfil["claves_casa"]),
    }


def correr(solo=None, sector=False):
    cat = catalogo()
    lista = [p for p in perfiles() if not solo or p["nombre"].lower() == solo.lower()]
    # Reanudable: basta un 503 de Gemini a la mitad para tirar la corrida.
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    banco = holland.preguntas()
    print(f"Catálogo: {len(cat)} registros carrera-sede · {len(lista)} perfiles"
          + f" · recorte al sector: {'SÍ' if sector else 'no'}"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")

    for perfil in lista:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']}")
        cadena = hoja(banco, perfil["riasec"], perfil["nombre"])
        p_holland = holland.perfil(cadena, zona=ZONA)
        print(f"  Holland: código {p_holland['codigo']} · "
              + " ".join(f"{a['letra']}={a['score']}" for a in p_holland["areas"])
              + f" · {len(p_holland['carreras'])} ocupaciones afines")
        try:
            print("  --- A (solo adaptativas)")
            a = _correr_brazo(perfil, cat, p_holland, con_fijas=False, sector=sector)
            print("  --- B (fijas + adaptativas)")
            b = _correr_brazo(perfil, cat, p_holland, con_fijas=True, sector=sector)
        except Exception as e:  # 503/429 de Gemini: no tirar los perfiles ya hechos
            print(f"  ABORTADO ({type(e).__name__}: {str(e)[:90]}) — se reintenta al volver a correr\n")
            continue
        print(f"  A top1: {a[0].carreras[0].carrera} ({a[0].carreras[0].afinidad}%) "
              f"· confianza {a[0].confianza}%")
        print(f"  B top1: {b[0].carreras[0].carrera} ({b[0].carreras[0].afinidad}%) "
              f"· confianza {b[0].confianza}%\n")
        salida.append({
            "perfil": perfil["nombre"],
            "recorte_al_sector": sector,
            "contexto": perfil["contexto"],
            "guion": perfil["guion"],
            "riasec_real": perfil["riasec"],
            "holland": {"codigo": p_holland["codigo"],
                        "areas": {x["letra"]: x["score"] for x in p_holland["areas"]},
                        "hoja": cadena,
                        "ocupaciones": [c["title"] for c in p_holland["carreras"][:8]]},
            "bloque_prompt": bloque_texto(p_holland),
            "a_solo_adaptativas": _resultado(perfil, *a),
            "b_fijas_y_adaptativas": _resultado(perfil, *b),
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Resultados en {SALIDA}")
    # Este script llama a recomendar.generar() directo, sin pasar por FastAPI, así
    # que su consumo NO queda en la tabla uso_tokens.
    print(recomendar.resumen_gasto())


def _hojas():
    """Califica las hojas simuladas en O*NET (sin gastar cuota de Gemini).

    Es el control que le faltó al experimento del CIP: si el código que devuelve
    el instrumento no contiene el área dominante que se pretendía simular, la
    hoja no representa a la persona y el A/B no probaría nada."""
    banco = holland.preguntas()
    for p in perfiles():
        cadena = hoja(banco, p["riasec"], p["nombre"])
        r = holland.perfil(cadena, zona=ZONA)
        marcas = " ".join(f"{a['letra']}={a['score']}" for a in
                          sorted(r["areas"], key=lambda a: -a["score"]))
        print(f"\n{p['nombre']} — niveles reales {p['riasec']}")
        print(f"  código {r['codigo']} · {marcas}")
        print(f"  ocupaciones: {', '.join(c['title'] for c in r['carreras'][:6])}")
        assert p["area_dominante"] in r["codigo"], (
            f"{p['nombre']}: el área dominante {p['area_dominante']} no quedó en el "
            f"código {r['codigo']} — la hoja no representa a la persona")
    print("\nhojas OK — el área dominante de cada perfil quedó en su código Holland")


def _recorte():
    """¿Qué le hace al catálogo recortarlo al sector de Holland? Sin gastar cuota
    de Gemini (solo la llamada gratuita a O*NET).

    Es la comprobación que se hizo ANTES de correr el A/B, y la que dejó el
    recorte apagado por defecto: el filtro se lleva por delante justo las
    carreras que cada perfil debería poder recibir."""
    cat = catalogo()
    banco = holland.preguntas()
    base = {"departamento": DEPARTAMENTO}
    for p in perfiles():
        ph = holland.perfil(hoja(banco, p["riasec"], p["nombre"]), zona=ZONA)
        sect = sector_texto(ph)
        print(f"\n=== {p['nombre']} · código {ph['codigo']}")
        for etiqueta, entrada in (("sin recorte", base),
                                  ("con recorte al sector", {**base, "_holland": sect})):
            cand = preseleccionar(entrada, cat)
            suyas = sorted({c.nombre for c in cand if acierta(c.nombre, p["claves_suyas"])})
            casa = sorted({c.nombre for c in cand if acierta(c.nombre, p["claves_casa"])})
            print(f"  {etiqueta}: {len(cand)} candidatas · "
                  f"lo suyo={len(suyas)} · lo de la casa={len(casa)}")
            print(f"     lo suyo: {suyas[:4] or '— NINGUNA —'}")
    print("\nSi 'lo suyo' desaparece con el recorte, el A/B con --sector mediría el "
          "filtro y no las preguntas fijas.")


def _self_check():
    cat = catalogo()
    assert len(cat) == 202, len(cat)
    ps = perfiles()
    assert len(ps) == 2, [p["nombre"] for p in ps]

    for p in ps:
        assert set(p["riasec"]) == set("RIASEC"), p["nombre"]
        assert p["area_dominante"] == max(p["riasec"], key=p["riasec"].get)
        for cual in ("claves_suyas", "claves_casa"):
            assert [c for c in cat if acierta(c.nombre, p[cual])], f"{p['nombre']}/{cual}"

    # Banco falso: el self-check no toca la red. Lo que se prueba es que cada
    # ítem se contesta con el nivel de SU área y que la hoja es reproducible.
    falso = {"preguntas": [{"index": i, "area": a}
                           for i, a in enumerate(
                               ["realistic", "investigative", "artistic",
                                "social", "enterprising", "conventional"] * 10, start=1)]}
    niveles = {"R": 1, "I": 2, "A": 3, "S": 4, "E": 5, "C": 1}
    h = hoja(falso, niveles, "x")
    assert len(h) == 60 and set(h) <= set("12345")
    assert h == hoja(falso, niveles, "x"), "la hoja tiene que ser reproducible"
    assert h != hoja(falso, niveles, "y"), "otra semilla, otro ruido"
    # Sin ruido, cada ítem sale exactamente en el nivel de su área.
    sin_ruido = hoja(falso, {k: 3 for k in "RIASEC"}, "z")
    assert set(sin_ruido) <= {"2", "3", "4"}, sin_ruido  # 3 ±1
    # El área alta tiene que quedar más alta que la baja, ruido incluido.
    por_area = {}
    for q, d in zip(falso["preguntas"], h):
        por_area.setdefault(q["area"][0].upper(), []).append(int(d))
    assert sum(por_area["E"]) > sum(por_area["R"]), por_area

    # El bloque del prompt tiene que llevar código, los 6 puntajes y ocupaciones.
    fake = {"codigo": "ASE",
            "areas": [{"letra": l, "title": l, "score": s} for l, s in
                      zip("RIASEC", [8, 10, 38, 33, 20, 15])],
            "carreras": [{"title": "Diseñadores Gráficos"}, {"title": "Editores"}]}
    txt = bloque_texto(fake)
    assert "ASE" in txt and "Diseñadores" in txt and txt.count("- ") == 6
    assert "38" in txt  # los puntajes sí viajan
    # ...pero los 60 dígitos crudos NO: el bloque es corto porque va en CADA
    # llamada de next-question.
    assert not re.search(r"[1-5]{20}", txt), "la hoja cruda no debe viajar en el prompt"
    assert len(txt) < 900, len(txt)

    # Sin fijas, el chat tiene que perseguir también entorno y motivaciones.
    solas = [d for d in preguntas.DIMENSIONES if d not in CUBIERTAS_POR_HOLLAND]
    assert "entorno" in solas and "motivaciones" in solas and "intereses" not in solas
    # Con fijas, las prioritarias son las mismas cuatro de producción.
    con = set(CUBIERTAS_POR_HOLLAND) | {"entorno", "motivaciones"}
    assert {d for d in preguntas.DIMENSIONES if d not in con} == set(preguntas.PRIORITARIAS)

    # La adenda no puede prometer que no hay fijas cuando sí las hay.
    assert "NO hay preguntas iniciales fijas" in adenda_system(False)
    assert "NO hay preguntas iniciales fijas" not in adenda_system(True)

    print(f"self-check OK — {len(cat)} carreras, {len(ps)} perfiles, hoja reproducible")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    ap.add_argument("--hojas", action="store_true", help="califica las hojas en O*NET, sin Gemini")
    ap.add_argument("--recorte", action="store_true",
                    help="qué le hace al catálogo el recorte al sector, sin Gemini")
    ap.add_argument("--sector", action="store_true",
                    help="recorta el catálogo al sector de Holland (ver --recorte antes de usarlo)")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.hojas:
        _hojas()
    elif a.recorte:
        _recorte()
    else:
        correr(a.perfil, sector=a.sector)
