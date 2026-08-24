"""Costo por alumno segun el departamento que elige, con el caché de hoy.

No genera nada: `count_tokens` es gratis, y los hashes de caché se calculan
localmente. Se puede correr las veces que haga falta sin gastar cuota.

El caché se indexa por `sha256(system + catálogo)` y el catálogo viene filtrado
por departamento, asi que cada departamento tiene su propio juego de cachés.
Dentro de un departamento hay dos: el de `next-question` (catálogo recortado por
filtro.preseleccionar) y el de `recommend` (catálogo completo). Como
`preseleccionar` se recalcula tras cada respuesta, el del chat cambia en cada
llamada, salvo donde el catálogo es mas chico que TOP_DEFAULT y no hay nada que
recortar (Totonicapán).

Imprime dos columnas de costo a proposito:

- **solo tokens**: lo que ve `uso_tokens`, y lo que coincide con las sesiones
  reales de Neon.
- **con alquiler**: sumando $1/1M tokens/hora por cada caché distinto. Esta es
  la columna CORRECTA: la factura del 2026-08-24 confirmo el SKU
  `cached content storage token hours` a $1.004/1M tokens-hora, o sea el 38% del
  gasto total. Ver experiments/cache-compartido.md §8.

    uv run python costo_por_departamento.py
"""
import hashlib
import os

from dotenv import load_dotenv
from google import genai

from app import preguntas, recomendar  # noqa: F401  (preguntas fija el SYSTEM del chat)
from app.db import SessionLocal
from app.filtro import preseleccionar
from app.models import Carrera

load_dotenv()

P_CACHE, P_OUT, P_RENTA = 0.025, 1.50, 1.00  # $/1M tokens; renta por hora
SALIDA_POR_SESION = 2900  # medido, ver decisions/gemini-costos-y-caching.md
LLAMADAS_CHAT = 4         # MIN_ADAPTATIVAS
DEPTOS = ("Quetzaltenango", "Totonicapán", "Ambos")

# Dos perfiles DISTINTOS: el segundo sirve para ver si su recorte colisiona con
# el del primero (o sea, si un alumno reusa el caché que dejo otro).
BASE = {"impacto": "Ayudar, enseñar o cuidar a las personas",
        "estilo": "Con personas, en trato directo",
        "entorno": "En un hospital, clínica o consultorio",
        "gustos": "Salud y cuidar personas, Tecnología y computación"}
OTRO = dict(BASE, impacto="Liderar, organizar negocios o usar tecnología y números",
            gustos="Matemáticas y números, Tecnología y computación")
ADAPT = ["Prefiero el trato directo con la gente",
         "Me gusta la investigacion y los datos",
         "Quiero algo practico y con las manos"]


def _hashes_y_tokens(perfil, depto, cat, contar):
    """Recorre las llamadas de chat de un alumno. Devuelve (hashes, tokens)."""
    r = dict(perfil, departamento=depto)
    hashes, toks = [], []
    for i in range(LLAMADAS_CHAT):
        txt = recomendar._catalogo_texto(preseleccionar(r, cat))
        hashes.append(hashlib.sha256(txt.encode()).hexdigest())
        toks.append(contar(txt))
        if i < len(ADAPT):
            r[f"adaptativa_{i}"] = ADAPT[i]
    return hashes, toks


def main():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def contar(texto):
        return client.models.count_tokens(
            model=recomendar.MODELO, contents=texto).total_tokens

    db = SessionLocal()
    filas = []
    print(f"{'Depto':16} {'carreras':>8} {'chat/llam':>10} {'recommend':>10} "
          f"{'caches 1o':>10} {'caches 2o':>10}")
    for depto in DEPTOS:
        q = db.query(Carrera)
        if depto != "Ambos":
            q = q.filter(Carrera.departamento == depto)
        cat = q.all()

        h1, toks = _hashes_y_tokens(BASE, depto, cat, contar)
        h2, _ = _hashes_y_tokens(OTRO, depto, cat, lambda _t: 0)
        tok_rec = contar(recomendar._catalogo_texto(cat))

        caches_1 = len(set(h1)) + 1            # + el de recommend
        caches_2 = len(set(h2) - set(h1))      # lo que AGREGA el segundo alumno
        filas.append((depto, len(cat), toks, tok_rec, set(h1), caches_2))
        print(f"{depto:16} {len(cat):>8} {sum(toks)//len(toks):>10,} {tok_rec:>10,} "
              f"{caches_1:>10} {caches_2:>10}")
    db.close()

    print(f"\n{'=' * 78}\nCosto por alumno ({LLAMADAS_CHAT} llamadas de chat + 1 recomendacion)\n")
    print(f"{'Depto':16} {'prompt':>9} {'solo tokens':>12} "
          f"{'+renta 1o':>11} {'+renta 2o':>11}")
    for depto, _n, toks, tok_rec, h1, caches_2 in filas:
        prompt = sum(toks) + tok_rec
        solo_tokens = (prompt * P_CACHE + SALIDA_POR_SESION * P_OUT) / 1e6
        tok_prom = sum(toks) / len(toks)
        renta_1 = (len(h1) * tok_prom + tok_rec) * P_RENTA / 1e6
        renta_2 = (caches_2 * tok_prom) * P_RENTA / 1e6  # recommend ya esta rentado
        print(f"{depto:16} {prompt:>9,} ${solo_tokens:>11.4f} "
              f"${solo_tokens + renta_1:>10.4f} ${solo_tokens + renta_2:>10.4f}")

    print("\nLa columna con renta es la CORRECTA: la factura del 2026-08-24 confirmo")
    print("el SKU de almacenamiento a $1.004/1M tokens-hora, el 38% del gasto total.")
    print("'solo tokens' es lo que reporta uso_tokens, o sea una cota inferior.")


if __name__ == "__main__":
    main()
