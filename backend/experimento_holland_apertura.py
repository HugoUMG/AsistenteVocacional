"""Experimento A/B: ¿ayuda que el chat NOMBRE el resultado de Holland en su
primera pregunta, en vez de usarlo solo como contexto de fondo?

## Por qué este experimento y no otro

`holland-en-chat.md` ya midió que el bloque de Holland en el prompt **no pesa
en la recomendación** (5/6 corridas ignoraron el área más alta). La conclusión
de esa medición fue que el valor de Holland no está en competir con el LLM por
decidir el ranking — está en la CONVERSACIÓN: que el alumno sienta que el chat
ya lo conoce antes de preguntar nada. Hoy eso es parcial: el bloque de Holland
viaja en el prompt, pero el system prompt solo dice "personaliza la apertura
CON TACTO" — el LLM puede o no usarlo, y si lo usa puede diluirlo en una frase
genérica que el alumno ni nota.

Este experimento prueba si OBLIGAR al chat a nombrar el resultado de forma
explícita en su primera pregunta, y a usar el perfil para decidir QUÉ pregunta
primero (desempatar las áreas más parejas, no una dimensión genérica), cambia
algo medible: no solo el ranking final, sino si la conversación misma se lee
como personalizada.

## Brazos

Los dos son el modo 3 de producción (Holland → chat, con las 4 fijas —
`holland-en-chat.md` ya dejó esa parte decidida) y los dos reciben el MISMO
bloque de Holland en el prompt. Lo único que cambia es la instrucción sobre
qué hacer con él:

- **B — producción.** `adenda_system` tal cual está hoy en
  `experimento_holland.py`: "personaliza la apertura, con tacto, sin cifras".
- **C — apertura explícita + calibrada.** Se agregan dos instrucciones:
  1. La primera pregunta adaptativa DEBE nombrar el código o el área más alta
     de Holland de forma explícita (p. ej. "vi que tu perfil salió fuerte en
     Artístico...").
  2. Si dos áreas están a 5 puntos o menos de diferencia (empate técnico), la
     pregunta debe apuntar a desempatarlas — no a una dimensión genérica.

## Qué se mide que el experimento anterior no midió

`holland-en-chat.md` midió el RESULTADO final (qué carrera ganó). Este mide
también el PROCESO: si la primera pregunta adaptativa efectivamente nombra el
resultado (se busca el código o el nombre del área en el texto), y con qué
área trabaja el desempate cuando el perfil tiene un empate técnico real.

## La hoja de Holland NO la responde Gemini

Misma disciplina que en `experimento_holland.py`: la hoja de 60 ítems se arma
aritméticamente desde el nivel real 1-5 por área de cada perfil (±1 de ruido
determinista) y la califica la API de O*NET, no este script. `--hojas` verifica
que el área dominante quedó en el código antes de gastar cuota de Gemini.

## Perfiles

Se reusan Dulce y Melany de `experimento_holland.py` (mismo `RIASEC`, mismo
`contexto`/`guion`) para poder leer este experimento junto al anterior. Se
agrega un tercer perfil, **Byron**, diseñado a propósito con dos áreas casi
empatadas (R=32, I=30) para poder probar la instrucción de desempate — algo
que Dulce (A=39 vs todo el resto bajo) y Melany (C=36 claro) no permiten
probar porque no tienen ningún empate real.

## Limitaciones

- 3 perfiles ficticios, pocas corridas por brazo: sirve para leer el MECANISMO
  (¿el chat nombra el resultado? ¿el empate se resuelve?), no para afirmar una
  mejora con potencia estadística.
- Igual que en los experimentos anteriores, quien responde el chat y quien
  recomienda son el mismo modelo; entre ambos media la calificación de O*NET.
- Detectar "¿nombró el resultado?" es un regex sobre el texto de la pregunta,
  no un juicio humano — puede haber falsos negativos si el chat parafrasea sin
  usar el código ni el nombre del área.

## Uso

    uv run python experimento_holland_apertura.py --self-check   # sin red
    uv run python experimento_holland_apertura.py --hojas        # califica en O*NET, sin Gemini
    uv run python experimento_holland_apertura.py                # el A/B (gasta cuota)
    uv run python experimento_holland_apertura.py --perfil Byron # un solo perfil
"""

