"""Experimento: ¿el pre-filtro rompe el caching explícito de Gemini?

El caché de `recomendar.py` se indexa por `sha256(system + catálogo)`. El
catálogo que ve `next-question` sale de `filtro.preseleccionar`, que puntúa
contra TODAS las respuestas acumuladas: cada respuesta nueva reordena el top-35,
el texto cambia y el hash cambia. Medido sin gastar API (Quetzaltenango, 185
carreras): 5 llamadas de una sesión producen 5 hashes distintos, o sea 5
CachedContent en vez de uno reusado.

Con caching explícito no existe "la primera llamada cara": `caches.create` no
cobra los tokens de entrada, cada request paga los suyos a tarifa reducida
($0.025 vs $0.25 por 1M) y por encima se paga ALQUILER, $1 por 1M tokens/hora
con TTL de 1h. Entonces un hash que no se repite es una renta que no se
amortiza, y hay una renta por alumno.

## Brazos

Los dos corren la fase de chat con los MISMOS tres perfiles.

- **A (control)** — producción de hoy: `next-question` ve el top-35 del filtro,
  recalculado tras cada respuesta.
- **B** — `next-question` ve el catálogo completo del departamento, idéntico en
  todas las llamadas y entre todos los alumnos.

## Qué se mide

Solo economía del caché. La CALIDAD de esta misma comparación ya está medida en
experiments/filtro-catalogo-ab.md (13/16 vs 12/16, empate dentro del ruido), así
que aquí no se vuelve a juzgar el ranking.

1. Cachés distintos creados por brazo (cuántas rentas de 1h se pagan).
2. % de prompt cacheado.
3. Costo de tokens, y alquiler estimado aparte, que `uso_tokens` NO registra.

## Por qué respuestas enlatadas

experimento_filtro.py usa un alumno simulado por Gemini, que duplica el gasto.
El caché depende del CATÁLOGO, no de qué tan realista sea la respuesta del
alumno, así que aquí se contesta con la primera opción que ofrece el modelo.

    uv run python experimento_cache_compartido.py [llamadas_por_perfil]
"""
import sys

from app.db import SessionLocal
from app.models import Carrera
from app import preguntas, recomendar

DEPARTAMENTO = "Quetzaltenango"
LLAMADAS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
PRECIO_ALQUILER_POR_1M_HORA = 1.00  # $/1M tokens/hora, TTL de _get_cache = 1h

PERFILES = [
    {"nombre": "Ana",
     "impacto": "Ayudar, enseñar o cuidar a las personas",
     "estilo": "Con personas, en trato directo",
     "entorno": "En un hospital, clínica o consultorio",
     "gustos": "Salud y cuidar personas, Psicología y comportamiento"},
    {"nombre": "Diego",
     "impacto": "Liderar, organizar negocios o usar tecnología y números",
     "estilo": "Analizando datos, ideas y lógica",
     "entorno": "En una oficina o empresa",
     "gustos": "Matemáticas y números, Tecnología y computación"},
    {"nombre": "Karla",
     "impacto": "Comunicar, crear, diseñar o investigar la realidad",
     "estilo": "De forma práctica, con las manos",
     "entorno": "En medios, un estudio creativo o diseñando",
     "gustos": "Arte, diseño y creatividad, Comunicación, escritura y medios"},
]


def _sin_filtro(respuestas, carreras, top=None):
    """Brazo B: no recorta nada.

    ponytail: monkeypatch en el experimento, no un flag en producción. Si el A/B
    sale a favor, el cambio real es BORRAR la llamada a preseleccionar en
    preguntas.siguiente_pregunta, no agregar una bifurcación que mantener.
    """
    return carreras


