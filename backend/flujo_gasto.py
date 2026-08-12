"""Corre N conversaciones completas contra el backend local y reporta el gasto
real (tokens y $) leyendo /api/uso-tokens, comparando con-caché vs sin-caché.

Uso: python flujo_gasto.py [N] [departamento] [paralelas]
"""
import json, random, sys, time, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

API = "http://localhost:8000"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 25
DEPTO = sys.argv[2] if len(sys.argv) > 2 else "Quetzaltenango"
PARALELAS = int(sys.argv[3]) if len(sys.argv) > 3 else 4

# Precios gemini-3.1-flash-lite ($/1M tokens), ver decisions/gemini-costos-y-caching.md
P_IN, P_OUT = 0.25, 1.50
P_CACHE = P_IN * 0.10

IMPACTO = ["Ayudar, enseñar o cuidar a las personas", "Defender la justicia y resolver conflictos",
           "Liderar, organizar negocios o usar tecnología y números",
           "Trabajar con la naturaleza, el campo o el ambiente",
           "Comunicar, crear, diseñar o investigar la realidad",
           "Construir, diseñar o hacer que las cosas funcionen"]
ESTILO = ["Con personas, en trato directo", "Analizando datos, ideas y lógica",
          "De forma práctica, con las manos", "Al aire libre y en movimiento"]
ENTORNO = ["En una oficina o empresa", "En un hospital, clínica o consultorio",
           "Al aire libre, en el campo o la naturaleza", "En un laboratorio o taller técnico",
           "En un aula o centro educativo", "En una obra, con máquinas o herramientas",
           "En medios, un estudio creativo o diseñando", "Con la comunidad, ayudando a personas"]
GUSTOS = ["Matemáticas y números", "Tecnología y computación", "Salud y cuidar personas",
          "Biología y naturaleza", "Química y laboratorio", "Leyes, justicia y debate",
          "Negocios, dinero y emprender", "Arte, diseño y creatividad",
          "Comunicación, escritura y medios", "Enseñar y educar", "Psicología y comportamiento"]
NOMBRES = ["Ana", "Luis", "Sofia", "Diego", "Maria", "Carlos", "Lucia", "Jose", "Karla", "Pablo"]


def elige(lista, rng, k=2):
    return ", ".join(rng.sample(lista, min(k, len(lista))))


def una_sesion(i: int) -> tuple[str, int, str | None]:
    """Devuelve (session_id, llamadas_gemini, error)."""
    rng = random.Random(i)
    sid = str(uuid.uuid4())
    with httpx.Client(base_url=API, timeout=180) as c:
        nombre = f"{rng.choice(NOMBRES)} Prueba"
        est = c.post("/api/register", json={"nombre": nombre})
        est.raise_for_status()
        eid = est.json()["id"]

        respuestas = {
            "departamento": DEPTO,
            "nombre": nombre,
            "impacto": elige(IMPACTO, rng, 2),
            "estilo": elige(ESTILO, rng, 2),
            "entorno": elige(ENTORNO, rng, 2),
            "gustos": elige(GUSTOS, rng, 3),
        }
        llamadas = 0
        for _ in range(8):  # MAX_ADAPTATIVAS
            r = c.post("/api/next-question",
                       json={"estudiante_id": eid, "respuestas": respuestas, "session_id": sid})
            r.raise_for_status()
            paso = r.json()
            llamadas += 1
            if paso["terminado"]:
                break
            ops = [o["label"] for o in paso["opciones"]] or ["Sí"]
            respuestas[paso["pregunta_texto"]] = rng.choice(ops)

        c.post("/api/submit-survey",
               json={"estudiante_id": eid, "respuestas": respuestas, "session_id": sid})
        rec = c.post("/api/recommend",
                     json={"estudiante_id": eid, "respuestas": respuestas, "session_id": sid})
        rec.raise_for_status()
        llamadas += 1
    return sid, llamadas, None


def costo(prompt, cached, output):
    """($ con caché, $ si nada hubiera cacheado)."""
    con = ((prompt - cached) * P_IN + cached * P_CACHE + output * P_OUT) / 1e6
    sin = (prompt * P_IN + output * P_OUT) / 1e6
    return con, sin


def main():
    mios, t0 = [], time.time()
    # En paralelo: secuencial tardaría ~2.5 min por sesión. Se parece más a un
    # salón real que a un usuario solo.
    with ThreadPoolExecutor(max_workers=PARALELAS) as pool:
        futs = {pool.submit(una_sesion, i): i for i in range(N)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                sid, llamadas, _ = f.result()
                mios.append(sid)
                print(f"[{len(mios)}/{N}] sesion {i} ok — {llamadas} llamadas ({time.time()-t0:.0f}s)", flush=True)
            except Exception as e:
                print(f"[sesion {i}] FALLO: {type(e).__name__} {str(e)[:200]}", flush=True)

    r = httpx.get(f"{API}/api/uso-tokens", timeout=60).json()
    ses = {s["session_id"]: s for s in r["sesiones"]}
    filas = [ses[s] for s in mios if s in ses]
    tot = {k: sum(f[k] for f in filas) for k in
           ("llamadas", "prompt_tokens", "output_tokens", "total_tokens", "cached_tokens")}
    n = len(filas)
    con, sin = costo(tot["prompt_tokens"], tot["cached_tokens"], tot["output_tokens"])
    pct = tot["cached_tokens"] / tot["prompt_tokens"] * 100 if tot["prompt_tokens"] else 0

    print("\n" + "=" * 62)
    print(f"{n} conversaciones · departamento: {DEPTO} · {tot['llamadas']} llamadas a Gemini")
    print(f"  prompt      {tot['prompt_tokens']:>10,}")
    print(f"  cacheados   {tot['cached_tokens']:>10,}  ({pct:.1f}% del prompt)")
    print(f"  salida      {tot['output_tokens']:>10,}")
    print(f"  total       {tot['total_tokens']:>10,}   ({tot['total_tokens']/n:,.0f} por sesión)")
    # ponytail: no distingue qué key atendió cada llamada (uso_tokens no lo guarda).
    # Si la primaria es gratis, el gasto REAL es $0 salvo lo que cayó al respaldo:
    # este número es "lo que costaría si todo fuera de pago". Cotejar con el
    # crédito de la consola de Google, que tarda horas en actualizarse.
    print(f"  costo si TODO es key de pago  ${con:.4f}   (${con/n:.4f}/sesión)")
    print(f"  costo si no cacheara  ${sin:.4f}   (ahorro {(1-con/sin)*100:.1f}%)")
    for esc in (100, 200):
        c2, s2 = costo(tot["prompt_tokens"]/n*esc, tot["cached_tokens"]/n*esc, tot["output_tokens"]/n*esc)
        print(f"  proyección {esc} sesiones: ${c2:.2f} con caché · ${s2:.2f} sin caché")
    print("=" * 62)
    json.dump({"sesiones": filas, "totales": tot}, open("gasto25.json", "w"), indent=2)


if __name__ == "__main__":
    main()