import argparse
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

from app import holland, preguntas, recomendar  # noqa: E402
from app.filtro import preseleccionar  # noqa: E402

from experimento_psicometrico import DEPARTAMENTO, FIJAS, _conversar, _responder, acierta, catalogo  # noqa: E402
from experimento_holland import RIASEC as RIASEC_BASE, bloque_texto, hoja, perfiles as perfiles_base  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_holland_apertura_resultados.json")
ZONA = 4

# --- El tercer perfil: Byron, con un empate técnico real ------------------
#
# R=32 e I=30 (2 puntos de diferencia): "le gusta armar y arreglar motores
# (R) y también le atrae entender por qué fallan (I)" es un empate de verdad,
# no forzado — a diferencia de Dulce/Melany, que tienen un área que domina
# claramente y no sirven para probar el desempate.

BYRON = {
    "nombre": "Byron",
    "contexto": (
        "18 años, perito en mecánica automotriz en Quetzaltenango. Trabaja en el "
        "taller de su tío los fines de semana. Le gusta arreglar motores con las "
        "manos, pero también se queda leyendo manuales técnicos para entender POR "
        "QUÉ falla una pieza, no solo cambiarla. No tiene un plan claro: unos le "
        "dicen que estudie Ingeniería Mecánica, otros que se quede de técnico."
    ),
    "guion": (
        "Es honesto y directo. Si le preguntan qué prefiere entre reparar con las "
        "manos o investigar por qué algo falla, responde con matices reales: "
        "'depende del día, a veces solo quiero resolverlo con las manos, a veces "
        "quiero entender la causa antes de tocar nada'. No inventa un plan que no "
        "tiene si se lo preguntan directamente."
    ),
    "riasec": {"R": 4, "I": 4, "A": 1, "S": 1, "E": 2, "C": 2},
    "area_dominante": "R",  # empate real: puede salir R o I según el ruido
    "claves_empate_r": ["mecánic", "industrial", "electromecánic", "automotriz"],
    "claves_empate_i": ["química", "sistemas", "agronomía", "ambiental"],
}


def perfiles():
    return perfiles_base() + [BYRON]


# --- La adenda del brazo C: apertura explícita + desempate ----------------

def adenda_apertura_explicita(empate: list[str] | None) -> str:
    base = (
        "\n\nCONTEXTO ADICIONAL DE ESTE MODO: el estudiante YA respondió el test de "
        "Holland (O*NET Interest Profiler) y su perfil de INTERESES MEDIDO viene en "
        "el mensaje del usuario. Tu trabajo en este modo es averiguar cuál carrera "
        "CONCRETA del catálogo, dentro del sector que sus intereses ya marcan, "
        "encaja mejor con él.\n\n"
        "REGLA DE APERTURA (obligatoria, solo en tu PRIMERA pregunta adaptativa): "
        "la primera frase DEBE nombrar explícitamente el código o el área de mayor "
        "puntaje de su perfil de Holland tal cual salió en el test — por ejemplo "
        "'Vi que tu test de Holland salió fuerte en Artístico...' — para que el "
        "estudiante note que ya leíste su resultado antes de preguntar. En las "
        "preguntas siguientes no hace falta repetirlo.\n"
        "Después de esa apertura, contrasta: si lo que dice contradice lo medido, "
        "pregunta para aclarar esa tensión y anótalo en 'alerta_contradiccion'."
    )
    if empate:
        base += (
            f"\n\nEMPATE TÉCNICO EN EL PERFIL: las áreas {' y '.join(empate)} quedaron "
            "a 5 puntos o menos de diferencia — no hay una claramente dominante. Tu "
            "PRIMERA pregunta adaptativa debe apuntar a desempatarlas (qué de cada una "
            "le atrae más en concreto), no a una dimensión genérica."
        )
    return base


