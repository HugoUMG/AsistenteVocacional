"""Experimento A/B: darle a Holland un TURNO OBLIGADO de sondeo en el chat.

## La hipótesis, y por qué es distinta de lo ya medido

Holland no mueve la recomendación. Se midió tres veces y las tres dieron lo
mismo: como prosa en el prompt (`holland-en-chat.md` §5.2), como orden del
catálogo (`holland-estructura.md` §4) y con ese catálogo revisado a mano (§9).

El mecanismo del fallo está diagnosticado: el alumno **declara** una cosa, el
test **mide** otra, y el modelo le hace caso a lo declarado. Los tres intentos
atacaron el momento de **recomendar**, o sea le pidieron al modelo que ponderara
mejor. Este ataca el momento de **preguntar**.

La diferencia importa porque el único experimento de este proyecto que midió una
MEJORA fue justamente de dirección de preguntas: `cobertura-dimensiones.md` pasó
de 40% a 100% de cumplimiento y de 7/10 a 10/10 de acierto dirigiendo el vector
de cobertura. La palanca de las preguntas funciona; la de la recomendación no.

## Qué está roto hoy, en concreto

`app/holland.py::adenda_chat` YA le dice al modelo que contraste:

> "Después de esa apertura, contrasta: si lo que dice contradice lo medido,
> pregunta para aclarar esa tensión y anótalo en 'alerta_contradiccion'."

O sea que la instrucción de arbitraje **ya está en producción**. Lo que no
existe es la **obligación**: en `app/preguntas.py`, `intereses` arranca cubierta
(`COBERTURA_INICIAL`, por las 4 preguntas fijas) y no está en `PRIORITARIAS`.
El modelo puede saltarse el contraste sin costo, porque ninguna dimensión
pendiente lo empuja a gastar un turno ahí.

**La intervención: cuando hay perfil de Holland, `intereses` deja de arrancar
cubierta y pasa a ser prioritaria.** Los intereses declarados en las 4 fijas ya
no dan por saldada la dimensión que el test mide de otra forma.

## Brazos

Los dos usan la adenda de producción (`holland.adenda_chat`), las 4 preguntas
fijas y el mismo catálogo sin recortar. La única variable es la semilla de
cobertura:

- **VIEJO** — producción de hoy: `intereses` cubierta, prioritarias = las 4
  normales (personalidad, habilidades, valores, estilo_cognitivo).
- **NUEVO** — `intereses` PENDIENTE y primera en la lista de prioritarias.

## Por qué acá NO se puede compartir la conversación

`holland-estructura.md` §4 comparte una sola conversación entre brazos para
aislar la variable, y ahí se puede porque lo único que cambia es el catálogo del
paso final. Acá la intervención **cambia la conversación misma**, así que cada
brazo tiene que conversar por su cuenta.

Eso reintroduce el problema que aquel informe documenta: la varianza entre
corridas fue MAYOR que la varianza entre brazos. Por eso este experimento corre
`REPETICIONES` conversaciones por brazo y por perfil, y se lee por tasa, no por
una corrida suelta.

## Uso

    uv run python experimento_holland_sondeo.py --self-check   # sin red
    uv run python experimento_holland_sondeo.py                # el A/B
    uv run python experimento_holland_sondeo.py --perfil Dulce
"""

import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()  # antes de importar recomendar: resuelve MODELO con os.getenv

from app import holland, preguntas, recomendar  # noqa: E402
from app.filtro import preseleccionar  # noqa: E402
from experimento_holland import (  # noqa: E402
    DEPARTAMENTO, ZONA, acierta, bloque_texto, catalogo, hoja, perfiles,
)
from experimento_psicometrico import FIJAS, _conversar, _responder  # noqa: E402

SALIDA = os.path.join(os.path.dirname(__file__), "data", "tests",
                      "experimento_holland_sondeo.json")

# Conversaciones por brazo y por perfil. Con 1 sola no se puede leer nada: los
# brazos no comparten conversación y la varianza entre corridas es alta.
REPETICIONES = 3

# Las que las 4 preguntas fijas dejan tocadas, igual que COBERTURA_INICIAL.
POR_LAS_FIJAS = ("intereses", "entorno", "motivaciones")


