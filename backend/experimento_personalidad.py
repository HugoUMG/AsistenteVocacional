"""Experimento A/B: el test corto de personalidad/valores/estilo cognitivo
antes del chat (modo `/personalidad`, ver docs/personalidad.md), ¿cambia el
top-1 de la recomendación?

## Por qué este experimento

`app/personalidad.py` y su wiring en `app/preguntas.py`/`app/main.py` ya están
en producción (igual patrón que Holland: bloque de texto + cobertura de
dimensiones sembrada), pero SIN medir — regla 4 del proyecto: todo cambio de
heurística se mide antes de aceptarse. Este script cierra ese pendiente.

A diferencia de `experimento_holland.py` y `experimento_psicometrico.py`
(que tuvieron que DUPLICAR `preguntas.siguiente_pregunta` localmente porque
Holland/psicométrico no estaban wireados en producción todavía), acá se llama
la función de producción TAL CUAL, con `personalidad=` y
`personalidad_cobertura=`: es literalmente el código que corre en el chat
real, no una reimplementación paralela.

## Brazos

Los dos llevan las 4 preguntas fijas (no se tocan, ver `holland-en-chat.md`):

- **VIEJO** — producción de hoy, sin el test corto. Es `brazo_viejo` de
  `experimento_psicometrico.py`, reusado tal cual.
- **NUEVO** — el test corto se responde ANTES del chat; su bloque entra al
  prompt y la cobertura arranca con personalidad/valores/estilo_cognitivo ya
  cubiertas, así que las adaptativas solo tienen que cubrir habilidades.

## Los perfiles

Se reusan los 5 de `experimento_psicometrico.py` (mismo `contexto`/`guion`,
comparable con esos resultados). Sus `rasgos` (los 6 de personalidad) ya
calzan 1:1 con `app/personalidad.py` porque reusa el mismo banco. Se agregan
niveles 1-5 de valores y estilo cognitivo por perfil (`RASGOS_EXTRA`),
leídos a mano de cada biografía — es una aproximación razonable, no una
medición real de esos perfiles ficticios.

## La hoja del test corto NO la responde Gemini

Misma disciplina que en los experimentos anteriores: se arma aritméticamente
desde los niveles honestos (±1 de ruido determinista) y la califica
`app/personalidad.py`, no este script.

## Limitaciones, dichas de frente

- 5 perfiles ficticios no dan potencia estadística: sirve para leer el
  MECANISMO (¿la cobertura se siembra?, ¿cambia el top-1?), no para afirmar
  una mejora.
- Los niveles de valores/estilo cognitivo por perfil son una aproximación de
  quien escribió el experimento, no algo medido.
- Circularidad parcial: quien responde el chat y quien recomienda son el
  mismo modelo.

## Uso

    uv run python experimento_personalidad.py --self-check   # sin red
    uv run python experimento_personalidad.py --hojas        # califica las hojas, sin red ni Gemini
    uv run python experimento_personalidad.py                # el A/B (gasta cuota)
    uv run python experimento_personalidad.py --perfil Kevin # un solo perfil
"""

import argparse
import json
import os
import random

from dotenv import load_dotenv

load_dotenv()

from app import personalidad, preguntas, recomendar  # noqa: E402

from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    FIJAS,
    PERFILES,
    _conversar,
    _responder,
    acierta,
    brazo_viejo,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_personalidad_resultados.json")

