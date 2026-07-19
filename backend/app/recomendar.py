"""Motor de recomendación: le pasa el perfil del estudiante y el catálogo de
carreras a Gemini, y devuelve un análisis de afinidad por carrera (agrupando
las universidades que ofrecen la misma carrera)."""

import hashlib
import os
import random
import time

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

# Dos modelos (híbrido):
# - MODELO: preguntas del chat (alto volumen, hasta 8 por test) → prioriza cuota.
# - MODELO_FINAL: resultados que el alumno LEE (análisis final, simulador,
#   comparador; 1 llamada c/u) → prioriza calidad de tono, aunque gaste más cuota.
# Ambos configurables por .env.
MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MODELO_FINAL = os.getenv("GEMINI_MODEL_FINAL", "gemini-2.5-flash")

# Tono compartido por todos los prompts: el lector es un adolescente, no un
# adulto. Se añade al final de cada SYSTEM (recomendar, preguntas, extras).
TONO = (
    "A QUIÉN LE ESCRIBES (muy importante): el lector es un estudiante de 13 a 17 "
    "años. Escribe como si le hablaras a un amigo de secundaria: SENCILLO, cálido "
    "y directo, nunca como un documento formal. Frases cortas. Nivel de lectura "
    "básico.\n"
    "Prefiere siempre la palabra del día a día en vez de la palabra 'de adulto'. "
    "Por ejemplo, di: 'te imaginas' (no 'te visualizas'); 'lo que te gusta' (no "
    "'tu enfoque'); 'hablar con la gente' (no 'la interacción'); 'organizar' (no "
    "'gestionar'); 'mejorar' (no 'optimizar'); 'área' o 'mundo' (no 'ámbito'); "
    "'lo que sabes hacer' (no 'competencias'); 'los temas de clase' (no 'el "
    "currículo'). Evita palabras rebuscadas como 'idóneo', 'índole', 'holístico', "
    "'aunar'. Si de verdad necesitas un término técnico, explícalo en pocas "
    "palabras. Motivador y cercano, nada acartonado."
)

SYSTEM = (
    "Eres un orientador vocacional. Analiza el perfil del estudiante contra TODO "
    "el catálogo de carreras y produce un análisis de afinidad.\n\n"
    "Reglas:\n"
    "- AGRUPA SOLO carreras que son EL MISMO programa (mismo nombre esencial y "
    "mismo nivel) ofrecido por varios centros: p. ej. 'Derecho / Ciencias "
    "Jurídicas' en varias universidades = UN grupo con varias instituciones.\n"
    "- NO fusiones programas DISTINTOS aunque el tema sea parecido. Ejemplos que "
    "van SEPARADOS: una 'Ingeniería en Ciencias y Sistemas' y una 'Licenciatura en "
    "Administración de Sistemas Informáticos' (distinto nivel y enfoque); "
    "especialidades distintas (Psicología Clínica ≠ Industrial ≠ Educativa); "
    "niveles distintos (Ingeniería ≠ Licenciatura ≠ Profesorado ≠ PEM). Ante la "
    "duda, SEPÁRALAS.\n"
    "- El nombre de cada grupo debe reflejar FIELMENTE lo que ofrecen ESAS sedes; "
    "NO inventes un nombre que renombre o disfrace el programa real de una sede. "
    "Cada institución que listes bajo un grupo debe ofrecer DE VERDAD esa carrera "
    "con ese nombre en el catálogo.\n"
    "- Asigna a cada carrera un porcentaje de afinidad ENTERO. Los porcentajes de "
    "TODAS las carreras deben sumar exactamente 100.\n"
    "- Incluye únicamente las carreras con afinidad mayor a 1. Ordena de mayor a "
    "menor afinidad.\n"
    "- 'descripcion': explicación general (2-3 frases) de por qué la carrera encaja "
    "con el perfil, válida para todas las instituciones que la ofrecen; NO menciones "
    "una universidad concreta aquí.\n"
    "- 'razones': 3 a 5 frases MUY cortas, tipo checklist, de por qué esta carrera "
    "encaja con ESTE estudiante, conectando con sus respuestas (p. ej. 'Disfrutas "
    "resolver problemas', 'Te gustan las matemáticas'). Sin viñetas ni emojis.\n"
    "- 'factores': 3 a 5 dimensiones del perfil que MÁS influyeron en esta "
    "recomendación, cada una con 'nombre' corto (p. ej. 'Pensamiento lógico', "
    "'Trato con personas') y 'peso' entero 0-100 (cuánto pesó para esta carrera). "
    "No tienen que sumar 100.\n"
    "- Por cada institución indica universidad, centro y departamento (tal como "
    "aparecen en el catálogo) y su 'enfoque': qué distingue a ESE centro para esa "
    "carrera (su sello o énfasis particular), en 1-2 frases.\n"
    "- 'confianza': entero 0-100 que refleja qué tan segura es la recomendación en "
    "conjunto. Alta (80-100) si el perfil apunta claramente a un área; media "
    "(50-79) si hay un par de áreas compitiendo; baja (<50) si las respuestas son "
    "escasas, ambiguas o dispersas entre muchas áreas distintas.\n"
    "- 'confianza_nota': 1 frase corta explicando esa confianza en términos del "
    "perfil (p. ej. 'Tus respuestas apuntan de forma consistente a un mismo área' "
    "o 'Todavía hay algo de ambigüedad entre dos áreas distintas').\n"
    "- Escribe en español, cercano y claro.\n\n"
    + TONO
)


