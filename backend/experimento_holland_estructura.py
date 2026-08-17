"""Experimento A/B: Holland como ESTRUCTURA (vector RIASEC sobre el catálogo).

`experiments/holland-en-chat.md` §5.2 midió que el bloque de texto con el
resultado de Holland en el prompt **no mueve la recomendación**: con A=39 en el
prompt, 5 de 6 corridas dieron un top-1 de otra área. La conclusión fue que un
bloque de prosa es contexto, no peso, y que si Holland tiene que pesar entra
como estructura: el catálogo codificado con los códigos RIASEC que O*NET publica
por ocupación, y el ranking ordenado por afinidad.

Esto mide justamente eso.

## Brazos

Los dos reciben **la misma conversación**: se corre el chat de producción (4
fijas + adaptativas, con el bloque de Holland en el prompt) UNA vez por perfil, y
las mismas respuestas alimentan las dos recomendaciones finales. La única
variable es el catálogo que ve Gemini al recomendar:

- **VIEJO** — producción de hoy: catálogo completo, Holland solo como prosa.
- **NUEVO** — `HOLLAND_EN_RECOMENDACION=1`: el catálogo llega ORDENADO por
  correlación entre los seis puntajes del alumno y el vector RIASEC de cada
  carrera. Sin cortar: `--ranking` mostró que cualquier corte razonable deja
  fuera la carrera correcta del perfil artístico.

Compartir la conversación es lo mismo que hizo `experimento_cip.py` y es lo que
aísla la variable: si los brazos conversaran por separado, la varianza entre
corridas (que en el experimento anterior fue MAYOR que la varianza entre brazos)
se comería el efecto.

## Los vectores no los inventa el modelo

Salen de `codificar_holland.py`: búsqueda en el O*NET en español + el perfil de
intereses oficial de cada ocupación. Es la ventaja que el CIP no tenía
(`experiments/cip-en-recomendacion.md` §6: allá el propio Gemini respondía el
instrumento y el A/B terminó midiendo un perfil equivocado).

## La puerta previa, sin gastar cuota

`--ranking` responde antes que nada: con el catálogo ordenado por afinidad,
¿dónde queda la carrera que le corresponde a cada perfil? Si el ordenamiento la
tira fuera del corte, el A/B mediría el filtro y no la hipótesis — es la lección
de §3 del experimento anterior, donde el recorte al sector borraba justo las
carreras correctas.

## Uso

    uv run python experimento_holland_estructura.py --self-check  # sin red
    uv run python experimento_holland_estructura.py --ranking     # sin Gemini
    uv run python experimento_holland_estructura.py               # el A/B
"""

import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()  # antes de importar recomendar: resuelve MODELO con os.getenv

from app import holland, holland_filtro, recomendar  # noqa: E402
from experimento_holland import (  # noqa: E402
    DEPARTAMENTO, ZONA, _correr_brazo, acierta, bloque_texto, catalogo, hoja, perfiles,
)

SALIDA = os.path.join(os.path.dirname(__file__), "data", "tests",
                      "experimento_holland_estructura.json")


def _puntajes(p_holland: dict) -> dict[str, int]:
    return {a["letra"]: a["score"] for a in p_holland["areas"]}


def _posiciones(cat, puntajes, claves):
    """En qué puesto del catálogo ordenado por afinidad caen esas carreras."""
    orden = holland_filtro.priorizar(cat, puntajes, top=len(cat))
    vistos, out = set(), []
    for i, c in enumerate(orden, 1):
        if c.nombre not in vistos and acierta(c.nombre, claves):
            vistos.add(c.nombre)
            out.append((i, c.nombre, round(holland_filtro.afinidad(c, puntajes), 2)))
    return out


def ranking():
    """La puerta previa: ¿el orden por afinidad conserva la carrera correcta?"""
    cat = catalogo()
    banco = holland.preguntas()
    corte = 30  # el corte que usaba cip_filtro, para ver qué se llevaría por delante
    print(f"Catálogo: {len(cat)} registros · TOP_HOLLAND={holland_filtro.TOP_HOLLAND} "
          f"(0 = sin cortar) · 'sobrevivirían' simula un corte en {corte}\n")
    for p in perfiles():
        ph = holland.perfil(hoja(banco, p["riasec"], p["nombre"]), zona=ZONA)
        pts = _puntajes(ph)
        print(f"=== {p['nombre']} · código {ph['codigo']} · "
              + " ".join(f"{l}={s}" for l, s in pts.items()))
        top = holland_filtro.priorizar(cat, pts, top=corte)
        print("  top-5 del catálogo ordenado: "
              + "; ".join(dict.fromkeys(c.nombre for c in top))[:200])
        for etiqueta, claves in (("lo suyo", p["claves_suyas"]),
                                 ("lo de la casa", p["claves_casa"])):
            pos = _posiciones(cat, pts, claves)
            dentro = [x for x in pos if x[0] <= corte]
            print(f"  {etiqueta}: {len(dentro)} sobrevivirían un corte en {corte} · primeras "
                  f"{[(i, n[:34], a) for i, n, a in pos[:3]] or '— NINGUNA —'}")
        print()
    print("Si 'lo suyo' cae fuera del corte, el A/B mediría el filtro y no la "
          "hipótesis: por eso TOP_HOLLAND=0 (ordenar sin cortar).")


