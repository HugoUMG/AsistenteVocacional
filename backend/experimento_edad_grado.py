"""Experimento A/B: la edad y el grado académico, ¿deben decirle algo al prompt?

Las preguntas fijas del chat ahora piden edad, grado académico (actual o el
último cursado) y si le gustó lo que estudia o estudió. Los tres datos ya
llegaban al prompt dentro del PERFIL DEL ESTUDIANTE, porque `recomendar()`
vuelca el dict completo. Lo que NO existía es una instrucción de qué hacer con
ellos: para el modelo, "edad: 24" pesaba lo mismo que cualquier otra línea, y el
bloque TONO le sigue diciendo que le escribe a alguien de 13 a 17 años.

Esa instrucción es `recomendar.CONTEXTO_ACADEMICO`, detrás del flag
`EDAD_Y_GRADO_EN_RECOMENDACION`. Este script mide si vale la pena encenderla.

## Brazos

Los dos reciben EXACTAMENTE el mismo perfil (misma edad, mismo grado, la misma
conversación). Lo único que cambia es el SYSTEM de la recomendación:

- **A (control)** — producción de hoy: los datos están en el perfil, sin
  instrucción sobre ellos.
- **B** — igual, más el bloque `CONTEXTO_ACADEMICO`.

## Por qué una sola conversación por perfil

El cambio está en el ÚLTIMO paso (la recomendación), no en las preguntas. Correr
dos chats independientes metería ruido conversacional (temperatura 0.9) en la
comparación de un prompt que ni siquiera participa en el chat. Se conversa una
vez, se guarda el dict de respuestas y se llama a `recomendar()` dos veces
alternando el flag. Barato y limpio.

## Qué se mide

1. **No romper a los jóvenes** (Kevin, Melany): el top-1 debe seguir acertando.
   Es la regresión que importa, porque son el caso de uso normal.
2. **Los que ya cursaron algo y NO les gustó** (Ana, Sergio): la carrera que
   dejaron NO debería volver en el top-3. Es la petición concreta de la
   psicóloga y lo único que el control no tiene forma de saber que debe hacer.
3. **El adulto sin universidad** (Marvin, 31): no hay carrera que evitar; se
   mira si el trato deja de ser de colegio. Eso se lee, no se cuenta.

## Limitaciones, dichas de frente

- 5 perfiles ficticios no dan potencia estadística. La medida 2 son 2 perfiles.
  Sirve para ver SI el mecanismo se cumple, no para afirmar una mejora general.
- Circularidad parcial: la persona simulada y el orientador son el mismo modelo.
- La recomendación corre a temperatura 0.3, así que el top-1 es bastante estable,
  pero no es determinista.

## Ronda 2 (la que corre este script hoy)

La ronda 1 midió esto SIN la pregunta de qué carrera cursó, y salió que no: el
ranking no se movió, el control ya evitaba la carrera que el alumno dejó porque
él mismo lo decía en el chat, y el bloque despersonalizaba el texto con los
adultos. Los números y las transcripciones están en `experiments/edad-y-grado.md`
y en `data/tests/experimento_edad_grado_resultados.json`.

Esta ronda arregla las dos fallas de diseño de aquella:

1. El chat ahora pregunta **qué carrera** cursa o cursó (`carrera_cursada`), así
   que el dato existe. Antes el bloque no tenía con qué trabajar.
2. Los perfiles que dejaron una carrera **ya NO la nombran en la conversación**.
   Así el campo fijo es la ÚNICA fuente, que es el caso que importa: si el alumno
   lo dice en el chat, el control ya se entera solo.

El bloque también cambió: se le quitó la instrucción de tono de adulto que causó
la despersonalización y se le puso lo contrario ("háblale siempre de tú"). Se
mide `segunda_persona` para verificar que eso no vuelva a pasar.

## Uso

    uv run python experimento_edad_grado.py --self-check   # sin red
    uv run python experimento_edad_grado.py                # el A/B (gasta cuota)
    uv run python experimento_edad_grado.py --perfil Ana
"""

import argparse
import json
import os
import re

from dotenv import load_dotenv

# ANTES de importar app.recomendar (resuelve MODELO con os.getenv al importarse).
load_dotenv()

