"""Motor de recomendación: le pasa el perfil del estudiante y el catálogo de
carreras a Claude, y devuelve carreras recomendadas con justificación."""

import os

from anthropic import Anthropic
from pydantic import BaseModel

MODELO = "claude-opus-4-8"


class Recomendacion(BaseModel):
    carrera: str
    universidad: str
    justificacion: str


class Recomendaciones(BaseModel):
    recomendaciones: list[Recomendacion]


def hay_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _catalogo_texto(carreras) -> str:
    lineas = []
    for c in carreras:
        materias = ", ".join(c.materias or [])
        lineas.append(
            f"- {c.nombre} ({c.universidad})\n"
            f"  Núcleo de formación: {c.nucleo_formacion or 'N/D'}\n"
            f"  Materias representativas: {materias or 'N/D'}"
        )
    return "\n".join(lineas)


def recomendar(respuestas: dict, carreras) -> list[Recomendacion]:
    """respuestas: dict con las respuestas del cuestionario.
    carreras: lista de models.Carrera (el catálogo).
    Devuelve hasta 3 carreras recomendadas, de mayor a menor afinidad."""
    perfil = "\n".join(f"- {k}: {v}" for k, v in respuestas.items())

    client = Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    resp = client.messages.parse(
        model=MODELO,
        max_tokens=2000,
        system=(
            "Eres un orientador vocacional. A partir del perfil de un estudiante "
            "y un catálogo de carreras, recomienda las 3 carreras más afines, de "
            "mayor a menor. Usa SOLO carreras del catálogo. En cada justificación, "
            "conecta de forma concreta los intereses del estudiante con el núcleo "
            "y las materias de la carrera. Escribe en español, cercano y claro."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"PERFIL DEL ESTUDIANTE:\n{perfil}\n\n"
                    f"CATÁLOGO DE CARRERAS:\n{_catalogo_texto(carreras)}"
                ),
            }
        ],
        output_format=Recomendaciones,
    )
    return resp.parsed_output.recomendaciones


if __name__ == "__main__":
    # ponytail: self-check del parseo del catálogo, sin llamar a la API.
    class _C:
        def __init__(self, n, u, nuc, mat):
            self.nombre, self.universidad, self.nucleo_formacion, self.materias = n, u, nuc, mat

    txt = _catalogo_texto([_C("Ing. Sistemas", "UMG", "Computación", ["Cálculo", "Programación"])])
    assert "Ing. Sistemas" in txt and "UMG" in txt and "Programación" in txt
    print("ok")
