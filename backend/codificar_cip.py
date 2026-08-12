"""Codifica el catálogo de carreras con las 15 escalas del CIP.

## Qué hace y por qué

Hoy el emparejamiento alumno↔carrera vive entero dentro de Gemini: se le manda el
perfil en texto de cada carrera y él decide. Funciona, pero no es auditable ("¿por
qué salió esta carrera primero?" → "el modelo lo decidió") ni estable entre
corridas.

Este script le agrega a cada carrera **la escala del CIP a la que pertenece**. Con
eso, el emparejamiento pasa a ser una consulta: si el alumno saca percentil 92 en
Biosanitaria (VII), las carreras VII del catálogo son candidatas por aritmética, no
por criterio del modelo. Gemini queda redactando el porqué y desempatando, que es
lo que hace bien.

## Cómo

- Se codifica **por perfil, no por registro**: 202 registros carrera-sede comparten
  90 perfiles distintos (64 en `perfiles_compartidos.json` + 26 inline). Así la
  misma carrera recibe el mismo código en todas sus sedes, por construcción.
- El resultado va a **un solo archivo**, `data/cip_catalogo.json`, no repartido en
  los 12 archivos del catálogo. Es deliberado: alguien tiene que revisar esto a
  mano, y revisar una lista de 90 líneas es viable; revisar 12 archivos no.
- Es **idempotente y resumible**: relee lo ya codificado y solo pide lo que falta.
  Si la corrida se corta a la mitad, volver a ejecutarlo no vuelve a gastar cuota.
- Corre **una sola vez, offline**. En tiempo de ejecución el sistema solo lee el
  JSON: cero llamadas a Gemini, cero costo por alumno.

## La codificación automática NO es el producto final

Va a fallar en las carreras híbridas y en las de nombre local poco común. El
archivo generado marca cada entrada con `"revisado": false`; la revisión humana de
un profesional de orientación es parte del trabajo, no un adorno. Es también lo
que permite escribir en el documento "codificación asistida por IA, validada por
profesional colegiada" en lugar de "el modelo la generó".

## Uso

    uv run python codificar_cip.py --limite 5    # prueba de humo, 1 llamada
    uv run python codificar_cip.py               # el resto
    uv run python codificar_cip.py --revisar     # informe, sin llamar a Gemini
"""

import argparse
import glob
import json
import os
from collections import Counter
from typing import Literal

from dotenv import load_dotenv

# ANTES de importar `app.recomendar`: además de la GEMINI_API_KEY, ese módulo
# resuelve MODELO/MODELO_FINAL con os.getenv al importarse. Cargar el .env
# después hace que el script use el modelo por defecto del código en vez del
# configurado en el proyecto.
load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import cip_fogliatto, recomendar  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "cip_catalogo.json")
COMPARTIDOS = os.path.join(DATA, "perfiles_compartidos.json")
POR_LOTE = 25  # 90 perfiles → 4 llamadas

ROMANOS = [e["romano"] for e in cip_fogliatto.ESCALAS]

SYSTEM = """Eres un orientador vocacional que clasifica carreras universitarias
guatemaltecas dentro de las 15 escalas de intereses del Cuestionario de Intereses
Profesionales (CIP) de Fogliatto.

Para cada carrera devuelves:
- `principal`: la escala que mejor describe el tipo de ACTIVIDAD COTIDIANA que
  realiza quien ejerce esa profesión.
- `secundaria`: una segunda escala relevante, o null si la carrera es claramente
  de una sola área.

Reglas:
- Clasifica por la actividad diaria del egresado, no por la facultad que la
  imparte ni por el prestigio de la carrera.
- Usa EXCLUSIVAMENTE los códigos romanos de la lista de escalas. Nunca inventes uno.
- `secundaria` debe ser distinta de `principal`, o null.
- Devuelve exactamente una entrada por cada carrera recibida, con su misma `clave`.

Escalas disponibles:
""" + "\n".join(
    f'{e["romano"]}. {e["nombre"]}: {e["definicion"]}' for e in cip_fogliatto.ESCALAS
)


# Los 15 códigos van como enum en el esquema, no como texto libre: en la primera
# prueba el modelo devolvió "X. Económica-Administrativa" (copió la etiqueta de la
# lista de escalas del SYSTEM) y hubo que descartar el lote entero. Con el enum,
# la propia API restringe los valores posibles.
Romano = Literal["I", "II", "III", "IV", "V", "VI", "VII", "VIII",
                 "IX", "X", "XI", "XII", "XIII", "XIV", "XV"]


