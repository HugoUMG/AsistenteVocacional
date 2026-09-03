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

# Respuestas que NO aportan señal vocacional al solapamiento de palabras. El
# nivel, el grado y el motivo se excluyen porque su texto ("universidad",
# "carrera", "estudiar") solapa con casi cualquier perfil y ensucia el puntaje.
# El nombre se excluye por lo mismo y por una razón de costo: el catálogo
# recortado es la clave del caché de Gemini (sha256 en recomendar._clave_cache),
# así que meter el nombre del alumno le da un hash propio a cada uno y ningún
# caché se reusa. Ver experiments/cache-compartido.md.
# 'carrera_cursada' SÍ se queda: el bachillerato o la carrera que lleva es señal
# real de sus intereses. Siguen llegando
# completas al prompt de Gemini: esto solo afecta el recorte del catálogo.
_SIN_SENAL = {"departamento", "nombre", "edad", "nivel", "grado", "motivo"}


def _normaliza(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar 'Ingeniería' con 'ingenieria'."""
    tabla = str.maketrans("áéíóúü", "aeiouu")
    return (texto or "").lower().translate(tabla)


def _significativas(texto: str) -> set:
    """Palabras con carga semántica de un nombre de carrera: sin stopwords y de
    más de 3 letras, para que 'en', 'de' o 'con' no emparejen nada."""
    return {
        w for w in _PALABRA.findall(_normaliza(texto))
        if w not in STOPWORDS and len(w) > 3
    }


def descartar(carreras: list, carrera_abandonada: str | None) -> list:
    """Saca del catálogo la carrera que el alumno dijo que abandonó, y sus
    variantes de nombre ('Ingeniería en Sistemas' también saca 'Ingeniería en
    Ciencias y Sistemas'). Se compara por palabras significativas: una carrera
    se descarta si comparte TODAS las del texto del alumno, o al menos dos.

    ponytail: emparejamiento por palabras, no semántico. No sabe que 'Derecho'
    es 'Ciencias Jurídicas y Sociales', así que ahí no descarta nada; el techo
    se sube con una tabla de sinónimos si hace falta. Prefiere quedarse corto:
    borrar de más le quitaría opciones válidas al alumno.
    """
    query = _significativas(carrera_abandonada or "")
    if not query:
        return carreras

    def coincide(carrera) -> bool:
        palabras = _significativas(carrera.nombre)
        comunes = query & palabras
        return comunes == query or len(comunes) >= 2

    quedan = [c for c in carreras if not coincide(c)]
    # Red de seguridad: si el texto era tan genérico que se llevó medio
    # catálogo, no se descarta nada y que decida el modelo.
    if len(quedan) < len(carreras) * 0.7:
        return carreras
    return quedan


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
        str(v) for k, v in respuestas.items() if k not in _SIN_SENAL
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

    # descartar(): la carrera abandonada y sus variantes salen del catálogo.
    sis = _C("Ingeniería en Sistemas", "software programación")
    sis2 = _C("Ingeniería en Ciencias y Sistemas", "software algoritmos")
    civil = _C("Ingeniería Civil", "obra estructuras concreto")
    resto = [_C(f"Otra {i}", "texto neutro") for i in range(20)]
    quedan = descartar([sis, sis2, civil, *resto], "Ingeniería en Sistemas")
    assert sis not in quedan and sis2 not in quedan, "debe sacar la carrera y su variante"
    assert civil in quedan, "no debe llevarse otra ingeniería que no comparte 2 palabras"

    assert descartar([sis, civil], None) == [sis, civil]  # sin dato, no toca nada
    assert descartar([sis, civil], "de la en") == [sis, civil]  # solo stopwords

    # Red de seguridad: un texto que se llevaría medio catálogo no descarta nada.
    muchas = [_C(f"Ingeniería en Sistemas {i}", "x") for i in range(10)]
    assert descartar(muchas, "Ingeniería en Sistemas") == muchas

    # El grado no arrastra el recorte: "universidad" no debe pesar como interés.
    con_grado = {"grado": "Estoy estudiando en la universidad", "gustos": "tecnología y programación"}
    assert preseleccionar(con_grado, [lejana, *otras, afin], top=5)[0] is afin

    # El nombre no pesa ni cambia el recorte: dos alumnos con los mismos gustos
    # deben producir EXACTAMENTE las mismas candidatas, o el caché no se reusa.
    # El nombre lleva palabras que solapan con un perfil ("Justicia Comunidad"
    # con Trabajo Social): sin la exclusión eso reordena el top y le da a cada
    # alumno un hash propio.
    base = {"gustos": "tecnología y programación"}
    cat = [lejana, *otras, afin]
    ana = preseleccionar({**base, "nombre": "Ana Justicia Comunidad"}, cat, top=3)
    luis = preseleccionar({**base, "nombre": "Luis"}, cat, top=3)
    assert ana == luis, "el nombre no debe mover el recorte (rompe el caché)"

    # <= top: no filtra nada, aunque el puntaje sea 0 para todas.
    pocas = [lejana, afin]
    assert preseleccionar(respuestas, pocas, top=5) == pocas

    # sin señal en las respuestas (todo stopwords/vacío): recorta sin romper.
    sin_senal = preseleccionar({"departamento": "Quetzaltenango"}, [lejana, *otras, afin], top=3)
    assert len(sin_senal) == 3

    print("ok")