class Institucion(BaseModel):
    universidad: str
    centro: str
    departamento: str
    enfoque: str


class Factor(BaseModel):
    nombre: str
    peso: int  # 0-100: cuánto influyó esa dimensión


class CarreraRecomendada(BaseModel):
    carrera: str
    afinidad: int
    descripcion: str
    razones: list[str]
    factores: list[Factor]
    instituciones: list[Institucion]


class Resultado(BaseModel):
    carreras: list[CarreraRecomendada]
    confianza: int
    confianza_nota: str


def hay_api_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def uso_tokens(resp, modelo: str) -> dict:
    """Extrae el consumo de tokens de una respuesta de Gemini (usage_metadata).
    Devuelve un dict listo para registrar en la tabla uso_tokens."""
    u = getattr(resp, "usage_metadata", None)
    return {
        "modelo": modelo,
        "prompt_tokens": getattr(u, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(u, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(u, "total_token_count", 0) or 0,
    }


def _catalogo_texto(carreras) -> str:
    """Carreras de una sola sede: un bloque con su perfil completo (igual que
    antes). Carreras que varias sedes ofrecen (mismo perfil_grupo, p. ej. las 5
    sedes de Ciencias Jurídicas) comparten el MISMO perfil base -> se manda UNA
    sola vez, seguido de la lista de sedes con su 'sello' (lo que sí las
    distingue). Evita repetir el mismo banco de palabras N veces en el prompt."""
    grupos: dict[str, list] = {}
    sueltas = []
    for c in carreras:
        if c.perfil_grupo:
            grupos.setdefault(c.perfil_grupo, []).append(c)
        else:
            sueltas.append(c)

    partes = [
        f"### {c.nombre} ({c.universidad} - {c.centro} - {c.departamento})\n{c.perfil}"
        for c in sueltas
    ]
    for sedes in grupos.values():
        sedes_txt = "\n".join(
            f"  - {c.nombre} ({c.universidad} - {c.centro} - {c.departamento})"
            + (f": {c.sello}" if c.sello else "")
            for c in sedes
        )
        partes.append(f"### {sedes[0].nombre}\n{sedes[0].perfil}\nSEDES QUE LA OFRECEN:\n{sedes_txt}")
    return "\n\n".join(partes)


# --- Context caching de Gemini ---
# El catálogo (~24k tokens de entrada) es idéntico en TODAS las llamadas y es el
# ~97% del costo. Lo metemos en un CachedContent reutilizable: se paga una vez a
# tarifa normal y las siguientes llamadas lo pagan ~a 1/4. Solo el perfil/historial
# del alumno viaja en fresco.
#
# La clave es un hash de (modelo, system, catálogo): distinto system (recomendar vs
# preguntas) o distinto filtro de departamento → caché distinto, automáticamente. Si
# cambias el catálogo (reseed), el hash cambia y se crea uno nuevo solo; el viejo
# expira por TTL. Por eso NO hace falta crearlo al arrancar ni tocar seed_carreras.py.
#
# OJO (verificado 2026-07): el TIER GRATIS de Gemini tiene el almacenamiento de caché
# en 0 (429 "TotalCachedContentStorageTokensPerModelFreeTier limit=0"), así que
# caches.create SIEMPRE falla y todo cae a inline (la app no se rompe, pero no ahorra).
# Se activa solo con billing habilitado (plan de pago). En DeepSeek el ahorro es
# automático por prefijo y no necesita esto.
_caches: dict[tuple[str, str], str | None] = {}  # clave -> cache.name (None = no cacheable)


def _clave_cache(model: str, system: str, catalogo: str) -> tuple[str, str]:
    h = hashlib.sha256(f"{system}\x00{catalogo}".encode()).hexdigest()
    return (model, h)


def _get_cache(client, model: str, system: str, catalogo: str) -> str | None:
    """name de un CachedContent para (model, system, catalogo), creado la 1ª vez y
    reusado. None si Gemini no lo puede cachear (p. ej. catálogo bajo el mínimo de
    tokens) → el llamador manda todo inline."""
    clave = _clave_cache(model, system, catalogo)
    if clave in _caches:
        return _caches[clave]
    try:
        cache = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                system_instruction=system,
                contents=[catalogo],
                ttl="3600s",  # 1h; se recrea solo al expirar (ver generar())
            ),
        )
        _caches[clave] = cache.name
    except errors.APIError:
        _caches[clave] = None  # memoriza el fallo: no reintentar en cada llamada
    return _caches[clave]


# Códigos que ameritan reintentar (límite de cuota / servicio saturado). Todo lo
# demás (400 mal pedido, 404, etc.) es un error real: se propaga de inmediato.
_CODIGOS_REINTENTABLES = {429, 500, 503}


