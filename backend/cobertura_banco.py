# -*- coding: utf-8 -*-
"""¿Qué temas del catálogo NO tiene forma de nombrar el alumno?

La depuración anterior fue carrera por carrera, y eso sobrecuenta: cinco
Ingenierías en Sistemas con el mismo perfil son UN tema, no cinco. Acá el
clúster es el PERFIL: el catálogo ya agrupa por `perfil_id`, así que dos
carreras que comparten perfil comparten tema por construcción.

Para cada tema se pregunta:
  1. ¿Alguna opción del banco lo toca con una palabra específica (df <= 10)?
  2. Esa palabra, ¿significa lo mismo en los dos lados, o es un falso amigo?

No gasta cuota. Uso:  uv run python cobertura_banco.py
"""

import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.filtro import _PALABRA, STOPWORDS, _palabras  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ESPECIFICA = 10   # df <= 10: la palabra de verdad distingue

# Falsos amigos ya verificados leyendo el contexto en el perfil (ver
# experiments/filtro-catalogo-ab.md). Palabra -> qué significa en el catálogo.
#
# OJO: la tabla es POR PALABRA, no por tema, así que sobre-aplica. 'escritura'
# es falso amigo en el perfil del idioma maya ("la escritura del idioma") y
# legítima en el de Comunicación y Lenguaje ("difusión literaria"). Por eso
# "solo entra por falso amigo" es una señal para ir a leer el perfil, no un
# veredicto. Afinarla por tema costaría más que leer los pocos casos que salen.
FALSOS_AMIGOS = {
    "campo": "campo laboral, no el campo agrícola",
    "crear": "crear soluciones digitales, no crear arte",
    "estudio": "el estudio médico solicitado, no un estudio creativo",
    "aire": "la señal viaja por el aire, no trabajar al aire libre",
    "medio": "nivel medio (educativo), no medio ambiente",
    "práctica": "la práctica del idioma, no trabajo práctico con las manos",
    "trato": "trato con el paciente, no el estilo de trabajo",
    "salud": "la salud de una organización (contabilidad)",
    "historia": "la historia económica, no la materia de Historia",
    "realidad": "la realidad socioeconómica, no 'investigar la realidad'",
    "usar": "verbo suelto",
    "liderar": "verbo suelto",
    "centro": "centro educativo o de trabajo, sin carga temática",
    "funcionan": "verbo suelto",
    "ayudar": "verbo suelto",
    "escritura": "la escritura del idioma, no escritura creativa",
    "psicología": "psicología aplicada a la pedagogía",
    "comunicación": "comunicación terapéutica / telecomunicación / oratoria",
    "estudios": "verbo suelto",
}

FIJAS_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "frontend", "src", "preguntas-fijas.js")


def banco():
    """Lee el banco de opciones del propio Chat, no de una copia.

    Tener la lista duplicada acá garantizaba que se desincronizara con
    `preguntas-fijas.js` a la primera edición, y entonces el análisis mentiría
    justo cuando alguien lo corre para decidir un cambio.

    ponytail: regex sobre el JS, no un parser. Las opciones son literales de una
    línea (`{ label: '...' }`); si algún día se generan con código, esto se cae
    ruidosamente en el self-check en vez de mentir en silencio.
    """
    import re
    js = open(FIJAS_JS, encoding="utf-8").read()
    out = {}
    for clave in ("impacto", "estilo", "entorno", "gustos"):
        i = js.index(f"clave: '{clave}'")
        bloque = js[i:js.index("],", i)]
        out[clave] = re.findall(r"label: '([^']+)'", bloque)
        assert out[clave], f"no se pudieron leer las opciones de '{clave}' del JS"
    return out


BANCO = banco()
OPCIONES = [(g, o) for g, v in BANCO.items() for o in v]


def cargar():
    """Devuelve {clave_de_perfil: {'perfil':..., 'carreras': [...], 'deptos': set}}."""
    comp = json.load(open(os.path.join(DATA, "perfiles_compartidos.json"), encoding="utf-8"))
    temas = {}
    for f in glob.glob(os.path.join(DATA, "carreras_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for c in d["carreras"]:
            pid = c.get("perfil_id")
            perfil = comp[pid] if pid else c["perfil"]
            if isinstance(perfil, dict):
                perfil = perfil.get("perfil", "")
            # Sin perfil_id, el propio texto agrupa: dos carreras con el mismo
            # perfil literal son el mismo tema aunque no lo declaren.
            clave = pid or ("txt:" + perfil[:80])
            t = temas.setdefault(clave, {"perfil": perfil, "carreras": set(), "deptos": set()})
            t["carreras"].add(c["nombre"])
            t["deptos"].add(d["departamento"])
    return temas


def main():
    temas = cargar()
    bolsas = {k: {w for w in _PALABRA.findall(t["perfil"].lower())
                  if w not in STOPWORDS and len(w) > 2}
              for k, t in temas.items()}
    df = Counter()
    for b in bolsas.values():
        for w in b:
            df[w] += 1
    n = len(temas)

    filas = []
    for k, t in temas.items():
        b = bolsas[k]
        legit, falsos = set(), set()
        for _, o in OPCIONES:
            for w in _palabras(o):
                if len(w) > 2 and w in b and df[w] <= ESPECIFICA:
                    (falsos if w in FALSOS_AMIGOS else legit).add(w)
        propias = sorted([w for w in b if df[w] <= 3], key=lambda w: (df[w], w))[:10]
        filas.append({
            "clave": k, "carreras": sorted(t["carreras"]), "deptos": sorted(t["deptos"]),
            "legit": sorted(legit), "falsos": sorted(falsos), "propias": propias,
        })

    sin = [f for f in filas if not f["legit"]]
    solo_falso = [f for f in sin if f["falsos"]]
    nada = [f for f in sin if not f["falsos"]]
    filas.sort(key=lambda f: (len(f["legit"]), -len(f["carreras"])))

    print(f"Temas del catálogo (agrupados por perfil): {n}")
    print(f"Carreras que cubren: {sum(len(f['carreras']) for f in filas)}")
    print(f"Temas SIN ninguna palabra legítima del banco: {len(sin)}  "
          f"({len(nada)} sin nada, {len(solo_falso)} solo por falso amigo)\n")

    print("=" * 78)
    print("TEMAS QUE EL ALUMNO NO TIENE FORMA DE NOMBRAR")
    print("=" * 78)
    for f in sin:
        print(f"\n[{len(f['carreras'])} carrera(s)] {', '.join(f['carreras'])[:150]}")
        print(f"   lo distingue : {', '.join(f['propias'][:8])}")
        if f["falsos"]:
            print(f"   solo entra por falso amigo: "
                  + "; ".join(f"'{w}' ({FALSOS_AMIGOS[w]})" for w in f["falsos"]))
        else:
            print("   no la toca NINGUNA opción del banco")

    print("\n" + "=" * 78)
    print("TEMAS QUE SÍ ESTÁN CUBIERTOS (para no romperlos al redactar chips)")
    print("=" * 78)
    for f in filas:
        if f["legit"]:
            print(f"  {', '.join(f['legit']):32s} <- {', '.join(f['carreras'])[:90]}")


if __name__ == "__main__":
    main()
