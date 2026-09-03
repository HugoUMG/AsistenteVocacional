"""Comparación de modelo Gemini: ¿vale la pena cambiar `gemini-3.1-flash-lite`
por uno más caro?

Corre el MISMO flujo de producción (4 fijas + adaptativas + recomendación)
contra los mismos perfiles simulados de `experimento_psicometrico.py`, variando
solo el modelo que hace de orientador (`next-question`/`recommend`). El modelo
que actúa de ALUMNO se deja fijo en flash-lite en los tres brazos, para que la
comparación mida al orientador, no a dos actores distintos.

## Modelos comparados

Precios oficiales por 1M tokens (input/output), medidos 2026-08-17:

- `gemini-3.1-flash-lite` (el de hoy): $0.25 / $1.50
- `gemini-3.7-flash` (precio de lanzamiento, vigente hasta 2026-12-31): $0.75 / $3.75
- `gemini-3.5-flash-lite`: $0.30 / $2.50

No se compara `3.1 Pro` ni `3.5/3.6 Flash` completos: para una tarea de
clasificación estructurada contra 35 carreras, cuestan 6-10x sin que haya razón
para esperar que el ranking mejore (ver CLAUDE.md regla 3: no tocar los prompts
sin medir, y aquí el modelo es la variable, no el prompt).

## Qué mide y qué NO mide

Mide: ¿cambia el top1, la confianza o el número de alertas de contradicción al
cambiar de modelo? Con el MISMO prompt y el MISMO catálogo.

NO mide: latencia (fuera del alcance de este script) ni calidad subjetiva del
fraseo (para eso hay que leer las transcripciones en el JSON de salida, como en
los demás `experimento_*.py`).

## Limitaciones, dichas de frente

- Perfiles ficticios (los mismos 5 de `experimento_psicometrico.py`): no dan
  potencia estadística, sirven para leer si algo se mueve.
- Temperature 0.5 en el orientador: dos corridas del mismo modelo no son
  idénticas. Un solo top1 distinto no es evidencia, hay que ver el patrón.

## Uso

    uv run python experimento_modelos.py --self-check   # sin red
    uv run python experimento_modelos.py --perfil Kevin  # 1 perfil x 3 modelos (barato)
    uv run python experimento_modelos.py                 # los 5 perfiles x 3 modelos (gasta cuota)
"""

import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()

from app import preguntas, recomendar  # noqa: E402
from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    FIJAS,
    PERFILES,
    RespuestaAlumno,
    SYSTEM_ALUMNO,
    acierta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_modelos_resultados.json")

ALUMNO_MODELO = "gemini-3.1-flash-lite"  # fijo en los 3 brazos: se compara al orientador, no al actor

MODELOS = {
    "actual": "gemini-3.1-flash-lite",
    "3.5-flash-lite": "gemini-3.5-flash-lite",
}
# 3.7-flash quedó fuera: 4 corridas seguidas (2026-08-17) fallaron con 503
# "currently experiencing..." antes de terminar una sola conversación, agotando
# cuota de ambos proyectos (primaria + respaldo) sin producir resultado.
# Sobrecarga real del lado de Google en un modelo recién lanzado, no un bug de
# este script. Reintentar más tarde agregándolo de nuevo a este dict.

# USD por 1M tokens (input, output). Fuente: búsqueda web 2026-08-17, ver
# decisions/gemini-costos-y-caching.md para el precio de flash-lite confirmado
# contra factura real.
PRECIOS = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}


def costo(modelo: str, prompt_tokens: int, output_tokens: int) -> float:
    pin, pout = PRECIOS[modelo]
    return (prompt_tokens * pin + output_tokens * pout) / 1e6


def _responder(perfil: dict, pregunta: str, contexto_previo: str) -> tuple[str, dict]:
    """Copia de `experimento_psicometrico._responder`, con el modelo FIJO en vez
    de leer el global mutable (que este script cambia para el orientador)."""
    resp = recomendar.generar(
        model=ALUMNO_MODELO,
        system=SYSTEM_ALUMNO,
        catalogo="",
        variable=(f"ESTUDIANTE: {perfil['nombre']}, {perfil['contexto']}\n\n"
                  f"GUION DE SINCERIDAD: {perfil['guion']}\n\n"
                  f"LO QUE YA DIJISTE EN ESTA CONVERSACIÓN:\n{contexto_previo or '(nada aún)'}\n\n"
                  f"PREGUNTA DEL ORIENTADOR:\n{pregunta}"),
        schema=RespuestaAlumno,
        temperature=0.9,
    )
    texto = RespuestaAlumno.model_validate_json(recomendar._texto_seguro(resp)).respuesta.strip()
    return texto, recomendar.uso_tokens(resp, ALUMNO_MODELO)