class Codigo(BaseModel):
    clave: str
    principal: Romano
    secundaria: Romano | None = None


class Lote(BaseModel):
    codigos: list[Codigo]


def perfiles_del_catalogo() -> dict[str, dict]:
    """{clave: {nombre, perfil, sedes}} — una entrada por perfil distinto.

    La clave es el `perfil_id` cuando la carrera comparte perfil entre sedes, y
    `"centro::nombre"` cuando lo trae inline. Es estable mientras no se renombre
    la carrera o el centro, que es la misma condición que ya asume `seed_carreras`.
    """
    compartidos = json.load(open(COMPARTIDOS, encoding="utf-8"))
    out: dict[str, dict] = {}
    for archivo in sorted(glob.glob(os.path.join(DATA, "carreras_*.json"))):
        d = json.load(open(archivo, encoding="utf-8"))
        for c in d["carreras"]:
            pid = c.get("perfil_id")
            clave = pid or f'{d["centro"]}::{c["nombre"]}'
            entrada = out.setdefault(clave, {
                "nombre": c["nombre"],
                "perfil": compartidos[pid] if pid else c["perfil"],
                "sedes": [],
            })
            entrada["sedes"].append(d["centro"])
    return out


def _pedir(pendientes: list[tuple[str, dict]]) -> list[Codigo]:
    """Una llamada a Gemini por lote. El perfil se recorta: la clasificación se
    decide con la actividad y el entorno, que están al inicio; mandar el párrafo
    completo de las 90 carreras multiplica el costo sin mejorar el resultado."""
    listado = "\n\n".join(
        f'clave: {clave}\ncarrera: {v["nombre"]}\nperfil: {v["perfil"][:700]}'
        for clave, v in pendientes
    )
    resp = recomendar.generar(
        model=recomendar.MODELO_FINAL,
        system=SYSTEM,
        catalogo="",
        variable=f"Clasifica estas {len(pendientes)} carreras:\n\n{listado}",
        schema=Lote,
        temperature=0.0,  # clasificación, no redacción: se quiere reproducible
    )
    return Lote.model_validate_json(resp.text).codigos


def _validar(cod: Codigo, esperadas: set[str]) -> str | None:
    """Devuelve el motivo del rechazo, o None si la codificación es utilizable."""
    if cod.clave not in esperadas:
        return "clave que no se pidió"
    if cod.principal not in ROMANOS:
        return f"escala principal inexistente: {cod.principal}"
    if cod.secundaria is not None and cod.secundaria not in ROMANOS:
        return f"escala secundaria inexistente: {cod.secundaria}"
    if cod.secundaria == cod.principal:
        return "secundaria igual a la principal"
    return None