# Niveles 1-5 de valores/estilo cognitivo por perfil, leídos de su biografía en
# experimento_psicometrico.PERFILES (no están ahí porque ese script es previo a
# este instrumento). Los 6 rasgos de personalidad SÍ se reusan tal cual de
# `perfil["rasgos"]`: son el mismo banco.
RASGOS_EXTRA = {
    # Kevin: arma y repara (practico_manual alto), evita gente/liderazgo (baja
    # ayuda_social), le gusta resolver a su manera (autonomia_creativa media).
    "Kevin": {
        "valores": {"ayuda_social": 2, "seguridad_economica": 3, "autonomia_creativa": 4, "justicia": 3},
        "estilo_cognitivo": {"logico_estructurado": 3, "creativo_intuitivo": 3, "practico_manual": 5, "analitico_critico": 3},
    },
    # Dulce: cuidar gente de verdad (ayuda_social alta) y dibujar/editar
    # (creativo_intuitivo alto), nada de estructura rígida.
    "Dulce": {
        "valores": {"ayuda_social": 5, "seguridad_economica": 3, "autonomia_creativa": 4, "justicia": 3},
        "estilo_cognitivo": {"logico_estructurado": 2, "creativo_intuitivo": 5, "practico_manual": 3, "analitico_critico": 2},
    },
    # Brandon: indiferente, sin distinción real entre rasgos.
    "Brandon": {
        "valores": {"ayuda_social": 3, "seguridad_economica": 3, "autonomia_creativa": 3, "justicia": 3},
        "estilo_cognitivo": {"logico_estructurado": 3, "creativo_intuitivo": 3, "practico_manual": 3, "analitico_critico": 3},
    },
    # Melany: ordenada y competitiva, seguridad económica alta, estructura
    # sobre creatividad (su "leyes" declarado no es lo que estos ítems miden).
    "Melany": {
        "valores": {"ayuda_social": 2, "seguridad_economica": 5, "autonomia_creativa": 2, "justicia": 3},
        "estilo_cognitivo": {"logico_estructurado": 5, "creativo_intuitivo": 2, "practico_manual": 2, "analitico_critico": 4},
    },
    # Josué: práctico y manual (la milpa), poco interés en estructura formal.
    "Josué": {
        "valores": {"ayuda_social": 3, "seguridad_economica": 3, "autonomia_creativa": 3, "justicia": 3},
        "estilo_cognitivo": {"logico_estructurado": 2, "creativo_intuitivo": 3, "practico_manual": 5, "analitico_critico": 2},
    },
}


# --- La hoja del test corto (sin IA, reproducible) -------------------------

def _hoja(perfil: dict, semilla: int = 7) -> dict:
    """{id_item: 1..5} para los 48 ítems, desde los niveles honestos del perfil
    (los 6 de personalidad + los 8 de RASGOS_EXTRA) con ±1 de ruido determinista."""
    rnd = random.Random(f"{perfil['nombre']}-personalidad-{semilla}")
    extra = RASGOS_EXTRA[perfil["nombre"]]
    niveles = {**perfil["rasgos"], **extra["valores"], **extra["estilo_cognitivo"]}
    hoja = {}
    for i, _, _, rasgo, signo in personalidad.ITEMS:
        nivel = min(5, max(1, niveles[rasgo] + rnd.choice([-1, 0, 0, 1])))
        hoja[i] = nivel if signo == 1 else 6 - nivel
    return hoja


COBERTURA_EXTRA = {"personalidad": 1, "valores": 1, "estilo_cognitivo": 1}


# --- El brazo NUEVO: test corto + fijas + adaptativas -----------------------

def brazo_nuevo(perfil, cat, puntajes):
    bloque = personalidad.bloque(puntajes)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    tokens = 0
    for clave, texto, opciones in FIJAS:
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}",
                       "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre"))
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})
        print(f"    [fija:{clave}] -> {r[:90]}")
    sid = f"nuevo-personalidad-{perfil['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    tokens += _conversar(
        perfil, cat, respuestas,
        lambda r: preguntas.siguiente_pregunta(
            r, cat, sid, personalidad=bloque, personalidad_cobertura=COBERTURA_EXTRA,
        ),
        log,
    )
    res, uso = recomendar.recomendar(
        {**respuestas, "perfil_personalidad": bloque}, cat, personalidad=bloque,
    )
    return res, respuestas, log, tokens + uso["total_tokens"]


