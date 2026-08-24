# -*- coding: utf-8 -*-
"""¿Las etiquetas acortadas dicen lo mismo que las largas?

Acortar los chips para que quepan en una línea cambia el texto que el alumno
marca, y eso es literalmente la señal que entra al prompt. La cobertura del
catálogo se verifica gratis con `cobertura_banco.py`; lo que esa herramienta NO
puede ver es si el significado se movió, porque compara palabras.

Esto es una comprobación DIRIGIDA y barata: una sola llamada con los 25 pares
antes/después, pidiendo que marque los que dejaron de comunicar lo mismo. No
reemplaza un A/B de recomendaciones; sirve para atrapar el caso obvio (una
etiqueta que al recortarse pasó a significar otra cosa) antes de gastar en uno.

Uso:  uv run python verifica_etiquetas.py
"""

import os

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import recomendar  # noqa: E402

# (larga original, corta nueva). Solo las que cambiaron.
PARES = [
    ("Salud, cuidados y atención a pacientes", "Salud y cuidar pacientes"),
    ("Equipos médicos, laboratorio e imágenes", "Equipos médicos e imágenes"),
    ("Cuerpo, deporte y rehabilitación", "Deporte y rehabilitación"),
    ("Ambiente, agricultura y agronegocios", "Ambiente y agronegocios"),
    ("Construcción, máquinas y cómo funcionan las cosas", "Construcción y máquinas"),
    ("Enseñanza, docencia y educación", "Enseñanza y docencia"),
    ("Psicología y comportamiento", "Psicología y conducta"),
    ("Historia, sociedad y cultura", "Historia y sociedad"),
    ("Fe, religión y espiritualidad", "Fe y espiritualidad"),
    ("Música, danza y artes escénicas", "Música, danza y teatro"),
    ("Comunicación, escritura y medios", "Comunicación y medios"),
    ("Negocios, dinero y emprendimiento", "Negocios y emprendimiento"),
    ("Economía, pobreza y desarrollo del país", "Economía y pobreza"),
    ("Comercio, política y otros países", "Comercio y otros países"),
    ("Organizar y dirigir equipos o instituciones", "Dirigir instituciones"),
    ("Gastronomía, turismo y hotelería", "Gastronomía y turismo"),
]


class Veredicto(BaseModel):
    numero: int
    equivalente: bool
    que_se_perdio: str   # "" si no se perdió nada relevante


class Revision(BaseModel):
    veredictos: list[Veredicto]


SYSTEM = (
    "Eres un orientador vocacional. Te dan pares de etiquetas de un test de "
    "intereses: la versión LARGA que se usaba y la versión CORTA que la "
    "reemplaza. La corta existe para que quepa en pantalla.\n\n"
    "Para cada par, di si un estudiante de 17 años entendería lo MISMO al "
    "leerlas, y si la versión corta dejó fuera algún interés que la larga sí "
    "cubría.\n\n"
    "- 'equivalente': true si apuntan al mismo territorio de intereses. false "
    "si la corta excluye un interés que la larga incluía, o si desvía el "
    "sentido.\n"
    "- 'que_se_perdio': si equivalente es false, di en pocas palabras qué "
    "interés quedó fuera. Si es true, cadena vacía.\n"
    "- Sé estricto: es preferible marcar una duda que dejarla pasar.\n"
    "- Devuelve un veredicto por cada par, con su 'numero'.\n"
    "- Español."
)


def main():
    listado = "\n".join(f"{i}. LARGA: {a}\n   CORTA: {b}"
                        for i, (a, b) in enumerate(PARES, 1))
    resp = recomendar.generar(
        model=recomendar.MODELO, system=SYSTEM, catalogo="",
        variable=f"PARES A REVISAR:\n{listado}",
        schema=Revision, temperature=0.0)
    rev = Revision.model_validate_json(recomendar._texto_seguro(resp))

    dudosos = [v for v in rev.veredictos if not v.equivalente]
    print(f"Pares revisados: {len(rev.veredictos)} de {len(PARES)}")
    print(f"Marcados como equivalentes: {len(rev.veredictos) - len(dudosos)}")
    print()
    if dudosos:
        print("MARCADOS COMO NO EQUIVALENTES (revisar a mano):")
        for v in dudosos:
            i = v.numero - 1
            if 0 <= i < len(PARES):
                print(f"  {v.numero}. {PARES[i][0]}")
                print(f"     -> {PARES[i][1]}")
            print(f"     se perdió: {v.que_se_perdio}")
    else:
        print("Ninguno marcado. Ojo: esto atrapa el cambio obvio de sentido,")
        print("no prueba que la recomendación no se mueva. Para eso hace falta")
        print("el A/B de coherencia (ver experimento_banco.py).")
    print(recomendar.resumen_gasto())


if __name__ == "__main__":
    main()