def _semilla(sondear_intereses: bool) -> tuple[dict[str, int], list[str]]:
    """(cobertura inicial, prioritarias) de cada brazo.

    Es TODA la diferencia entre VIEJO y NUEVO. Se devuelve junta para que el
    informe pueda imprimir con qué arrancó cada brazo y no haya que deducirlo.
    """
    cubiertas = set(POR_LAS_FIJAS)
    prioritarias = list(preguntas.PRIORITARIAS)
    if sondear_intereses:
        cubiertas.discard("intereses")
        # Primera de la lista a propósito: si queda al final, el chat gasta sus
        # turnos en las otras cuatro y se queda sin ninguno para el contraste.
        prioritarias = ["intereses"] + prioritarias
    return ({d: (1 if d in cubiertas else 0) for d in preguntas.DIMENSIONES},
            prioritarias)


def _siguiente_pregunta(respuestas, carreras, ctx, cobertura):
    """`preguntas.siguiente_pregunta` con la cobertura y las prioritarias
    inyectadas desde el brazo.

    Vive acá y no en `app/preguntas.py` para no tocar producción (regla 4),
    igual que `experimento_holland._siguiente_pregunta`. Salvo la semilla, el
    prompt es el de producción: misma SYSTEM, misma adenda, mismo catálogo sin
    recortar.
    """
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
        system=preguntas.SYSTEM + holland.adenda_chat(ctx["puntajes"]),
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


def _correr_brazo(perfil, cat, p_holland, puntajes, sondear_intereses):
    bloque = bloque_texto(p_holland)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    tokens = 0

    for clave, texto, opciones in FIJAS:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})
        print(f"    [fija:{clave}] -> {r[:80]}")

    cobertura, prioritarias = _semilla(sondear_intereses)
    ctx = {
        "bloque": bloque,
        "puntajes": puntajes,
        "cubiertas_inicio": {d for d, v in cobertura.items() if v},
        "prioritarias": prioritarias,
    }
    tokens += _conversar(perfil, cat, respuestas,
                         lambda r: _siguiente_pregunta(r, cat, ctx, cobertura), log)
    res, uso = recomendar.recomendar({**respuestas, "perfil_holland": bloque}, cat)
    return res, respuestas, log, tokens + uso["total_tokens"]


def _resultado(perfil, res, respuestas, log, tokens):
    top = res.carreras[0]
    dims = [x["dimension"] for x in log if "dimension" in x]
    return {
        "log": log, "respuestas": respuestas, "tokens": tokens,
        "confianza": res.confianza, "confianza_nota": res.confianza_nota,
        "top": [c.model_dump() for c in res.carreras[:3]],
        "dimensiones": dims,
        "adaptativas": len(dims),
        # ¿Se gastó de verdad un turno en sondear los intereses medidos?
        "sondeo_intereses": "intereses" in dims,
        "alertas": [x["alerta_contradiccion"] for x in log if x.get("alerta_contradiccion")],
        "top1_area_suya": acierta(top.carrera, perfil["claves_suyas"]),
        "top1_area_casa": acierta(top.carrera, perfil["claves_casa"]),
        "suya_en_top3": any(acierta(c.carrera, perfil["claves_suyas"]) for c in res.carreras[:3]),
    }