CUBIERTAS_POR_HOLLAND = ("intereses",)


def _empate(p_holland: dict) -> list[str] | None:
    areas = sorted(p_holland["areas"], key=lambda a: -a["score"])
    if areas[0]["score"] - areas[1]["score"] <= 5:
        return [areas[0]["title"], areas[1]["title"]]
    return None


def _siguiente_pregunta(respuestas, carreras, ctx, cobertura):
    """Igual que `experimento_holland._siguiente_pregunta`, pero sin recorte al
    sector (ya descartado en `holland-en-chat.md`) y con la adenda del brazo."""
    candidatas = preseleccionar(respuestas, carreras)
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
        system=preguntas.SYSTEM + ctx["adenda"],
        catalogo=("CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
                  f"{recomendar._catalogo_texto(candidatas)}"),
        variable=variable,
        schema=preguntas.SiguientePaso,
        temperature=0.5,
    )
    paso = preguntas.SiguientePaso.model_validate_json(recomendar._texto_seguro(resp))
    if paso.dimension_objetivo:
        cobertura[paso.dimension_objetivo] = 1
    return paso, recomendar.uso_tokens(resp, recomendar.MODELO)


NOMBRA_HOLLAND = re.compile(
    r"holland|realista|investigador|artíst|social|emprendedor|convencional",
    re.IGNORECASE,
)


def _correr_brazo(perfil, cat, p_holland, explicito: bool):
    bloque = bloque_texto(p_holland)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []

    for clave, texto, opciones in FIJAS:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})

    cubiertas = set(CUBIERTAS_POR_HOLLAND) | {"entorno", "motivaciones"}
    cobertura = {d: (1 if d in cubiertas else 0) for d in preguntas.DIMENSIONES}
    adenda = (adenda_apertura_explicita(_empate(p_holland) if explicito else None)
              if explicito else
              # Brazo B: la adenda de producción, copiada de experimento_holland.py
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
              "'alerta_contradiccion'.")
    ctx = {
        "bloque": bloque,
        "cubiertas_inicio": cubiertas,
        "prioritarias": [d for d in preguntas.DIMENSIONES if d not in cubiertas],
        "adenda": adenda,
    }
    tokens = _conversar(perfil, cat, respuestas,
                        lambda r: _siguiente_pregunta(r, cat, ctx, cobertura), log)
    res, uso = recomendar.recomendar({**respuestas, "perfil_holland": bloque}, cat)

    primera_adaptativa = next((x for x in log if "dimension" in x), None)
    nombra = bool(primera_adaptativa and NOMBRA_HOLLAND.search(primera_adaptativa.get("pregunta", "")))
    return res, respuestas, log, tokens + uso["total_tokens"], nombra


def _resultado(perfil, res, respuestas, log, tokens, nombra):
    top = res.carreras[0]
    r = {
        "log": log, "respuestas": respuestas, "tokens": tokens,
        "confianza": res.confianza, "confianza_nota": res.confianza_nota,
        "top": [c.model_dump() for c in res.carreras[:3]],
        "alertas": [x["alerta_contradiccion"] for x in log if x.get("alerta_contradiccion")],
        "adaptativas": sum(1 for x in log if "dimension" in x),
        "nombra_holland_en_apertura": nombra,
    }
    if "claves_suyas" in perfil:
        r["top1_area_suya"] = acierta(top.carrera, perfil["claves_suyas"])
        r["top1_area_casa"] = acierta(top.carrera, perfil["claves_casa"])
    else:  # Byron: no hay "casa" vs "suya", hay dos áreas empatadas de verdad
        r["top1_area_r"] = acierta(top.carrera, perfil["claves_empate_r"])
        r["top1_area_i"] = acierta(top.carrera, perfil["claves_empate_i"])
    return r


