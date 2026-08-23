"""A/B del banco de opciones, juzgado por COHERENCIA y no por acierto.

## Por qué este experimento no se parece a los otros

Los A/B anteriores de este repo puntúan con `claves`: se define de antemano qué
carrera "debería" salir y se cuenta si el top-1 la contiene. Para medir un banco
de opciones nuevo ese diseño está roto, y vale la pena decir por qué:

1. El perfil del alumno simulado se escribe para llevar a la carrera objetivo,
   así que las respuestas ya vienen elegidas para que ese resultado gane.
2. Si el brazo nuevo propone una carrera **distinta pero igual de sensata**, la
   métrica la cuenta como fallo. El brazo nuevo solo puede empatar o perder.

O sea que el banco viejo gana por construcción. La pregunta correcta no es
"¿acertó la carrera que yo tenía en mente?" sino **"¿la recomendación tiene
lógica para esta persona?"**.

## Diseño

- **Personas, no objetivos.** Cada perfil describe a alguien (su vida, lo que
  disfruta, cómo es) y NO nombra ninguna carrera ni dice cuál debería salir.
  Tampoco menciona etiquetas del banco: el alumno simulado elige las opciones
  que le calzan, de la lista que le toque a su brazo.
- **Brazo A:** banco viejo (15 chips en `gustos`, etiquetas anteriores).
- **Brazo B:** banco nuevo (25 chips), tal como está hoy en
  `frontend/src/preguntas-fijas.js`. Se lee del JS, no de una copia.
- Lo único que cambia entre brazos son las opciones que se le ofrecen. El resto
  del flujo es idéntico.

## Cómo se juzga

**Un juez ciego.** Recibe la descripción de la persona y las dos
recomendaciones sin saber cuál es cuál (el orden se sortea por perfil, y las
etiquetas de brazo se borran). Da, para cada una, una nota de coherencia de 1 a
5 con su justificación, y dice cuál le calza mejor a esa persona o si empatan.

**Y el material crudo.** Lo que más vale de esta corrida no es el marcador: es
el archivo con las dos recomendaciones lado a lado para leerlas. El juez es una
segunda opinión, no el veredicto.

## Limitaciones, dichas de frente

- **El juez es el mismo modelo que recomienda.** Circularidad real. Se mitiga
  con el ciego y con el sorteo de orden, no se elimina. Por eso la salida está
  pensada para leerse a mano.
- **n chico.** El A/B del filtro midió que 3 de 8 perfiles cambian de resultado
  solos entre corridas. Con esta n, una diferencia de uno o dos casos no se
  puede leer como señal.
- Un juez que puntúa coherencia tiende a encontrarle sentido a casi cualquier
  recomendación. Las notas van a salir altas las dos; lo informativo es la
  comparación y el texto, no el valor absoluto.

## Uso

    uv run python experimento_banco.py --self-check   # sin red
    uv run python experimento_banco.py                # el A/B (gasta cuota)
"""

import argparse
import json
import os
import random
import time

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import preguntas, recomendar  # noqa: E402
from cobertura_banco import banco as banco_nuevo  # noqa: E402
from experimento_filtro import _solo_etiquetas, _top  # noqa: E402
from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    _responder,
    _texto_pregunta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_banco_resultados.json")
LECTURA = os.path.join(DATA, "tests", "experimento_banco_para_leer.md")

TOPE_USD = 0.15  # lo que queda del presupuesto autorizado

