"""Pre-filtro barato (sin IA) del catálogo antes de mandarlo a Gemini en
next-question: en vez de las 94-122 carreras completas, nos quedamos con las
~30 más afines según las respuestas del estudiante hasta ahora (solapamiento
de palabras entre sus respuestas y el 'perfil'/banco de palabras de cada
carrera). Sin librerías nuevas, sin entrenar nada.

Se recalcula en CADA llamada con TODAS las respuestas acumuladas (fijas +
adaptativas), así que si el perfil del estudiante cambia de rumbo a mitad de
conversación, el recorte se ajusta solo en la siguiente llamada.

recommend() NO usa este filtro: se llama una sola vez por sesión (el ahorro
por-llamada importa menos ahí) y preferimos minimizar el riesgo de excluir
una carrera válida de la respuesta final."""

import re
from collections import Counter

TOP_DEFAULT = 35

STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "que", "con",
    "para", "por", "es", "su", "sus", "del", "al", "lo", "como", "más", "o",
    "u", "e", "ni", "se", "le", "les", "me", "mi", "tu", "te", "no", "sí",
    "muy", "esta", "este", "esto", "son", "hay", "ser", "estar", "cada",
}

_PALABRA = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def _palabras(texto: str) -> Counter:
    """Cuenta palabras relevantes (sin stopwords, largo > 2) de un texto."""
    return Counter(
        w for w in _PALABRA.findall((texto or "").lower())
        if w not in STOPWORDS and len(w) > 2
    )


def preseleccionar(respuestas: dict, carreras: list, top: int = TOP_DEFAULT) -> list:
    """Devuelve hasta `top` carreras de `carreras`, las de mayor solapamiento
    de palabras con las respuestas del estudiante (departamento excluido: no
    aporta señal vocacional). Si ya hay <= top carreras, no filtra nada."""
    if len(carreras) <= top:
        return carreras

    texto_estudiante = " ".join(
        str(v) for k, v in respuestas.items() if k != "departamento"
    )
    palabras_estudiante = _palabras(texto_estudiante)
    if not palabras_estudiante:
        return carreras[:top]

    def puntaje(carrera) -> int:
        palabras_perfil = {
            w for w in _PALABRA.findall(carrera.perfil.lower())
            if w not in STOPWORDS
        }
        return sum(cnt for w, cnt in palabras_estudiante.items() if w in palabras_perfil)

    return sorted(carreras, key=puntaje, reverse=True)[:top]


if __name__ == "__main__":
    # ponytail: self-check sin BD ni llamadas a la API.
    class _C:
        def __init__(self, nombre, perfil):
            self.nombre, self.perfil = nombre, perfil

    afin = _C("Ingeniería en Sistemas", "programación software algoritmos tecnología código")
    lejana = _C("Trabajo Social", "comunidad pobreza justicia intervención social")
    otras = [_C(f"Relleno {i}", "texto neutro sin relación clara") for i in range(40)]

    respuestas = {"departamento": "Quetzaltenango", "gustos": "tecnología y programación"}
    resultado = preseleccionar(respuestas, [lejana, *otras, afin], top=5)
    assert afin in resultado, "la carrera afín debe sobrevivir al recorte"
    assert resultado[0] is afin, "la carrera afín debe quedar primera"

    # <= top: no filtra nada, aunque el puntaje sea 0 para todas.
    pocas = [lejana, afin]
    assert preseleccionar(respuestas, pocas, top=5) == pocas

    # sin señal en las respuestas (todo stopwords/vacío): recorta sin romper.
    sin_senal = preseleccionar({"departamento": "Quetzaltenango"}, [lejana, *otras, afin], top=3)
    assert len(sin_senal) == 3

    print("ok")