def correr(solo=None):
    cat = catalogo()
    lista = [p for p in perfiles() if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    banco = holland.preguntas()
    print(f"Catálogo: {len(cat)} registros · {len(lista)} perfiles"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")

    for perfil in lista:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']}")
        cadena = hoja(banco, perfil["riasec"], perfil["nombre"])
        p_holland = holland.perfil(cadena, zona=ZONA)
        empate = _empate(p_holland)
        print(f"  Holland: código {p_holland['codigo']} · "
              + " ".join(f"{a['letra']}={a['score']}" for a in p_holland["areas"])
              + (f" · EMPATE: {empate}" if empate else ""))
        try:
            print("  --- B (producción, apertura pasiva)")
            b = _correr_brazo(perfil, cat, p_holland, explicito=False)
            print("  --- C (apertura explícita + desempate)")
            c = _correr_brazo(perfil, cat, p_holland, explicito=True)
        except Exception as e:
            print(f"  ABORTADO ({type(e).__name__}: {str(e)[:90]}) — se reintenta al volver a correr\n")
            continue
        print(f"  B top1: {b[0].carreras[0].carrera} ({b[0].carreras[0].afinidad}%) · nombra Holland: {b[4]}")
        print(f"  C top1: {c[0].carreras[0].carrera} ({c[0].carreras[0].afinidad}%) · nombra Holland: {c[4]}\n")
        salida.append({
            "perfil": perfil["nombre"],
            "contexto": perfil["contexto"],
            "guion": perfil["guion"],
            "riasec_real": perfil["riasec"],
            "holland": {"codigo": p_holland["codigo"],
                        "areas": {x["letra"]: x["score"] for x in p_holland["areas"]},
                        "hoja": cadena, "empate": empate},
            "b_produccion": _resultado(perfil, *b),
            "c_apertura_explicita": _resultado(perfil, *c),
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Resultados en {SALIDA}")
    print(recomendar.resumen_gasto())


def _hojas():
    banco = holland.preguntas()
    for p in perfiles():
        cadena = hoja(banco, p["riasec"], p["nombre"])
        r = holland.perfil(cadena, zona=ZONA)
        marcas = " ".join(f"{a['letra']}={a['score']}" for a in
                          sorted(r["areas"], key=lambda a: -a["score"]))
        print(f"\n{p['nombre']} — niveles reales {p['riasec']}")
        print(f"  código {r['codigo']} · {marcas} · empate: {_empate(r)}")
        assert p["area_dominante"] in r["codigo"], (
            f"{p['nombre']}: el área dominante no quedó en el código {r['codigo']}")
    print("\nhojas OK")


def _self_check():
    ps = perfiles()
    assert len(ps) == 3, [p["nombre"] for p in ps]
    assert any(p["nombre"] == "Byron" for p in ps)

    fake_empate = {"areas": [{"letra": "R", "title": "Realista", "score": 32},
                              {"letra": "I", "title": "Investigador", "score": 30},
                              {"letra": "C", "title": "Convencional", "score": 10}]}
    assert _empate(fake_empate) == ["Realista", "Investigador"]
    fake_claro = {"areas": [{"letra": "A", "title": "Artístico", "score": 39},
                             {"letra": "S", "title": "Social", "score": 20},
                             {"letra": "C", "title": "Convencional", "score": 10}]}
    assert _empate(fake_claro) is None

    assert "REGLA DE APERTURA" in adenda_apertura_explicita(None)
    con = adenda_apertura_explicita(["Realista", "Investigador"])
    assert "EMPATE TÉCNICO" in con and "Realista y Investigador" in con

    assert NOMBRA_HOLLAND.search("Vi que tu test de Holland salió fuerte en Artístico")
    assert NOMBRA_HOLLAND.search("noté que te atrae mucho lo Realista")
    assert not NOMBRA_HOLLAND.search("¿Qué materia se te hace más fácil en el colegio?")

    print(f"self-check OK — {len(ps)} perfiles ({[p['nombre'] for p in ps]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--hojas", action="store_true")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.hojas:
        _hojas()
    else:
        correr(a.perfil)