# --- Banco VIEJO (brazo A), recuperado del commit 38c8df7 -----------------
BANCO_VIEJO = {
    "impacto": [
        "Ayudar, enseñar o cuidar a las personas",
        "Defender la justicia y resolver conflictos",
        "Liderar, organizar negocios o usar tecnología y números",
        "Trabajar con la naturaleza, el campo o el ambiente",
        "Comunicar, crear, diseñar o investigar la realidad",
        "Construir, diseñar o hacer que las cosas funcionen"],
    "estilo": [
        "Con personas, en trato directo",
        "Analizando datos, ideas y lógica",
        "De forma práctica, con las manos",
        "Al aire libre y en movimiento"],
    "entorno": [
        "En una oficina o empresa",
        "En un hospital, clínica o consultorio",
        "Al aire libre, en el campo o la naturaleza",
        "En un laboratorio o taller técnico",
        "En un aula o centro educativo",
        "En una obra, con máquinas o herramientas",
        "En medios, un estudio creativo o diseñando",
        "Con la comunidad, ayudando a personas"],
    "gustos": [
        "Matemáticas y números", "Tecnología y computación",
        "Salud y cuidar personas", "Biología y naturaleza",
        "Química y laboratorio", "Leyes, justicia y debate",
        "Negocios, dinero y emprender", "Arte, diseño y creatividad",
        "Comunicación, escritura y medios", "Enseñar y educar",
        "Psicología y comportamiento", "Medio ambiente y agricultura",
        "Construcción, máquinas y cómo funcionan las cosas",
        "Gastronomía, turismo y hotelería", "Historia, sociedad y cultura"],
}

TEXTOS = {
    "impacto": "¿Qué tipo de impacto te gustaría tener en el mundo? (puedes elegir varios)",
    "estilo": "¿Cómo prefieres trabajar? (puedes elegir varias)",
    "entorno": "¿Dónde te imaginas trabajando? (puedes elegir varios)",
    "gustos": "¿Qué temas te apasionan? Elige los que quieras (o agrega el tuyo).",
}
ORDEN = ("impacto", "estilo", "entorno", "gustos")


# --- Las personas ---------------------------------------------------------
#
# Se describen como personas: su vida, lo que disfrutan, cómo son. NINGUNA dice
# qué carrera debería salir, y ninguna usa las palabras de las etiquetas del
# banco. Si alguien las lee y ya sabe qué "tiene que" salir, el perfil está mal
# escrito para este experimento.

