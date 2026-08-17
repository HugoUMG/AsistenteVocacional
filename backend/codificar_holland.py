"""Codifica el catálogo de carreras con el perfil RIASEC que O*NET publica.

## Qué hace y por qué

El bloque de texto con el resultado de Holland en el prompt **no mueve la
recomendación** (medido: 5 de 6 corridas ignoraron el área más alta, ver
`experiments/holland-en-chat.md`). La conclusión de ese experimento fue que si
Holland tiene que pesar, entra como **estructura**, no como prosa: cada carrera
del catálogo con su vector RIASEC, y el ranking ordenado por distancia al vector
del alumno.

Este script produce esa estructura. Para cada perfil del catálogo:

1. busca el nombre de la carrera en el buscador **en español** de O*NET
   (`/mpp/search`, el mismo "Mi Próximo Paso" que sirve el test),
2. toma las `OCUPACIONES` primeras ocupaciones,
3. les pide su perfil de intereses oficial
   (`/online/occupations/{code}/details/interests`, 0-100 por área),
4. promedia los vectores y guarda el resultado.

**El código RIASEC no lo inventa un modelo**: sale de la misma fuente que
califica el test del alumno. Esa es exactamente la ventaja que el CIP no tenía
(ver `experiments/cip-en-recomendacion.md` §6, donde el instrumento simulado
invalidó el A/B).

## Igual que en el CIP

- Se codifica **por perfil, no por registro**: la misma carrera recibe el mismo
  vector en todas sus sedes, por construcción.
- Un solo archivo, `data/holland_catalogo.json`, para que sea revisable a mano.
- Idempotente y resumible: solo pide lo que falta.
- Corre **offline, una vez**. En tiempo de ejecución solo se lee el JSON.

## Esto NO es el producto final

El emparejamiento carrera guatemalteca → ocupación de EE. UU. lo hace un
buscador por palabras: va a fallar en las carreras de nombre local (los
profesorados, los peritos) y en las híbridas. Cada entrada guarda **qué
ocupaciones se usaron** y `"revisado": false` justamente para que la revisión
humana sea posible y quede dicho que hace falta. `--revisar` imprime el informe.

## Uso

    uv run python codificar_holland.py --limite 3   # prueba de humo
    uv run python codificar_holland.py              # el resto
    uv run python codificar_holland.py --revisar    # informe, sin red
"""

import argparse
import glob
import json
import os
import re
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv()

from app import holland  # noqa: E402  (usa el mismo cliente/credenciales del test)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "holland_catalogo.json")
COMPARTIDOS = os.path.join(DATA, "perfiles_compartidos.json")

# Cuántas ocupaciones de la búsqueda se promedian. Con 1 el vector queda a merced
# de que el primer resultado sea el técnico y no el profesional; con muchas se
# diluye. 3 es el punto en que un mal acierto no arrastra al promedio.
# ponytail: número fijo, no ponderado por posición. Si la revisión humana muestra
# que el 3.º suele ser ruido, bajarlo a 2 antes de inventar pesos.
OCUPACIONES = 3
LETRAS = "RIASEC"


def _cliente() -> httpx.Client:
    """El mismo cliente de `app.holland`, pero contra la raíz de la API: acá se
    usan `/mpp/search` y `/online/...`, no solo el Interest Profiler."""
    c = holland._cliente()
    c.base_url = "https://api-v2.onetcenter.org"
    return c


def perfiles_del_catalogo() -> dict[str, dict]:
    """{clave: {nombre, sedes}} — una entrada por perfil distinto.

    Misma convención de clave que `codificar_cip.py` y que `cip_filtro._clave`:
    `perfil_id` si la carrera comparte perfil entre sedes, `"centro::nombre"` si
    lo trae inline. Se copia en vez de importarse porque aquel módulo arrastra a
    Gemini al importarse y esto no necesita ni una llamada de IA.
    """
    out: dict[str, dict] = {}
    for archivo in sorted(glob.glob(os.path.join(DATA, "carreras_*.json"))):
        d = json.load(open(archivo, encoding="utf-8"))
        for c in d["carreras"]:
            clave = c.get("perfil_id") or f'{d["centro"]}::{c["nombre"]}'
            out.setdefault(clave, {"nombre": c["nombre"], "sedes": []})
            out[clave]["sedes"].append(d["centro"])
    return out


# El grado académico no es una ocupación y ensucia la búsqueda: con
# "Licenciatura en Ciencias Jurídicas y Sociales" el primer resultado eran
# profesores universitarios; sin el grado, salen los oficiales jurídicos.
# "PEM" se expande porque es una sigla local que O*NET no puede conocer;
# "Profesorado" NO se quita: ahí la docencia sí es la ocupación.
PREFIJOS = ("Licenciatura en la ", "Licenciatura en ", "Técnico Universitario en ",
            "Técnico en ")


def termino(nombre: str) -> str:
    """El nombre de la carrera como palabras que O*NET pueda buscar."""
    t = re.sub(r"\s*\([^)]*\)", "", nombre).strip()  # "(Técnico Universitario)" y demás
    for p in PREFIJOS:
        if t.startswith(p):
            t = t[len(p):]
            break
    return re.sub(r"^PEM en ", "Profesorado de Enseñanza Media en ", t)