def correr(solo=None):
    cat = catalogo()
    perfiles = [p for p in PERFILES if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    print(f"Catálogo: {len(cat)} registros carrera-sede · {len(perfiles)} perfiles"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")

    for perfil in perfiles:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']} ({perfil['area_esperada']})")
        puntajes = personalidad.calificar(_hoja(perfil))
        print(f"  test corto: personalidad {puntajes['personalidad']} · "
              f"valores {puntajes['valores']} · estilo dominante {puntajes['estilo_dominante']}")
        try:
            print("  --- VIEJO (producción, sin test corto)")
            r_v, resp_v, log_v, tok_v = brazo_viejo(perfil, cat)
            print("  --- NUEVO (test corto antes del chat)")
            r_n, resp_n, log_n, tok_n = brazo_nuevo(perfil, cat, puntajes)
        except Exception as e:
            print(f"  ABORTADO ({type(e).__name__}: {str(e)[:90]}) — se reintenta al volver a correr\n")
            continue
        tv, tn = r_v.carreras[0], r_n.carreras[0]
        adap_v = sum(1 for x in log_v if "dimension" in x)
        adap_n = sum(1 for x in log_n if "dimension" in x)
        print(f"  VIEJO top1: {tv.carrera} ({tv.afinidad}%) · {adap_v} adaptativas")
        print(f"  NUEVO top1: {tn.carrera} ({tn.afinidad}%) · {adap_n} adaptativas\n")
        salida.append({
            "perfil": perfil["nombre"],
            "contexto": perfil["contexto"],
            "guion": perfil["guion"],
            "area_esperada": perfil["area_esperada"],
            "rasgos_reales": perfil["rasgos"],
            "rasgos_extra": RASGOS_EXTRA[perfil["nombre"]],
            "test_corto": puntajes,
            "bloque_prompt": personalidad.bloque(puntajes),
            "viejo": {"log": log_v, "respuestas": resp_v, "tokens": tok_v, "adaptativas": adap_v,
                      "confianza": r_v.confianza, "confianza_nota": r_v.confianza_nota,
                      "top": [c.model_dump() for c in r_v.carreras[:3]],
                      "ok": acierta(tv.carrera, perfil["claves"]) if perfil["claves"] else None},
            "nuevo": {"log": log_n, "respuestas": resp_n, "tokens": tok_n, "adaptativas": adap_n,
                      "confianza": r_n.confianza, "confianza_nota": r_n.confianza_nota,
                      "top": [c.model_dump() for c in r_n.carreras[:3]],
                      "ok": acierta(tn.carrera, perfil["claves"]) if perfil["claves"] else None},
            "top1_coincide": tv.carrera == tn.carrera,
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Resultados en {SALIDA}")
    print(recomendar.resumen_gasto())


def _hojas():
    """Califica las 5 hojas simuladas sin gastar cuota de Gemini."""
    for p in PERFILES:
        puntajes = personalidad.calificar(_hoja(p))
        print(f"\n{p['nombre']}")
        print("  personalidad: " + ", ".join(f"{k} {v}" for k, v in puntajes["personalidad"].items()))
        print("  valores: " + ", ".join(f"{k} {v}" for k, v in puntajes["valores"].items()))
        print("  estilo: " + ", ".join(f"{k} {v}" for k, v in puntajes["estilo_cognitivo"].items())
              + f" -> dominante: {puntajes['estilo_dominante']}")


def _self_check():
    assert set(RASGOS_EXTRA) == {p["nombre"] for p in PERFILES}
    for nombre, extra in RASGOS_EXTRA.items():
        assert set(extra["valores"]) == set(personalidad.RASGOS_VALORES)
        assert set(extra["estilo_cognitivo"]) == set(personalidad.RASGOS_ESTILO)

    kevin = next(p for p in PERFILES if p["nombre"] == "Kevin")
    h1, h2 = _hoja(kevin), _hoja(kevin)
    assert h1 == h2, "la hoja tiene que ser reproducible"
    assert set(h1) == {i for i, *_ in personalidad.ITEMS}
    assert personalidad.valida(h1)

    p = personalidad.calificar(h1)
    # Kevin: practico_manual alto (5), logico_estructurado más bajo (3).
    assert p["estilo_cognitivo"]["practico_manual"] > p["estilo_cognitivo"]["logico_estructurado"]

    # Melany: seguridad_economica alta (5) domina sobre autonomia_creativa (2).
    melany = next(p for p in PERFILES if p["nombre"] == "Melany")
    pm = personalidad.calificar(_hoja(melany))
    assert pm["valores"]["seguridad_economica"] > pm["valores"]["autonomia_creativa"]

    bloque = personalidad.bloque(p)
    assert "PERSONALIDAD" in bloque and "VALORES" in bloque and "ESTILO COGNITIVO" in bloque

    # El brazo NUEVO no puede arrancar preguntando lo que el test ya midió.
    cob = {d: (1 if d in COBERTURA_EXTRA else 0) for d in preguntas.DIMENSIONES}
    pendientes = [d for d in preguntas.PRIORITARIAS if not cob[d]]
    assert pendientes == ["habilidades"], pendientes

    print(f"self-check OK — {len(RASGOS_EXTRA)} perfiles, hoja reproducible, "
          "solo 'habilidades' queda pendiente con el test corto")


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