def _correr_brazo(perfil: dict, cat, modelo: str) -> dict:
    """El flujo de producción completo (4 fijas + adaptativas + recomendación)
    con el orientador forzado a `modelo`. Muta `preguntas.MODELO` y
    `recomendar.MODELO`/`MODELO_FINAL` porque `preguntas.py` importó `MODELO`
    por valor de `recomendar` (ver el import en preguntas.py:12): reasignar
    `recomendar.MODELO` solo no le llega, hay que tocar los tres."""
    preguntas.MODELO = recomendar.MODELO = recomendar.MODELO_FINAL = modelo

    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = []
    gasto = {"prompt": 0, "output": 0}

    def _acumular_gasto(uso):
        gasto["prompt"] += uso["prompt_tokens"]
        gasto["output"] += uso["output_tokens"]

    for clave, texto, opciones in FIJAS:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r, uso = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
        _acumular_gasto(uso)
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})
        print(f"      [fija:{clave}] -> {r[:80]}")

    sid = f"{modelo}-{perfil['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    alertas = 0
    for _ in range(preguntas.MAX_ADAPTATIVAS):
        # Se reusa preguntas.siguiente_pregunta tal cual (ya arma cobertura y
        # prioridades igual que producción); el modelo viaja por el global que
        # ya se seteó arriba.
        paso, uso = preguntas.siguiente_pregunta(respuestas, cat, sid)
        _acumular_gasto(uso)
        if paso.alerta_contradiccion:
            alertas += 1
        if paso.terminado:
            log.append({"terminado": True})
            break
        texto_p = paso.pregunta_texto
        if paso.pregunta_tipo == "opcion":
            texto_p += "\nOpciones: " + " / ".join(o.label for o in paso.opciones)
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r, uso = _responder(perfil, texto_p, previo)
        _acumular_gasto(uso)
        respuestas[paso.pregunta_texto] = r
        log.append({"dimension": paso.dimension_objetivo, "pregunta": paso.pregunta_texto, "respuesta": r})
        print(f"      [{paso.dimension_objetivo or '-'}] {paso.pregunta_texto[:60]} -> {r[:60]}")

    res, uso = recomendar.recomendar(respuestas, cat)
    _acumular_gasto(uso)
    top = res.carreras[0]
    return {
        "modelo": modelo,
        "top1": top.carrera,
        "afinidad": top.afinidad,
        "confianza": res.confianza,
        "alertas_contradiccion": alertas,
        "acierta_area": acierta(top.carrera, perfil["claves"]) if perfil["claves"] else None,
        "prompt_tokens": gasto["prompt"],
        "output_tokens": gasto["output"],
        "costo_usd": round(costo(modelo, gasto["prompt"], gasto["output"]), 4),
        "log": log,
    }


def correr(solo=None):
    cat = catalogo()
    perfiles = [p for p in PERFILES if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    print(f"Catálogo: {len(cat)} registros · {len(perfiles)} perfiles x {len(MODELOS)} modelos"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")

    modelo_original_pg, modelo_original_rc, modelo_original_rf = (
        preguntas.MODELO, recomendar.MODELO, recomendar.MODELO_FINAL)
    try:
        for perfil in perfiles:
            if perfil["nombre"] in hechos:
                continue
            print(f"=== {perfil['nombre']} ({perfil['area_esperada']})")
            brazos = {}
            try:
                for etiqueta, modelo in MODELOS.items():
                    print(f"  --- {etiqueta} ({modelo})")
                    brazos[etiqueta] = _correr_brazo(perfil, cat, modelo)
            except Exception as e:  # 429/503: no tirar los perfiles ya hechos
                print(f"  ABORTADO ({type(e).__name__}: {str(e)[:90]}) — se reintenta al volver a correr\n")
                continue
            for etiqueta, b in brazos.items():
                print(f"  {etiqueta}: {b['top1']} ({b['afinidad']}%) · confianza {b['confianza']}% "
                      f"· ${b['costo_usd']}")
            top1s = {b["top1"] for b in brazos.values()}
            print(f"  {'MISMO top1 en los 3' if len(top1s) == 1 else 'top1 CAMBIÓ entre modelos'}\n")
            salida.append({
                "perfil": perfil["nombre"], "area_esperada": perfil["area_esperada"],
                "mismo_top1": len(top1s) == 1, "brazos": brazos,
            })
            json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    finally:
        preguntas.MODELO, recomendar.MODELO, recomendar.MODELO_FINAL = (
            modelo_original_pg, modelo_original_rc, modelo_original_rf)

    total = sum(b["costo_usd"] for s in salida for b in s["brazos"].values())
    print(f"Resultados en {SALIDA}\nCosto total estimado: ${total:.4f}")


def _self_check():
    assert set(MODELOS.values()) <= set(PRECIOS), "cada modelo comparado necesita precio"
    assert costo("gemini-3.1-flash-lite", 1_000_000, 0) == 0.25
    assert costo("gemini-3.1-flash-lite", 0, 1_000_000) == 1.50
    assert costo("gemini-3.7-flash", 1_000_000, 1_000_000) == 0.75 + 3.75
    cat = catalogo()
    assert len(cat) == 202, len(cat)
    print("self-check OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre (barato)")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    else:
        correr(a.perfil)