def _buscar(cli: httpx.Client, nombre: str) -> list[dict]:
    """Las primeras ocupaciones de O*NET para el nombre de una carrera."""
    r = cli.get("/mpp/search",
                params={"keyword": termino(nombre), "start": 1, "end": OCUPACIONES})
    r.raise_for_status()
    return r.json().get("career", [])[:OCUPACIONES]


def _intereses(cli: httpx.Client, code: str) -> dict[str, int]:
    """{letra: 0-100} del perfil de intereses oficial de una ocupación."""
    r = cli.get(f"/online/occupations/{code}/details/interests")
    r.raise_for_status()
    # `name` viene en inglés (Realistic, Investigative, ...) y las seis iniciales
    # son distintas, igual que en `app.holland`.
    return {e["name"][0].upper(): e["occupational_interest"] for e in r.json()["element"]}


def _codigo(vector: dict[str, float]) -> str:
    """Las 3 letras más altas; empates por orden canónico RIASEC, como en el test."""
    orden = sorted(LETRAS, key=lambda l: (-vector.get(l, 0), LETRAS.index(l)))
    return "".join(orden[:3])


def codificar_una(cli: httpx.Client, nombre: str) -> dict | None:
    ocupaciones = _buscar(cli, nombre)
    if not ocupaciones:
        return None
    vectores = [_intereses(cli, o["code"]) for o in ocupaciones]
    vector = {l: round(sum(v.get(l, 0) for v in vectores) / len(vectores), 1) for l in LETRAS}
    return {
        "nombre": nombre,
        "vector": vector,
        "codigo": _codigo(vector),
        # Se guarda con qué ocupaciones se armó: sin esto, la revisión humana
        # tendría que adivinar por qué una carrera salió como salió.
        "ocupaciones": [{"code": o["code"], "title": o["title"]} for o in ocupaciones],
        "revisado": False,
    }


def codificar(limite: int | None = None):
    perfiles = perfiles_del_catalogo()
    hecho = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else {}
    pendientes = [(k, v) for k, v in perfiles.items() if k not in hecho][:limite or None]
    if not pendientes:
        print(f"Nada pendiente: los {len(perfiles)} perfiles ya están codificados.")
        return

    print(f"{len(perfiles)} perfiles · {len(hecho)} ya codificados · "
          f"{len(pendientes)} por codificar ({(1 + OCUPACIONES) * len(pendientes)} llamadas a O*NET)")
    with _cliente() as cli:
        for i, (clave, v) in enumerate(pendientes, 1):
            try:
                entrada = codificar_una(cli, v["nombre"])
            except httpx.HTTPError as e:
                print(f"  [{i}/{len(pendientes)}] {v['nombre']}: falló ({e})")
                continue
            if not entrada:
                print(f"  [{i}/{len(pendientes)}] {v['nombre']}: O*NET no devolvió ocupaciones")
                continue
            hecho[clave] = entrada
            print(f"  [{i}/{len(pendientes)}] {v['nombre']} -> {entrada['codigo']} "
                  f"({entrada['ocupaciones'][0]['title']})")
            # Se guarda en cada vuelta: si se corta, no se repite lo hecho.
            json.dump(dict(sorted(hecho.items())), open(SALIDA, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
    print(f"\n{SALIDA} · {len(hecho)} carreras codificadas")


def revisar():
    """Informe para la revisión humana. Sin red."""
    hecho = json.load(open(SALIDA, encoding="utf-8"))
    perfiles = perfiles_del_catalogo()
    faltan = [v["nombre"] for k, v in perfiles.items() if k not in hecho]
    print(f"{len(hecho)}/{len(perfiles)} perfiles codificados · "
          f"{sum(1 for v in hecho.values() if v['revisado'])} revisados a mano")
    print("Distribución de códigos: "
          + ", ".join(f"{c}={n}" for c, n in Counter(v["codigo"] for v in hecho.values()).most_common(10)))
    if faltan:
        print(f"Sin codificar ({len(faltan)}): " + ", ".join(faltan[:10]))
    print("\nCarrera -> código · ocupaciones de O*NET con las que se armó:")
    for v in sorted(hecho.values(), key=lambda v: v["nombre"]):
        marca = " " if v["revisado"] else "·"
        print(f" {marca} {v['nombre'][:48]:<48} {v['codigo']}  "
              + "; ".join(o["title"] for o in v["ocupaciones"]))


def _self_check():
    assert _codigo({"R": 90, "I": 80, "A": 10, "S": 70, "E": 5, "C": 5}) == "RIS"
    # Empate: manda el orden canónico RIASEC, no el del diccionario.
    assert termino("Licenciatura en Economía") == "Economía"
    assert termino("PEM en Matemática y Física") == "Profesorado de Enseñanza Media en Matemática y Física"
    assert termino("Chef Profesional e Internacional (Técnico Universitario)") == "Chef Profesional e Internacional"
    assert termino("Profesorado en Educación Primaria") == "Profesorado en Educación Primaria"
    assert _codigo({"C": 50, "A": 50, "R": 50, "I": 1, "S": 1, "E": 1}) == "RAC"
    p = perfiles_del_catalogo()
    assert len(p) > 50, len(p)
    assert all(v["sedes"] for v in p.values())
    print(f"self-check OK — {len(p)} perfiles en el catálogo")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limite", type=int, help="codifica solo N perfiles pendientes")
    ap.add_argument("--revisar", action="store_true", help="informe, sin red")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.revisar:
        revisar()
    else:
        codificar(a.limite)