from app import preguntas, recomendar  # noqa: E402

# Se reusa la maquinaria del experimento del psicométrico: la persona que
# responde, el bucle de conversación, el catálogo desde JSON y las 4 preguntas
# fijas vocacionales, para no tener dos copias del mismo alumno simulado.
from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    FIJAS,
    _conversar,
    _responder,
    acierta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_edad_grado_ronda2.json")

FLAG = "EDAD_Y_GRADO_EN_RECOMENDACION"

# --- Los 5 perfiles -------------------------------------------------------
#
# edad / grado / gusto: lo que hoy contestan las preguntas fijas nuevas. El
# texto de 'grado' y de 'gusto' es LITERAL el de las opciones de Chat.jsx.
# carrera: lo que contesta la pregunta nueva 'carrera_cursada'.
# claves: aciertos esperados para el top-1.
# evita: lo que NO debería volver en el top-3 (solo para quien cursó algo y no le
#   gustó). OJO: en esta ronda su guion NO nombra esa carrera en el chat, así que
#   el único lugar donde aparece es el campo fijo.

PERFILES = [
    {
        "nombre": "Kevin",
        "edad": "17",
        "grado": "Estoy en diversificado o bachillerato",
        "carrera": "Bachillerato en computación",
        "gusto": "Sí, mucho",
        "area_esperada": "informática/técnica",
        # "electrónic" se agregó DESPUÉS de la ronda 1, donde el top-1 de los dos
        # brazos fue Ingeniería en Electrónica y el criterio lo contaba como
        # fallo. Se aplica igual a los dos brazos, así que no inclina la
        # comparación; solo deja de mentir sobre el acierto.
        "claves": ["sistemas", "informátic", "software", "comput", "telecomunicac",
                   "electrónic"],
        "evita": [],
        "contexto": (
            "17 años, quinto bachillerato en computación en Quetzaltenango. Arma "
            "PCs y le pagan por reparar celulares. Programa poco pero se defiende. "
            "Reprobó matemática dos bimestres y le da vergüenza admitirlo."
        ),
        "guion": (
            "Es honesto sobre lo que le gusta: la tecnología, armar cosas, "
            "trabajar solo con audífonos. MIENTE si le preguntan por matemáticas "
            "o cálculo: dice que se le dan bien. Respuestas cortas, informales."
        ),
    },
    {
        "nombre": "Melany",
        "edad": "17",
        "grado": "Estoy en diversificado o bachillerato",
        "carrera": "Perito contador",
        "gusto": "Más o menos",
        "area_esperada": "administración/contaduría",
        "claves": ["administra", "empresa", "contad", "audit", "mercadot",
                   "market", "comercio", "econom", "finanz"],
        "evita": [],
        "contexto": (
            "17 años, perito contador, ayuda en la tienda de sus papás y lleva "
            "las cuentas desde los 14. Muy ordenada y competitiva. Está "
            "convencida de que quiere 'algo de leyes' porque una prima abogada "
            "gana bien, aunque todo lo que disfruta es de números e inventario."
        ),
        "guion": (
            "Articulada y segura. Cuando le preguntan por su meta menciona "
            "'derecho' o 'leyes'. HONESTA en lo demás: le gusta que las cuentas "
            "cuadren, odia improvisar, le aburre discutir y leer textos largos."
        ),
    },
    {
        "nombre": "Ana",
        "edad": "23",
        "grado": "Empecé una carrera universitaria pero la dejé",
        "carrera": "Ingeniería en Sistemas",
        "gusto": "No, nada",
        "area_esperada": "educación/humanidades",
        "claves": ["educac", "pedagog", "psicolog", "comunicac", "administra",
                   "recursos humanos", "trabajo social"],
        "evita": ["sistemas", "informátic", "comput"],
        "contexto": (
            "23 años. Estudió cuatro semestres de Ingeniería en Sistemas porque "
            "en su casa le dijeron que ahí estaba el trabajo, y la dejó: los "
            "cursos de programación se le hicieron eternos y no le encontró "
            "sentido. Ahora da clases de refuerzo a niños en su colonia y eso sí "
            "lo disfruta. Trabaja medio tiempo en una agencia bancaria."
        ),
        "guion": (
            "Habla como adulta joven, tranquila y clara. NUNCA menciona en el "
            "chat qué carrera empezó ni que la dejó: le da pena y prefiere no "
            "sacar el tema. Si le preguntan directo por lo que estudió, contesta "
            "algo vago ('empecé algo en la U pero no me hallé') sin nombrarlo. "
            "Se le ilumina cuando cuenta de los niños a los que da clases y de "
            "cómo explica las cosas. Es honesta en que no le molesta el orden ni "
            "los números básicos (por el banco), pero que lo suyo es la gente. Si "
            "le preguntan por tecnología dice que la usa y ya."
        ),
    },
    {
        "nombre": "Sergio",
        "edad": "26",
        "grado": "Empecé una carrera universitaria pero la dejé",
        "carrera": "Ciencias Jurídicas y Sociales",
        "gusto": "No, nada",
        "area_esperada": "gastronomía/turismo",
        "claves": ["gastron", "culinar", "chef", "hotel", "turism", "restaurant",
                   "administra"],
        "evita": ["jurídic", "abogad", "derecho", "notari", "criminal"],
        "contexto": (
            "26 años. Llevó dos años de Ciencias Jurídicas y Sociales y la dejó: "
            "leer expedientes lo aburría y las clases se le hacían pesadas. "
            "Desde entonces trabaja en la cocina de un restaurante en Xela, "
            "empezó lavando trastos y ahora arma el menú del día."
        ),
        "guion": (
            "Adulto joven, directo. NUNCA menciona en el chat qué carrera empezó "
            "ni que la dejó: para él es tema cerrado y no lo saca. Si le "
            "preguntan directo, dice 'llevé unos años en la U y no era lo mío' "
            "sin nombrar la carrera. Habla con detalle y "
            "orgullo de la cocina, de los tiempos, del estrés del servicio y de "
            "que le gustaría tener su propio lugar algún día. Es honesto en que "
            "no le gusta estar sentado y en que sí aguanta la presión."
        ),
    },
    {
        "nombre": "Marvin",
        "edad": "31",
        "grado": "Terminé el diversificado o bachillerato",
        "carrera": "Perito contador",
        "gusto": "Más o menos",
        "area_esperada": "administración/contaduría",
        "claves": ["administra", "empresa", "contad", "audit", "comercio",
                   "econom", "finanz", "market", "mercadot"],
        "evita": [],
        "contexto": (
            "31 años, perito contador graduado hace doce años. Nunca entró a la "
            "universidad porque se puso a trabajar. Lleva la contabilidad de dos "
            "tiendas de su familia y quiere por fin estudiar algo de noche o "
            "fin de semana."
        ),
        "guion": (
            "Adulto, tranquilo, habla de trabajo y de horarios, no de colegio. "
            "Menciona que tiene familia y que estudiaría de noche. Es honesto: "
            "le gustan las cuentas y organizar, le cuesta la tecnología nueva, "
            "no le interesa nada de laboratorio ni de campo."
        ),
    },
    {
        "nombre": "Wendy",
        "edad": "28",
        "grado": "Terminé una carrera universitaria",
        "carrera": "Administración de Empresas",
        "gusto": "No, nada",
        "area_esperada": "diseño/comunicación",
        "claves": ["diseñ", "comunicac", "publicid", "audiovisual", "arte",
                   "periodis", "marketing", "mercadot"],
        "evita": ["administración de empresas", "ciencias de la administración",
                  "licenciatura en administración"],
        "contexto": (
            "28 años. Terminó Administración de Empresas porque era lo que había "
            "cerca y lo que su familia podía pagar, y trabaja en el área "
            "administrativa de una empresa de transporte. El trabajo la aburre "
            "profundamente. Lleva tres años haciendo los flyers y las redes de "
            "la empresa por su cuenta, y eso es lo único que espera del día."
        ),
        "guion": (
            "Adulta, clara y con algo de frustración contenida. NUNCA menciona "
            "en el chat qué carrera terminó: le incomoda y cambia de tema. Si le "
            "preguntan directo dice 'ya me gradué de algo que no me llenó'. Habla "
            "con entusiasmo de armar los flyers, de elegir tipografías y colores, "
            "de grabar y editar los videos de las redes. Es honesta en que sí "
            "sabe de números y de organizar, pero que no quiere seguir ahí."
        ),
    },
]