PERSONAS = [
    {
        "nombre": "Wendy",
        "contexto": (
            "17 anios, quinto bachillerato en un instituto de Quetzaltenango. Toca "
            "la marimba en el grupo del colegio desde los 12 y ahora tambien "
            "guitarra; se junta los sabados con unos amigos a ensayar. Es la que "
            "organiza los ensayos y la que se pelea para que todos lleguen a "
            "tiempo. Le va bien en clase sin esforzarse mucho, pero se aburre "
            "rapido de lo que es puro memorizar. Le gusta ensenarle a los mas "
            "chiquitos del grupo."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
    {
        "nombre": "Elmer",
        "contexto": (
            "19 anios, termino el diversificado hace un anio y esta trabajando en "
            "la tienda de su mama mientras decide. Le arregla el celular y la "
            "compu a medio barrio, aprendio viendo videos. Le fascina abrir las "
            "cosas y ver que tienen adentro. En su aldea la senial es pesima y el "
            "se subio al techo a mover la antena hasta que agarro. Es callado, "
            "prefiere resolver solo antes que pedir ayuda."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
    {
        "nombre": "Rosa",
        "contexto": (
            "18 anios, bachillerato en ciencias y letras. Su abuela estuvo enferma "
            "dos anios y ella fue quien la baniaba, le daba sus pastillas y la "
            "llevaba a las citas. Se dio cuenta de que no le da impresion nada y "
            "que la gente se calma cuando ella habla. En el hospital le llamaron "
            "la atencion las maquinas grandes y le pregunto al tecnico como "
            "funcionaban. No le gusta estar sentada todo el dia."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
    {
        "nombre": "Kevin",
        "contexto": (
            "18 anios, recien graduado de perito contador. Lo que de verdad le "
            "quita el sueino es entender por que su aldea sigue igual de pobre que "
            "cuando el era ninio, mientras la cabecera crece. Lee todo lo que "
            "encuentra sobre eso y discute con quien sea. Es bueno con los numeros "
            "y le gusta hacer cuadros y graficas para explicar sus argumentos. Le "
            "aburre soberanamente la idea de llevar la contabilidad de una tienda."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
    {
        "nombre": "Ixchel",
        "contexto": (
            "20 anios, termino magisterio. Habla k'iche' con su familia y espanol "
            "en el pueblo, y aprendio ingles sola con series y hablando con "
            "turistas en el parque. Da clases particulares a ninios del barrio y le "
            "encanta el momento en que a alguien 'le cae el veinte'. Le duele que "
            "sus primos mas chiquitos ya no quieran hablar k'iche'. Es paciente y "
            "no se enoja cuando alguien se equivoca."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
    {
        "nombre": "Diego",
        "contexto": (
            "17 anios, quinto bachillerato. Juega futbol en una liga del municipio "
            "y se rompio la rodilla el anio pasado; paso seis meses yendo a "
            "terapia y le fascino todo lo que le hacian para volver a caminar bien. "
            "Le gusta el cuerpo humano y como se recupera. Es sociable, siempre "
            "anda con gente, y no se imagina metido en una oficina. Tiene dos "
            "perros y los cuida el."),
        "guion": (
            "Habla de tu vida como es. No nombres carreras ni digas que quieres "
            "estudiar algo especifico."),
    },
]


# --- El juez ciego --------------------------------------------------------

class Juicio(BaseModel):
    coherencia_1: int          # 1-5
    porque_1: str
    coherencia_2: int          # 1-5
    porque_2: str
    mejor: str                 # "1" | "2" | "empate"
    porque_mejor: str


SYSTEM_JUEZ = (
    "Eres un orientador vocacional con experiencia evaluando el trabajo de otros "
    "orientadores. Te dan la descripción de un estudiante y DOS listas de carreras "
    "recomendadas para él, hechas por dos orientadores distintos.\n\n"
    "Tu tarea NO es adivinar qué carrera 'debería' salir. Es juzgar, para cada "
    "lista, qué tan COHERENTE es con la persona descrita: ¿se explica a partir de "
    "lo que esa persona disfruta, de cómo es y de lo que se le da bien? ¿O hay "
    "carreras que aparecen sin que nada en la descripción las sostenga?\n\n"
    "Reglas:\n"
    "- Dos listas distintas pueden ser AMBAS coherentes. Si es así, dilo y pon "
    "'empate' en 'mejor'. No inventes una diferencia que no existe.\n"
    "- Una lista es MÁS coherente si recoge más facetas de la persona, o si evita "
    "carreras que contradicen algo que la persona dijo.\n"
    "- No premies que una lista sea más específica o más larga por sí sola.\n"
    "- 'coherencia_1' y 'coherencia_2': entero de 1 (no se explica con el perfil) "
    "a 5 (cada carrera se explica sola leyendo el perfil).\n"
    "- 'porque_1' y 'porque_2': 2 o 3 frases, citando lo concreto del perfil que "
    "sostiene o no sostiene la lista.\n"
    "- 'mejor': exactamente '1', '2' o 'empate'.\n"
    "- Español. No menciones que eres una IA."
)


def _juzgar(persona, lista_1, lista_2):
    def fmt(lista):
        return "\n".join(f"  {i}. {c['carrera']} ({c['afinidad']}%)"
                         for i, c in enumerate(lista, 1))
    resp = recomendar.generar(
        model=recomendar.MODELO,
        system=SYSTEM_JUEZ,
        catalogo="",
        variable=(f"ESTUDIANTE:\n{persona['contexto']}\n\n"
                  f"LISTA 1:\n{fmt(lista_1)}\n\n"
                  f"LISTA 2:\n{fmt(lista_2)}"),
        schema=Juicio,
        temperature=0.2,
    )
    return Juicio.model_validate_json(recomendar._texto_seguro(resp))


# --- Una sesión -----------------------------------------------------------

def _sesion(persona, cat, banco, etiqueta):
    respuestas = {"nombre": persona["nombre"], "departamento": DEPARTAMENTO}
    log = {"brazo": etiqueta, "persona": persona["nombre"], "fijas": {}, "adaptativas": []}

    for clave in ORDEN:
        opciones = banco[clave]
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(persona, f"{TEXTOS[clave]}\nOpciones: {' / '.join(opciones)}", previo)
        elegidas = _solo_etiquetas(r, opciones)
        respuestas[clave] = elegidas
        log["fijas"][clave] = elegidas
        print(f"    [{etiqueta}:{clave}] {elegidas[:95]}")

    sid = f"banco-{etiqueta}-{persona['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    for _ in range(preguntas.MAX_ADAPTATIVAS):
        paso, _uso = preguntas.siguiente_pregunta(respuestas, cat, sid)
        if paso.terminado:
            break
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(persona, _texto_pregunta(paso), previo)
        respuestas[paso.pregunta_texto] = r
        log["adaptativas"].append({"pregunta": paso.pregunta_texto, "respuesta": r})

    res, _uso = recomendar.recomendar(respuestas, cat)
    log["top3"] = _top(res, 3)
    return log


def _gastado():
    if not recomendar._GASTO:
        return 0.0
    t = {k: sum(g[k] for g in recomendar._GASTO.values())
         for k in ("llamadas", "prompt_tokens", "output_tokens", "cached_tokens")}
    return recomendar.costo_usd(t)


def correr():
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    nuevo = banco_nuevo()
    assert len(nuevo["gustos"]) > len(BANCO_VIEJO["gustos"]), \
        "el banco nuevo debe tener más chips que el viejo; ¿se revirtió el JS?"

    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {r["persona"]: r for r in json.load(open(SALIDA, encoding="utf-8"))["casos"]}
        print(f"Reanudando: {len(hechos)} personas ya hechas")

    casos = list(hechos.values())
    rnd = random.Random(20260823)
    for p in PERSONAS:
        if p["nombre"] in hechos:
            continue
        if _gastado() >= TOPE_USD:
            print(f"!! tope de ${TOPE_USD} alcanzado, se detiene en {p['nombre']}")
            break
        print(f"\n=== {p['nombre']} ===")
        t0 = time.perf_counter()
        a = _sesion(p, cat, BANCO_VIEJO, "A")
        b = _sesion(p, cat, nuevo, "B")

        # Ciego: se sortea quién es la Lista 1 y el juez nunca ve las etiquetas.
        primero_es_a = rnd.random() < 0.5
        l1, l2 = (a["top3"], b["top3"]) if primero_es_a else (b["top3"], a["top3"])
        j = _juzgar(p, l1, l2)
        gano = ("empate" if j.mejor == "empate"
                else ("A" if (j.mejor == "1") == primero_es_a else "B"))

        caso = {"persona": p["nombre"], "contexto": p["contexto"],
                "A": a, "B": b, "primero_es_a": primero_es_a,
                "juicio": j.model_dump(), "gano": gano,
                "coherencia_A": j.coherencia_1 if primero_es_a else j.coherencia_2,
                "coherencia_B": j.coherencia_2 if primero_es_a else j.coherencia_1,
                "segundos": round(time.perf_counter() - t0, 1)}
        casos.append(caso)
        json.dump({"casos": casos}, open(SALIDA, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"    A: {a['top3'][0]['carrera']}")
        print(f"    B: {b['top3'][0]['carrera']}")
        print(f"    juez (ciego): {gano}   coherencia A={caso['coherencia_A']} "
              f"B={caso['coherencia_B']}   gastado ${_gastado():.4f}")

    _reporte(casos)
    return casos


def _reporte(casos):
    print("\n" + "=" * 76)
    print("A/B DEL BANCO DE OPCIONES, JUZGADO POR COHERENCIA")
    print("=" * 76)
    if not casos:
        print("sin casos")
        return
    for c in casos:
        print(f"\n{c['persona']}")
        print(f"   A (banco viejo): {', '.join(x['carrera'] for x in c['A']['top3'])}")
        print(f"   B (banco nuevo): {', '.join(x['carrera'] for x in c['B']['top3'])}")
        print(f"   juez: {c['gano']}  (coherencia A={c['coherencia_A']} B={c['coherencia_B']})")
    n = len(casos)
    gana_a = sum(1 for c in casos if c["gano"] == "A")
    gana_b = sum(1 for c in casos if c["gano"] == "B")
    emp = sum(1 for c in casos if c["gano"] == "empate")
    print(f"\n   Juez ciego: A {gana_a}   B {gana_b}   empate {emp}   (de {n})")
    print(f"   Coherencia media: A {sum(c['coherencia_A'] for c in casos) / n:.2f}   "
          f"B {sum(c['coherencia_B'] for c in casos) / n:.2f}")
    distinto = sum(1 for c in casos if c["A"]["top3"][0]["carrera"] != c["B"]["top3"][0]["carrera"])
    print(f"   Top-1 distinto entre brazos: {distinto}/{n}")
    _escribir_lectura(casos)
    print(recomendar.resumen_gasto())
    print(f"\nGastado: ${_gastado():.4f} de ${TOPE_USD}")
    print(f"Para leer a mano: {LECTURA}")


def _escribir_lectura(casos):
    """El entregable de verdad: las dos recomendaciones lado a lado, para leerlas."""
    L = ["# A/B del banco de opciones, para leer a mano", "",
         "El juez ciego es una segunda opinión, no el veredicto. Lo que decide es",
         "si al leer esto la recomendación tiene lógica para la persona descrita.", ""]
    for c in casos:
        L += [f"## {c['persona']}", "", c["contexto"], "",
              "### Lo que marcó en las preguntas fijas", "",
              "| | A (banco viejo) | B (banco nuevo) |", "|---|---|---|"]
        for k in ORDEN:
            L.append(f"| {k} | {c['A']['fijas'].get(k, '')} | {c['B']['fijas'].get(k, '')} |")
        L += ["", "### Recomendación", "",
              "| # | A (banco viejo) | B (banco nuevo) |", "|---|---|---|"]
        for i in range(3):
            a = c["A"]["top3"][i] if i < len(c["A"]["top3"]) else {"carrera": "", "afinidad": ""}
            b = c["B"]["top3"][i] if i < len(c["B"]["top3"]) else {"carrera": "", "afinidad": ""}
            L.append(f"| {i + 1} | {a['carrera']} ({a['afinidad']}%) | {b['carrera']} ({b['afinidad']}%) |")
        j = c["juicio"]
        pa, pb = ((j["porque_1"], j["porque_2"]) if c["primero_es_a"]
                  else (j["porque_2"], j["porque_1"]))
        L += ["", f"**Juez ciego:** gana {c['gano']} · coherencia A={c['coherencia_A']} "
                  f"B={c['coherencia_B']}", "",
              f"- Sobre A: {pa}", f"- Sobre B: {pb}",
              f"- Comparación: {j['porque_mejor']}", ""]
    open(LECTURA, "w", encoding="utf-8").write("\n".join(L))


def _self_check():
    nuevo = banco_nuevo()
    assert len(nuevo["gustos"]) == 25 and len(BANCO_VIEJO["gustos"]) == 15
    # Los dos bancos deben diferir SOLO en las opciones, no en las preguntas.
    assert set(BANCO_VIEJO) == set(nuevo) == set(ORDEN)
    # Ninguna persona nombra una carrera ni una etiqueta del banco: si lo hiciera,
    # estaría dirigiendo el resultado y volveríamos al diseño que se critica.
    pistas = ["ingenier", "licenciatur", "profesorado", "medicina", "carrera de",
              "quiero estudiar", "quiere estudiar"]
    for p in PERSONAS:
        bajo = p["contexto"].lower()
        for x in pistas:
            assert x not in bajo, f"{p['nombre']} nombra una carrera: '{x}'"
        for etq in nuevo["gustos"] + BANCO_VIEJO["gustos"]:
            assert etq.lower() not in bajo, f"{p['nombre']} repite la etiqueta '{etq}'"
    # El desciframiento del ciego: si A fue primero y el juez dice "1", gana A.
    for primero_es_a, mejor, esperado in [(True, "1", "A"), (True, "2", "B"),
                                          (False, "1", "B"), (False, "2", "A")]:
        assert ("A" if (mejor == "1") == primero_es_a else "B") == esperado
    assert _gastado() == 0.0
    print(f"ok: {len(PERSONAS)} personas, ninguna dirige el resultado")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    _self_check() if a.self_check else correr()
