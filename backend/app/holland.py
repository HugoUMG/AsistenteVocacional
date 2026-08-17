"""Test de intereses de Holland (RIASEC) vía O*NET Web Services.

Es el Interest Profiler oficial del Departamento de Trabajo de EE. UU., en su
versión en español ("Mi Próximo Paso"). NO se reimplementa el instrumento aquí:
los 60 ítems, la escala y el puntaje RIASEC los sirve y calcula la API oficial;
este módulo es un proxy con credenciales de desarrollador.

Por qué proxy y no llamarla desde el navegador: la API key no puede viajar al
frontend (quedaría a la vista en devtools) y el servicio no manda CORS.

Credenciales: registro gratuito en https://services.onetcenter.org/ → una API key
por proyecto, que va en ONET_API_KEY (backend/.env). O*NET ya no usa usuario y
contraseña: la key viaja en el header X-API-Key y no se acepta en la query string.

Self-check: uv run python -m app.holland  (hace llamadas reales si hay credenciales)
"""

import functools
import os

import httpx

# API v2.0. El host es OTRO que el del sitio de documentación (services.onetcenter.org),
# que sigue sirviendo la v1.9 con usuario/contraseña y rechaza la API key con 401.
BASE = "https://api-v2.onetcenter.org/mpp/interestprofiler"
N_PREGUNTAS = 60
# La letra sale del `code` en inglés (realistic, investigative, ...), no del
# título, que en el endpoint en español llega traducido ("Realistas", ...).
# Las seis iniciales son distintas, así que basta la primera letra.
# Orden canónico del código Holland, para desempatar perfiles planos.
ORDEN_RIASEC = "RIASEC"
# Cuántas ocupaciones se le muestran al alumno. Sin recorte, un perfil plano
# devuelve cientos en orden alfabético, que no orientan a nadie.
TOPE_CARRERAS = 30


class SinCredenciales(RuntimeError):
    pass


def _cliente() -> httpx.Client:
    key = os.getenv("ONET_API_KEY")
    if not key:
        raise SinCredenciales(
            "Falta ONET_API_KEY en backend/.env. Se pide gratis en "
            "https://services.onetcenter.org/developer/signup"
        )
    return httpx.Client(
        base_url=BASE,
        headers={
            "X-API-Key": key,
            "Accept": "application/json",
            # O*NET pide identificar la aplicación en el User-Agent.
            "User-Agent": "AsistenteVocacional/1.0",
        },
        timeout=20,
    )


def _json(r: httpx.Response) -> dict:
    r.raise_for_status()
    return r.json()


@functools.cache
def preguntas() -> dict:
    """Los 60 ítems en español y la escala de 5 puntos, tal cual los da O*NET.

    Cacheado en memoria: el banco se revisó por última vez en 2018, no cambia
    entre peticiones. Reiniciar el backend lo vuelve a pedir.
    """
    with _cliente() as c:
        # Sin start/end el servicio devuelve solo las primeras 20.
        datos = _json(c.get("/questions", params={"start": 1, "end": N_PREGUNTAS}))
    items = datos["question"]
    if len(items) != N_PREGUNTAS:
        raise RuntimeError(f"O*NET devolvió {len(items)} preguntas, se esperaban {N_PREGUNTAS}")
    return {"preguntas": items, "opciones": datos["answer_option"], "total": len(items)}


def perfil(respuestas: str, zona: int | None = None) -> dict:
    """Puntajes RIASEC + carreras afines para una cadena de 60 dígitos 1-5.

    `zona` (1-5) es el Job Zone: filtra por nivel de preparación que pide la
    ocupación; 4 ≈ carrera universitaria. En la v2 el parámetro se llama `zone`
    (en la v1.9 era `job_zone`, y mandarlo con el nombre viejo NO da error: la
    API lo ignora en silencio y devuelve todas las ocupaciones).
    """
    params = {"answers": respuestas}
    with _cliente() as c:
        areas = _json(c.get("/results", params=params))["result"]
        crudas = _json(
            c.get(
                "/careers",
                # Por defecto pagina de 20 en 20; se pide un lote grande y se
                # recorta acá al mejor nivel de ajuste.
                params={**params, "start": 1, "end": 100,
                        **({"zone": zona} if zona else {})},
            )
        )

    for area in areas:
        area["letra"] = area["code"][0].upper()
    codigo = "".join(
        a["letra"]
        # Empate = orden canónico RIASEC, para que el código no dependa de en qué
        # orden vino la lista.
        for a in sorted(areas, key=lambda a: (-a["score"], ORDEN_RIASEC.index(a["letra"])))[:3]
    )

    # O*NET etiqueta cada ocupación como Best/Great/Good. Se recorre de mejor a
    # peor y se corta apenas hay una lista razonable: "Best" a veces trae solo dos
    # ocupaciones, y un perfil plano manda cientos de "Good" en orden alfabético
    # que no orientan a nadie.
    todas = crudas.get("career", [])
    carreras = []
    for nivel in ("Best", "Great", "Good"):
        if len(carreras) >= 10:
            break
        carreras += [c for c in todas if c.get("fit") == nivel]

    return {
        "areas": areas,
        "codigo": codigo,
        "carreras": carreras[:TOPE_CARRERAS],
        "carreras_total": crudas.get("total", len(carreras)),
    }


def valida(respuestas: str) -> bool:
    """Frontera de confianza: 60 caracteres, cada uno un dígito del 1 al 5."""
    return len(respuestas) == N_PREGUNTAS and all(c in "12345" for c in respuestas)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()  # corriendo suelto nadie cargó el .env todavía

    assert valida("3" * 60)
    assert not valida("3" * 59)
    assert not valida("6" + "3" * 59)
    assert not valida("3" * 30 + "0" + "3" * 29)
    print("validación OK")

    try:
        banco = preguntas()
    except SinCredenciales as e:
        raise SystemExit(f"(sin llamada real) {e}")
    print(f"{banco['total']} preguntas, ej.: {banco['preguntas'][0]['text']}")
    print(f"escala: {[o['name'] for o in banco['opciones']]}")

    p = perfil("553421321134342523523523254115342111351145453111231155343444", zona=4)
    print(f"código {p['codigo']} · " + " ".join(f"{a['letra']}={a['score']}" for a in p["areas"]))
    print(
        f"{len(p['carreras'])} carreras mostradas de {p['carreras_total']}, "
        f"ej.: {p['carreras'][0]['title']} ({p['carreras'][0]['fit']})"
    )

    # Perfil plano: el código no puede salir del orden en que vengan las áreas.
    plano = perfil("".join(str((i * 7) % 5 + 1) for i in range(1, 61)))
    assert plano["codigo"] == "RIA", plano["codigo"]
    print(f"perfil plano -> {plano['codigo']}, {len(plano['carreras'])} carreras")