def _brazo(nombre_brazo, con_filtro, cat):
    """Corre los tres perfiles y devuelve el acumulado de tokens del brazo."""
    recomendar._caches.clear()  # cada brazo cuenta sus propios caches
    total = dict.fromkeys(("llamadas", "prompt_tokens", "output_tokens", "cached_tokens"), 0)

    original = preguntas.preseleccionar
    if not con_filtro:
        preguntas.preseleccionar = _sin_filtro
    try:
        for perfil in PERFILES:
            respuestas = {"departamento": DEPARTAMENTO, **perfil}
            sid = f"cache-{nombre_brazo}-{perfil['nombre']}"
            preguntas._COBERTURA_POR_SESION.pop(sid, None)
            for _ in range(LLAMADAS):
                paso, uso = preguntas.siguiente_pregunta(respuestas, cat, sid)
                total["llamadas"] += 1
                for k in ("prompt_tokens", "output_tokens", "cached_tokens"):
                    total[k] += uso[k]
                pct = 100.0 * uso["cached_tokens"] / max(uso["prompt_tokens"], 1)
                print(f"    [{nombre_brazo}] {perfil['nombre']:6} "
                      f"{uso['prompt_tokens']:>7,} prompt  {pct:5.1f}% cache")
                if paso.terminado:
                    break
                # Enlatado: siempre la primera opcion que ofrece el modelo.
                respuestas[paso.pregunta_texto] = paso.opciones[0].label
    finally:
        preguntas.preseleccionar = original

    total["caches"] = sum(1 for v in recomendar._caches.values() if v is not None)
    total["nombres_cache"] = [v for v in recomendar._caches.values() if v is not None]
    return total


def _reporta(nombre_brazo, t):
    pct = 100.0 * t["cached_tokens"] / max(t["prompt_tokens"], 1)
    tokens_usd = recomendar.costo_usd(t)
    # Alquiler: cada cache distinto renta su contenido 1h. Aproximamos su tamaño
    # con el promedio de tokens cacheados por llamada.
    tok_por_cache = t["cached_tokens"] / max(t["llamadas"], 1)
    alquiler = t["caches"] * tok_por_cache * PRECIO_ALQUILER_POR_1M_HORA / 1e6
    print(f"\n  BRAZO {nombre_brazo}")
    print(f"    llamadas            {t['llamadas']:>10,}")
    print(f"    prompt              {t['prompt_tokens']:>10,}")
    print(f"    cacheado            {t['cached_tokens']:>10,}  ({pct:.1f}%)")
    print(f"    salida              {t['output_tokens']:>10,}")
    print(f"    CACHES distintos    {t['caches']:>10}")
    print(f"    costo tokens        ${tokens_usd:>9.4f}")
    print(f"    alquiler estimado   ${alquiler:>9.4f}   (no cae en uso_tokens)")
    print(f"    TOTAL               ${tokens_usd + alquiler:>9.4f}")
    return tokens_usd + alquiler


def main():
    db = SessionLocal()
    cat = db.query(Carrera).filter(Carrera.departamento == DEPARTAMENTO).all()
    db.close()
    print(f"Catalogo: {len(cat)} carreras en {DEPARTAMENTO} | "
          f"{len(PERFILES)} perfiles x {LLAMADAS} llamadas por brazo\n")

    print("  --- A: con pre-filtro (produccion de hoy) ---")
    a = _brazo("A", True, cat)
    print("\n  --- B: catalogo completo compartido ---")
    b = _brazo("B", False, cat)

    total_a = _reporta("A", a)
    total_b = _reporta("B", b)

    print("\n" + "=" * 62)
    if total_a > 0:
        print(f"B cuesta {100 * total_b / total_a:.0f}% de lo que cuesta A "
              f"(ahorro {100 * (1 - total_b / total_a):+.0f}%)")
    print(f"Caches: A={a['caches']}  B={b['caches']}")
    print("\nOJO: el alquiler es ESTIMADO con el precio de lista. El unico numero")
    print("real es la factura de Google. uso_tokens no registra almacenamiento.")
    print(recomendar.resumen_gasto())

    # Borrar los caches creados: dejan de rentar y no ensucian corridas futuras.
    import os
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    borrados = 0
    for name in set(a["nombres_cache"] + b["nombres_cache"]):
        try:
            client.caches.delete(name=name)
            borrados += 1
        except Exception as e:
            print(f"  no se pudo borrar {name}: {type(e).__name__}")
    print(f"Caches borrados: {borrados}")


if __name__ == "__main__":
    main()