def correr(solo=None):
    cat = catalogo()
    banco = holland.preguntas()
    lista = [p for p in perfiles() if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    hechos = {(s["perfil"], s["brazo"], s["corrida"]) for s in salida}

    for perfil in lista:
        ph = holland.perfil(hoja(banco, perfil["riasec"], perfil["nombre"]), zona=ZONA)
        puntajes = {a["letra"]: a["score"] for a in ph["areas"]}
        print(f"=== {perfil['nombre']} · Holland {ph['codigo']} · "
              + " ".join(f"{l}={s}" for l, s in puntajes.items()))

        for brazo, sondear in (("viejo", False), ("nuevo", True)):
            for corrida in range(1, REPETICIONES + 1):
                if (perfil["nombre"], brazo, corrida) in hechos:
                    continue
                print(f"  -- {brazo.upper()} corrida {corrida}/{REPETICIONES}")
                res, respuestas, log, tokens = _correr_brazo(
                    perfil, cat, ph, puntajes, sondear)
                r = _resultado(perfil, res, respuestas, log, tokens)
                print(f"     top1: {res.carreras[0].carrera} ({res.carreras[0].afinidad}%) · "
                      f"sondeo_intereses={r['sondeo_intereses']} · suya={r['top1_area_suya']}")
                salida.append({
                    "perfil": perfil["nombre"], "brazo": brazo, "corrida": corrida,
                    "holland": {"codigo": ph["codigo"], "areas": puntajes},
                    **r,
                })
                json.dump(salida, open(SALIDA, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
    print(f"\nResultados en {SALIDA}")
    resumen()
    print(recomendar.resumen_gasto())


def resumen():
    """Tasas por brazo. Sin red: lee el JSON."""
    if not os.path.exists(SALIDA):
        print("No hay resultados todavía.")
        return
    datos = json.load(open(SALIDA, encoding="utf-8"))
    perfiles_vistos = sorted({d["perfil"] for d in datos})
    print("\n" + "=" * 72)
    for p in perfiles_vistos:
        print(f"\n=== {p}")
        for brazo in ("viejo", "nuevo"):
            filas = [d for d in datos if d["perfil"] == p and d["brazo"] == brazo]
            if not filas:
                continue
            n = len(filas)
            suya = sum(1 for f in filas if f["top1_area_suya"])
            casa = sum(1 for f in filas if f["top1_area_casa"])
            top3 = sum(1 for f in filas if f["suya_en_top3"])
            sondeo = sum(1 for f in filas if f["sondeo_intereses"])
            alertas = sum(1 for f in filas if f["alertas"])
            adapt = sum(f["adaptativas"] for f in filas) / n
            tok = sum(f["tokens"] for f in filas) / n
            print(f"  {brazo.upper():6} n={n} · top1 suya {suya}/{n} · top1 casa {casa}/{n} · "
                  f"suya en top-3 {top3}/{n}")
            print(f"         sondeó intereses {sondeo}/{n} · alertas {alertas}/{n} · "
                  f"{adapt:.1f} adaptativas · {tok:,.0f} tokens de promedio")
            print("         top1: " + " | ".join(f["top"][0]["carrera"][:34] for f in filas))


def _self_check():
    # La semilla es toda la intervención: si esto se rompe, los brazos son iguales.
    cob_v, pri_v = _semilla(False)
    cob_n, pri_n = _semilla(True)
    assert cob_v["intereses"] == 1, "el brazo VIEJO debe arrancar con intereses cubierta"
    assert cob_n["intereses"] == 0, "el brazo NUEVO debe arrancar con intereses PENDIENTE"
    assert "intereses" not in pri_v, "VIEJO no persigue intereses (producción de hoy)"
    assert pri_n[0] == "intereses", "NUEVO la persigue, y primero"
    # Lo único que cambia es intereses: el resto de dimensiones, igual en ambos.
    assert {d: v for d, v in cob_v.items() if d != "intereses"} == \
           {d: v for d, v in cob_n.items() if d != "intereses"}
    assert set(pri_n) - {"intereses"} == set(pri_v)
    # Las fijas de producción cubren 3 dimensiones, no más.
    assert sum(cob_v.values()) == 3, cob_v
    assert sum(cob_n.values()) == 2, cob_n

    cat = catalogo()
    assert len(cat) > 50, len(cat)
    ps = perfiles()
    assert len(ps) == 2, [p["nombre"] for p in ps]
    # `acierta` es la métrica del informe: si no discrimina, el A/B no mide nada.
    dulce = [p for p in ps if p["nombre"] == "Dulce"][0]
    assert acierta("Licenciatura en Comunicación y Diseño", dulce["claves_suyas"])
    assert acierta("Licenciatura en Enfermería", dulce["claves_casa"])
    assert not acierta("Licenciatura en Enfermería", dulce["claves_suyas"])
    print(f"self-check OK — {len(cat)} registros · {len(ps)} perfiles · "
          f"{REPETICIONES} corridas por brazo · "
          f"VIEJO prioritarias={pri_v} · NUEVO prioritarias={pri_n}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    ap.add_argument("--resumen", action="store_true", help="tasas del JSON, sin red")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.resumen:
        resumen()
    else:
        correr(a.perfil)