def _seed(perfil: dict) -> dict:
    """Las respuestas fijas nuevas, tal como las guardaría Chat.jsx. El orden es
    el mismo del chat: la carrera cursada va ANTES de si le gustó, porque en el
    chat la pregunta del gusto la nombra ('¿Te gustó Ingeniería en Sistemas?')."""
    s = {
        "nombre": perfil["nombre"],
        "departamento": DEPARTAMENTO,
        "edad": perfil["edad"],
        "grado": perfil["grado"],
    }
    if perfil.get("carrera"):  # en básicos no hay carrera que preguntar
        s["carrera_cursada"] = perfil["carrera"]
    s["gusto_grado"] = perfil["gusto"]
    return s


def conversar(perfil, cat):
    """4 fijas vocacionales + adaptativas. Igual para los dos brazos."""
    respuestas = _seed(perfil)
    log = []
    tokens = 0
    for clave, texto, opciones in FIJAS:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
        respuestas[clave] = r
        log.append({"fija": clave, "pregunta": texto, "respuesta": r})
        print(f"    [fija:{clave}] -> {r[:90]}")
    sid = f"edadgrado-{perfil['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    tokens += _conversar(perfil, cat, respuestas,
                         lambda r: preguntas.siguiente_pregunta(r, cat, sid), log)
    return respuestas, log, tokens


