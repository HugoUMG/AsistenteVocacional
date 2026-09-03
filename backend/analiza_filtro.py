"""Junta las dos rondas del A/B del filtro y reporta lo que cada medida aguanta.

Se separa del experimento a propósito: correrlo no gasta cuota, así que se puede
reanalizar cuantas veces haga falta sin volver a llamar a Gemini.
"""

import json
import os
import statistics

DATA = os.path.join(os.path.dirname(__file__), "data", "tests")
RONDAS = [("R1", "experimento_filtro_ronda1.json"),
          ("R2", "experimento_filtro_resultados.json")]


def cargar():
    out = []
    for etiqueta, archivo in RONDAS:
        ruta = os.path.join(DATA, archivo)
        if not os.path.exists(ruta):
            continue
        for s in json.load(open(ruta, encoding="utf-8"))["sesiones"]:
            out.append({**s, "ronda": etiqueta})
    return out


def p(valores, q):
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else 0.0


def main():
    ses = cargar()
    idx = {(s["ronda"], s["perfil"], s["brazo"]): s for s in ses}
    perfiles = sorted({s["perfil"] for s in ses}, key=lambda n: [s["perfil"] for s in ses].index(n))
    rondas = sorted({s["ronda"] for s in ses})

    print("=" * 78)
    print("A/B DEL PRE-FILTRO — LAS DOS RONDAS JUNTAS")
    print("=" * 78)

    print("\n1) ACIERTO DEL TOP-1, RONDA POR RONDA")
    print(f"{'perfil':10s} " + "".join(f"{r + ':A':>6s}{r + ':B':>6s}" for r in rondas)
          + "   estabilidad de A")
    tot = {}
    for n in perfiles:
        fila = f"{n:10s} "
        marcas = []
        for r in rondas:
            for b in ("A", "B"):
                s = idx.get((r, n, b))
                ok = s and s["acierta"]
                fila += f"{('si' if ok else 'NO'):>6s}"
                tot[b] = tot.get(b, 0) + (1 if ok else 0)
                if b == "A":
                    marcas.append(ok)
        estable = "estable" if len(set(marcas)) == 1 else "<< CAMBIA solo"
        print(fila + f"   {estable}")
    npar = len(perfiles) * len(rondas)
    print(f"\n   TOTAL   A {tot.get('A', 0)}/{npar}   B {tot.get('B', 0)}/{npar}")

    inestables = sum(1 for n in perfiles
                     if len({idx[(r, n, 'A')]["acierta"] for r in rondas
                             if (r, n, 'A') in idx}) > 1)
    print(f"   Perfiles donde el MISMO brazo A cambia de resultado entre rondas: "
          f"{inestables}/{len(perfiles)}")
    print("   Ese número es el piso de ruido: ninguna diferencia entre brazos menor")
    print("   que eso se puede interpretar.")

    print("\n2) ¿LA CARRERA OBJETIVO SOBREVIVIÓ EL RECORTE? (brazo A, gratis)")
    print(f"{'perfil':10s} {'objetivo':46s} {'en las 35':>10s}  top-1 de A")
    for n in perfiles:
        for r in rondas:
            s = idx.get((r, n, "A"))
            if not s:
                continue
            d = s["objetivo_en_candidatas"]
            print(f"{n if r == rondas[0] else '':10s} "
                  f"{(s['objetivo'][:44] if r == rondas[0] else ''):46s} "
                  f"{sum(d)}/{len(d):<8} {s['top1'][:34]}")
    print("\n   Lectura: hay perfiles cuya carrera correcta NUNCA entra a las 35 y aun")
    print("   así sale de top-1. Es la confirmación de que el filtro no decide el")
    print("   resultado final: recommend() ve el catálogo completo.")

    print("\n3) LATENCIA (la medida con muestra suficiente)")
    for tipo in (None, "next-question", "recommend"):
        etiq = tipo or "todas"
        print(f"\n   {etiq}")
        print(f"   {'brazo':6s} {'n':>4s} {'mediana':>8s} {'p90':>7s} {'p95':>7s} {'max':>7s}")
        for b in ("A", "B"):
            v = [ll["segundos"] for s in ses if s["brazo"] == b
                 for ll in s["llamadas"] if not tipo or ll["tipo"] == tipo]
            if v:
                print(f"   {b:6s} {len(v):>4d} {statistics.median(v):>8.2f} "
                      f"{p(v, 0.90):>7.2f} {p(v, 0.95):>7.2f} {max(v):>7.2f}")

    print("\n4) SEGUNDOS DE ESPERA POR SESIÓN COMPLETA")
    for b in ("A", "B"):
        v = [sum(ll["segundos"] for ll in s["llamadas"]) for s in ses if s["brazo"] == b]
        print(f"   {b}: mediana {statistics.median(v):5.1f}s   "
              f"peor sesión {max(v):5.1f}s   (n={len(v)})")

    print("\n5) TOKENS Y COSTO")
    print(f"   {'brazo':6s} {'prompt':>12s} {'cacheado':>12s} {'%':>6s} {'salida':>8s} "
          f"{'USD/sesión':>11s}")
    for b in ("A", "B"):
        lg = [s for s in ses if s["brazo"] == b]
        pr = sum(ll["prompt_tokens"] for s in lg for ll in s["llamadas"])
        ca = sum(ll["cached_tokens"] for s in lg for ll in s["llamadas"])
        ou = sum(ll["output_tokens"] for s in lg for ll in s["llamadas"])
        costo = ((pr - ca) * 0.25 + ca * 0.025 + ou * 1.50) / 1e6
        print(f"   {b:6s} {pr:>12,d} {ca:>12,d} {100 * ca / pr:>5.1f}% {ou:>8,d} "
              f"{costo / len(lg):>11.4f}")

    print("\n6) CUÁNTAS PREGUNTAS ADAPTATIVAS HIZO CADA BRAZO")
    for b in ("A", "B"):
        v = [len([a for a in s["adaptativas"] if not a.get("terminado")])
             for s in ses if s["brazo"] == b]
        print(f"   {b}: mediana {statistics.median(v):.1f}   "
              f"(min {min(v)}, max {max(v)})")


if __name__ == "__main__":
    main()
