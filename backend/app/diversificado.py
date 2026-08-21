"""Puente para los alumnos de BÁSICO: de las carreras universitarias que les
recomendó el chat a las carreras de diversificado que las preparan.

Es la petición de la psicóloga en la sesión de validación: un alumno de tercero
básico no elige universidad todavía, elige diversificado. Devolverle un top de
carreras universitarias y nada más lo deja sin el paso que sí tiene enfrente.

Sin IA y sin tokens: la tabla vive en `data/diversificados.json` y esto solo
cruza los nombres de las carreras recomendadas contra sus 'claves'.

La tabla sale de una investigación de la oferta REAL de diversificado en las
zonas céntricas de Totonicapán y Quetzaltenango, y por eso cada opción dice en
qué departamentos existe. No se nombran establecimientos: al alumno se le dice
la modalidad y dónde se ofrece, no a qué colegio ir. Al ampliar el catálogo a
otros departamentos hay que repetir la investigación.

Self-check: uv run python -m app.diversificado
"""

import json
import os
import unicodedata

DATOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "diversificados.json")

TOPE = 3  # cuántas opciones se le muestran: más que esto deja de ser una guía


def _normaliza(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _opciones() -> list[dict]:
    with open(DATOS, encoding="utf-8") as f:
        return json.load(f)["opciones"]


def _visible(opciones: list[dict]) -> list[dict]:
    """Lo que se le muestra al alumno: la modalidad, por qué, y en qué
    departamentos existe. Las 'claves' son de uso interno y no salen."""
    return [
        {"nombre": o["nombre"], "porque": o["porque"], "departamentos": o["departamentos"]}
        for o in opciones
    ]


def sugerir(carreras: list[str], tope: int = TOPE) -> list[dict]:
    """Carreras de diversificado para un top de carreras universitarias, en el
    orden en que aparecen las universitarias (la primera recomendación manda).

    ponytail: cruce por subcadena contra 'claves', igual que el resto del
    proyecto. No entiende sinónimos: una carrera cuyo nombre no comparta
    ninguna clave simplemente no suma, y si ninguna suma se devuelve vacío en
    vez de inventar una opción.
    """
    opciones = _opciones()
    salida: list[dict] = []
    for carrera in carreras:
        nombre = _normaliza(carrera)
        for opcion in opciones:
            if opcion in salida:
                continue
            if any(_normaliza(clave) in nombre for clave in opcion["claves"]):
                salida.append(opcion)
                if len(salida) >= tope:
                    return _visible(salida)
    return _visible(salida)


if __name__ == "__main__":
    r = sugerir(["Ingeniería en Ciencias y Sistemas", "Ingeniería Industrial",
                 "Licenciatura en Contaduría Pública y Auditoría"])
    assert "Computación" in r[0]["nombre"], "manda la primera carrera recomendada"
    assert len(r) == 3, "tres carreras de áreas distintas dan tres opciones"

    # El orden lo manda la recomendación: si la primera es de salud, esa va primero.
    r2 = sugerir(["Licenciatura en Enfermería", "Ingeniería en Sistemas"])
    assert "Biológicas" in r2[0]["nombre"]
    assert r2[0]["departamentos"] == ["Totonicapán", "Quetzaltenango"]
    assert "claves" not in r2[0], "las claves son internas, no se muestran"

    # Sin repetidos: dos carreras del mismo área dan UNA opción.
    r3 = sugerir(["Ingeniería en Sistemas", "Ingeniería en Sistemas de Información"])
    assert len(r3) == 1

    # Nada que cruzar: devuelve vacío, no inventa.
    assert sugerir(["Carrera Inexistente de Prueba"]) == []
    assert sugerir([]) == []

    # El tope se respeta aunque haya más coincidencias.
    assert len(sugerir(["Licenciatura en Enfermería", "Ingeniería en Sistemas",
                        "Contaduría Pública y Auditoría", "Ingeniería Agronómica"],
                       tope=2)) == 2
    print("ok")