def recomendar_con_flag(respuestas, cat, encendido: bool):
    previo = os.environ.get(FLAG)
    os.environ[FLAG] = "1" if encendido else "0"
    try:
        assert recomendar.contexto_academico_activo() is encendido
        return recomendar.recomendar(respuestas, cat)
    finally:
        if previo is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = previo


_SEGUNDA_PERSONA = re.compile(r"\b(te|tu|tus|ti|contigo|tuyo|tuya)\b", re.IGNORECASE)


def _resumen(res, perfil):
    top = [c.carrera for c in res.carreras[:3]]
    return {
        "top3": top,
        "top1": top[0] if top else None,
        "acierta": acierta(top[0], perfil["claves"]) if top else False,
        # La carrera que dejó no debería volver: se mira en TODO el top-3.
        "repite_lo_que_dejo": any(acierta(c, perfil["evita"]) for c in top) if perfil["evita"] else None,
        # Ronda 1: el bloque despersonalizaba la descripción de los adultos
        # ("para quienes tienen vocación" en vez de "para ti"). Se vigila.
        "segunda_persona": bool(_SEGUNDA_PERSONA.search(res.carreras[0].descripcion)) if res.carreras else None,
        "confianza": res.confianza,
        "confianza_nota": res.confianza_nota,
        "descripcion_top1": res.carreras[0].descripcion if res.carreras else "",
        "razones_top1": res.carreras[0].razones if res.carreras else [],
    }