def _con_reintento(fn, intentos=4):
    """Llama fn() con backoff exponencial + jitter si Gemini responde 429/503
    (cuota/RPM excedido o servicio saturado). Reintenta hasta `intentos` veces;
    al agotarlos, deja que el último error se propague tal cual."""
    for intento in range(intentos):
        try:
            return fn()
        except errors.APIError as e:
            if e.code not in _CODIGOS_REINTENTABLES or intento == intentos - 1:
                raise
            espera = (2**intento) + random.uniform(0, 1)
            time.sleep(espera)


def generar(client, model, system, catalogo, variable, schema, temperature):
    """Genera con el catálogo como contexto cacheado. Si el caché no está
    disponible (o expiró y falla dos veces), cae a mandar todo inline. Devuelve la
    respuesta cruda de Gemini (el llamador parsea .text y extrae uso_tokens).
    Los 429/503 (cuota agotada o servicio saturado) se reintentan con backoff."""
    for _ in range(2):
        name = _get_cache(client, model, system, catalogo)
        if name is None:
            break  # no cacheable → inline
        try:
            return _con_reintento(
                lambda: client.models.generate_content(
                    model=model,
                    contents=variable,
                    config=types.GenerateContentConfig(
                        cached_content=name,
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=temperature,
                    ),
                )
            )
        except errors.ClientError as e:
            if e.code == 404:
                # el caché pudo expirar por TTL → olvídalo y recréalo una vez
                _caches.pop(_clave_cache(model, system, catalogo), None)
                continue
            raise
    # inline: system + catálogo + variable en una sola llamada (como antes del caché)
    return _con_reintento(
        lambda: client.models.generate_content(
            model=model,
            contents=f"{catalogo}\n\n{variable}",
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
            ),
        )
    )


def recomendar(respuestas: dict, carreras) -> tuple[Resultado, dict]:
    """respuestas: dict con las respuestas del cuestionario.
    carreras: lista de models.Carrera (el catálogo).
    Devuelve (resultado, uso_tokens): las carreras afines (>1%) con su % y detalle
    más la confianza global, y el consumo de tokens de esta llamada."""
    perfil = "\n".join(f"- {k}: {v}" for k, v in respuestas.items())

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = generar(
        client,
        model=MODELO_FINAL,
        system=SYSTEM,
        catalogo=f"CATÁLOGO DE CARRERAS:\n{_catalogo_texto(carreras)}",
        variable=f"PERFIL DEL ESTUDIANTE:\n{perfil}",
        schema=Resultado,
        temperature=0.3,
    )
    return Resultado.model_validate_json(resp.text), uso_tokens(resp, MODELO_FINAL)


if __name__ == "__main__":
    # ponytail: self-check del parseo del catálogo, sin llamar a la API.
    class _C:
        def __init__(self, n, u, ce, d, p, grupo=None, sello=None):
            self.nombre, self.universidad, self.centro, self.departamento = n, u, ce, d
            self.perfil, self.perfil_grupo, self.sello = p, grupo, sello

    txt = _catalogo_texto([_C("Ing. Forestal", "USAC", "CUNTOTO", "Totonicapán", "ama el bosque")])
    assert "Ing. Forestal" in txt and "CUNTOTO" in txt and "bosque" in txt

    # self-check del agrupado: 2 sedes con el mismo perfil_grupo comparten el
    # perfil base UNA sola vez (no se duplica), y cada sede aporta su sello.
    agrupadas = [
        _C("Derecho A", "USAC", "CUNOC", "Quetzaltenango", "banco de palabras derecho", "derecho", "sello A"),
        _C("Derecho B", "UMG", "UMG Toto", "Totonicapán", "banco de palabras derecho", "derecho", "sello B"),
    ]
    txt2 = _catalogo_texto(agrupadas)
    assert txt2.count("banco de palabras derecho") == 1  # el perfil NO se repite
    assert "sello A" in txt2 and "sello B" in txt2 and "CUNOC" in txt2 and "UMG Toto" in txt2

    # self-check del caché: mismo (model, system, catálogo) → misma clave; distinto → distinta.
    k1 = _clave_cache("m", "sys", "cat")
    assert k1 == _clave_cache("m", "sys", "cat")
    assert k1 != _clave_cache("m", "sys", "cat2") != _clave_cache("m2", "sys", "cat")

    # self-check del backoff: 429/503 se reintentan hasta lograrlo o agotar intentos;
    # otros códigos (p. ej. 400) se propagan de inmediato, sin reintentar.
    llamadas = {"n": 0}

    def _falla_dos_veces():
        llamadas["n"] += 1
        if llamadas["n"] < 3:
            raise errors.ClientError(429, {"message": "rate limit"})
        return "ok"

    assert _con_reintento(_falla_dos_veces) == "ok"
    assert llamadas["n"] == 3

    def _error_no_reintentable():
        raise errors.ClientError(400, {"message": "bad request"})

    try:
        _con_reintento(_error_no_reintentable, intentos=4)
        assert False, "debía propagar el 400 sin reintentar"
    except errors.ClientError as e:
        assert e.code == 400

    print("ok")