def correr(solo=None):
    cat = catalogo()
    banco = holland.preguntas()
    lista = [p for p in perfiles() if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    hechos = {s["perfil"] for s in salida}

    for perfil in lista:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']}")
        ph = holland.perfil(hoja(banco, perfil["riasec"], perfil["nombre"]), zona=ZONA)
        pts = _puntajes(ph)
        print("  Holland: " + " ".join(f"{l}={s}" for l, s in pts.items()))

        # La conversación de producción, una sola vez: los dos brazos comparten
        # respuestas para que la única variable sea el catálogo.
        os.environ["HOLLAND_EN_RECOMENDACION"] = "0"
        viejo, respuestas, log, _, tokens = _correr_brazo(
            perfil, cat, ph, con_fijas=True, sector=False)

        entrada = {**respuestas, "perfil_holland": bloque_texto(ph)}
        os.environ["HOLLAND_EN_RECOMENDACION"] = "1"
        nuevo, uso = recomendar.recomendar(entrada, cat, holland_puntajes=pts)
        os.environ["HOLLAND_EN_RECOMENDACION"] = "0"

        def resumen(res):
            t = res.carreras[0]
            return {
                "top": [c.model_dump() for c in res.carreras[:3]],
                "confianza": res.confianza, "confianza_nota": res.confianza_nota,
                "top1_area_suya": acierta(t.carrera, perfil["claves_suyas"]),
                "top1_area_casa": acierta(t.carrera, perfil["claves_casa"]),
            }

        for etiqueta, res in (("VIEJO", viejo), ("NUEVO", nuevo)):
            print(f"  {etiqueta} top1: {res.carreras[0].carrera} "
                  f"({res.carreras[0].afinidad}%) · confianza {res.confianza}%")

        salida.append({
            "perfil": perfil["nombre"],
            "riasec_real": perfil["riasec"],
            "holland": {"codigo": ph["codigo"], "areas": pts},
            "respuestas": respuestas,
            "log": log,
            "tokens": tokens + uso["total_tokens"],
            "ranking_suyo": _posiciones(cat, pts, perfil["claves_suyas"])[:5],
            "ranking_casa": _posiciones(cat, pts, perfil["claves_casa"])[:5],
            "viejo": resumen(viejo),
            "nuevo": resumen(nuevo),
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nResultados en {SALIDA}")
    print(recomendar.resumen_gasto())


def _self_check():
    cat = catalogo()
    assert len(holland_filtro.VECTORES) >= 80, "falta correr codificar_holland.py"
    # Cobertura: cuántos registros carrera-sede tienen vector. Un catálogo mal
    # codificado hace que priorizar sea un orden aleatorio con cara de ciencia.
    con = [c for c in cat if holland_filtro.vector_de(c)]
    assert len(con) == len(cat), f"{len(cat) - len(con)} registros sin vector RIASEC"

    artista = {"R": 12, "I": 10, "A": 39, "S": 38, "E": 10, "C": 19}  # Dulce
    contable = {"R": 9, "I": 16, "A": 3, "S": 9, "E": 29, "C": 36}    # Melany

    # El orden tiene que DISCRIMINAR: la carrera concreta de cada perfil, mejor
    # colocada con su propio vector que con el del otro perfil. Se comparan
    # carreras exactas y no listas de palabras clave: "administra" casa con
    # "Administración Educativa", que es docencia, y eso mide otra cosa.
    def puesto(nombre, pts):
        orden = [c.nombre for c in holland_filtro.priorizar(cat, pts, top=len(cat))]
        return orden.index(nombre) + 1

    diseno = "Licenciatura en Publicidad con Especialidad en Diseño Gráfico"
    conta = "Contaduría Pública y Auditoría"
    assert puesto(diseno, artista) < puesto(diseno, contable)
    assert puesto(conta, contable) < puesto(conta, artista)
    print(f"self-check OK — {len(cat)} registros con vector · "
          f"{diseno[:30]}… puesto {puesto(diseno, artista)} (vs "
          f"{puesto(diseno, contable)} con el otro perfil) · "
          f"{conta} puesto {puesto(conta, contable)} (vs {puesto(conta, artista)})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    ap.add_argument("--ranking", action="store_true", help="la puerta previa, sin Gemini")
    ap.add_argument("--perfil", help="corre un solo perfil por nombre")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.ranking:
        ranking()
    else:
        correr(a.perfil)