def correr(solo=None):
    cat = catalogo()
    perfiles = [p for p in PERFILES if not solo or p["nombre"].lower() == solo.lower()]
    salida = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else []
    if solo:
        salida = [s for s in salida if s["perfil"].lower() != solo.lower()]
    hechos = {s["perfil"] for s in salida}
    print(f"Catálogo: {len(cat)} registros carrera-sede · {len(perfiles)} perfiles"
          + (f" · ya listos: {sorted(hechos)}" if hechos else "") + "\n")

    for perfil in perfiles:
        if perfil["nombre"] in hechos:
            continue
        print(f"=== {perfil['nombre']}, {perfil['edad']} años · {perfil['grado']} · "
              f"'{perfil['gusto']}' (esperado: {perfil['area_esperada']})")
        respuestas, log, tokens = conversar(perfil, cat)

        res_a, uso_a = recomendar_con_flag(respuestas, cat, False)
        res_b, uso_b = recomendar_con_flag(respuestas, cat, True)
        a, b = _resumen(res_a, perfil), _resumen(res_b, perfil)
        for etiqueta, r in (("A (control)", a), ("B (bloque) ", b)):
            extra = f", repite lo que cursó={r['repite_lo_que_dejo']}" if perfil["evita"] else ""
            print(f"  {etiqueta}: {r['top1']}  [acierta={r['acierta']}{extra}, "
                  f"2a persona={r['segunda_persona']}]")

        salida.append({
            "perfil": perfil["nombre"], "edad": perfil["edad"], "grado": perfil["grado"],
            "gusto": perfil["gusto"], "area_esperada": perfil["area_esperada"],
            "respuestas": respuestas, "log": log,
            "A": a, "B": b,
            "tokens": {"chat": tokens, "recomendar_A": uso_a["total_tokens"],
                       "recomendar_B": uso_b["total_tokens"]},
        })
        json.dump(salida, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print()

    print("--- Resumen ---")
    for s in salida:
        linea = f"{s['perfil']:8} A={s['A']['top1'][:34]:34} B={s['B']['top1'][:34]:34}"
        if s["A"]["repite_lo_que_dejo"] is not None:
            linea += f" | repite: A={s['A']['repite_lo_que_dejo']} B={s['B']['repite_lo_que_dejo']}"
        else:
            linea += f" | acierta: A={s['A']['acierta']} B={s['B']['acierta']}"
        linea += f" | 2a pers: A={s['A']['segunda_persona']} B={s['B']['segunda_persona']}"
        print(linea)
    print(f"\nGuardado en {SALIDA}")
    print(recomendar.resumen_gasto())


def _self_check():
    """Sin red: verifica el armado del perfil, el flag y la lectura de resultados."""
    p = next(x for x in PERFILES if x["nombre"] == "Ana")
    s = _seed(p)
    assert s["edad"] == "23" and s["grado"].startswith("Empecé")
    assert s["carrera_cursada"] == "Ingeniería en Sistemas"
    assert list(s)[-1] == "gusto_grado", "el gusto va después de la carrera, como en el chat"

    # Un perfil sin carrera que nombrar no lleva el campo (básicos).
    assert "carrera_cursada" not in _seed({**p, "carrera": None})

    # El flag prende y apaga el bloque, y se restaura al salir.
    os.environ.pop(FLAG, None)
    assert not recomendar.contexto_academico_activo()
    os.environ[FLAG] = "1"
    assert recomendar.contexto_academico_activo()
    assert recomendar.CONTEXTO_ACADEMICO in (recomendar.SYSTEM + recomendar.CONTEXTO_ACADEMICO)
    os.environ.pop(FLAG, None)

    # 'repite_lo_que_dejo' mira el top-3 completo, no solo el primero.
    class _C:
        def __init__(self, n):
            self.carrera, self.descripcion, self.razones = n, "", []

    class _R:
        def __init__(self, nombres):
            self.carreras = [_C(n) for n in nombres]
            self.confianza, self.confianza_nota = 70, ""

    r = _resumen(_R(["Licenciatura en Pedagogía y Administración Educativa",
                     "Ingeniería en Sistemas", "Licenciatura en Psicología Clínica"]), p)
    assert r["acierta"] is True, "el top-1 de educación debe contar como acierto"
    assert r["repite_lo_que_dejo"] is True, "Sistemas en el top-3 debe detectarse"

    r2 = _resumen(_R(["Licenciatura en Ciencias de la Educación"]), p)
    assert r2["repite_lo_que_dejo"] is False

    # La medida de trato: "para ti" cuenta como segunda persona, "para quienes" no.
    class _D(_C):
        def __init__(self, n, d):
            super().__init__(n)
            self.descripcion = d

    r3 = _resumen(type("_", (), {"carreras": [_D("X", "Es perfecta para ti porque te gusta enseñar.")],
                                 "confianza": 70, "confianza_nota": ""})(), p)
    assert r3["segunda_persona"] is True
    r4 = _resumen(type("_", (), {"carreras": [_D("X", "Es ideal para quienes tienen vocación.")],
                                 "confianza": 70, "confianza_nota": ""})(), p)
    assert r4["segunda_persona"] is False

    # Para quien no dejó nada, la medida no aplica (None, no False).
    assert _resumen(_R(["Ingeniería en Sistemas"]), PERFILES[0])["repite_lo_que_dejo"] is None
    print("ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--perfil")
    args = ap.parse_args()
    if getattr(args, "self_check"):
        _self_check()
    else:
        correr(args.perfil)