def codificar(limite: int | None = None):
    perfiles = perfiles_del_catalogo()
    hecho = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else {}
    pendientes = [(k, v) for k, v in perfiles.items() if k not in hecho]
    if limite:
        pendientes = pendientes[:limite]
    if not pendientes:
        print(f"Nada pendiente: los {len(perfiles)} perfiles ya están codificados.")
        return

    print(f"{len(perfiles)} perfiles en el catálogo · {len(hecho)} ya codificados · "
          f"{len(pendientes)} por codificar en {-(-len(pendientes) // POR_LOTE)} llamada(s)")

    for i in range(0, len(pendientes), POR_LOTE):
        lote = pendientes[i:i + POR_LOTE]
        esperadas = {k for k, _ in lote}
        print(f"  lote {i // POR_LOTE + 1}: {len(lote)} carreras…", end=" ", flush=True)
        codigos = _pedir(lote)
        ok = 0
        for cod in codigos:
            motivo = _validar(cod, esperadas)
            if motivo:
                print(f"\n    descartado {cod.clave!r}: {motivo}")
                continue
            hecho[cod.clave] = {
                "nombre": perfiles[cod.clave]["nombre"],
                "principal": cod.principal,
                "secundaria": cod.secundaria,
                "revisado": False,  # lo pone en true quien lo revise a mano
            }
            ok += 1
        faltan = esperadas - set(hecho)
        print(f"{ok} codificadas" + (f", {len(faltan)} sin respuesta" if faltan else ""))
        # Se guarda tras cada lote: si el siguiente falla, no se pierde lo pagado.
        json.dump(dict(sorted(hecho.items())), open(SALIDA, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    print(f"\nGuardado en {os.path.relpath(SALIDA)}")
    informe()


def informe():
    """Estado de la codificación. No llama a Gemini."""
    perfiles = perfiles_del_catalogo()
    hecho = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else {}
    nombres = {e["romano"]: e["nombre"] for e in cip_fogliatto.ESCALAS}
    sedes = Counter()
    for clave, v in perfiles.items():
        if clave in hecho:
            sedes[hecho[clave]["principal"]] += len(v["sedes"])

    faltan = [k for k in perfiles if k not in hecho]
    sin_revisar = [k for k, v in hecho.items() if not v.get("revisado")]
    print(f"\n{'─' * 62}\nCobertura: {len(hecho)}/{len(perfiles)} perfiles "
          f"({sum(sedes.values())}/{sum(len(v['sedes']) for v in perfiles.values())} "
          f"registros carrera-sede)")
    if faltan:
        print(f"Sin codificar: {faltan}")
    print(f"Pendientes de revisión humana: {len(sin_revisar)}")

    print("\nDistribución por escala principal (registros carrera-sede):")
    for rom in ROMANOS:
        n = sedes.get(rom, 0)
        print(f"  {rom:>4}. {nombres[rom]:<26} {n:>3} {'█' * n}")
    vacias = [nombres[r] for r in ROMANOS if not sedes.get(r)]
    if vacias:
        print(f"\n  Escalas sin ninguna carrera en el catálogo: {', '.join(vacias)}")
        print("  No es un error: significa que la oferta local no cubre esa área.")
        print("  Un alumno con percentil alto ahí necesita que el chat se lo diga.")


def _self_check():
    """Comprueba el armado del catálogo y la validación, sin llamar a Gemini."""
    perfiles = perfiles_del_catalogo()
    assert perfiles, "no se leyó ningún perfil del catálogo"
    assert all(v["nombre"] and v["perfil"] and v["sedes"] for v in perfiles.values())
    # Un perfil compartido tiene que aparecer una sola vez, con todas sus sedes.
    compartidos = json.load(open(COMPARTIDOS, encoding="utf-8"))
    multi = [k for k in compartidos if k in perfiles and len(perfiles[k]["sedes"]) > 1]
    assert multi, "se esperaba al menos un perfil compartido entre sedes"

    # El enum del esquema tiene que seguir siendo exactamente las escalas del
    # instrumento: si algún día cambian, esto truena antes de gastar cuota.
    from typing import get_args
    assert list(get_args(Romano)) == ROMANOS, "el enum no coincide con las escalas del CIP"

    # Capa 1 — el esquema rechaza cualquier código que no sea una de las 15 escalas.
    for malo in ({"principal": "XVI"}, {"principal": "I", "secundaria": "ZZ"},
                 {"principal": "X. Económica-Administrativa"}):  # el fallo real observado
        try:
            Codigo(clave="x", **malo)
        except Exception:
            pass
        else:
            raise AssertionError(f"el esquema aceptó {malo}")

    # Capa 2 — `_validar` cubre lo que el esquema no puede ver. Se usa
    # model_construct para saltarse la validación y llegar a esos casos.
    esperadas = {"x", "y"}
    crudo = lambda **kw: Codigo.model_construct(**kw)
    assert _validar(crudo(clave="z", principal="I"), esperadas) == "clave que no se pidió"
    assert _validar(crudo(clave="x", principal="XVI"), esperadas)
    assert _validar(crudo(clave="x", principal="I", secundaria="I"), esperadas) == \
        "secundaria igual a la principal"
    assert _validar(Codigo(clave="x", principal="VII", secundaria="VIII"), esperadas) is None
    assert _validar(Codigo(clave="y", principal="VII"), esperadas) is None
    print(f"self-check OK — {len(perfiles)} perfiles distintos, "
          f"{sum(len(v['sedes']) for v in perfiles.values())} registros carrera-sede")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--limite", type=int, help="codifica solo N perfiles (prueba de humo)")
    p.add_argument("--revisar", action="store_true", help="informe, sin llamar a Gemini")
    p.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    a = p.parse_args()
    if a.self_check:
        _self_check()
    elif a.revisar:
        informe()
    else:
        codificar(a.limite)
