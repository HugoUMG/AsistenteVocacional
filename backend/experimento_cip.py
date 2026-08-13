"""Experimento A/B: ¿mejora la recomendación si el CIP prioriza el catálogo?

Mide la hipótesis del experimento `cip-en-recomendacion`: que hacer el recorte de
candidatas con el **percentil de un instrumento** en vez de dejárselo entero al
criterio de Gemini mejora (o al menos no empeora) el acierto, y de paso lo vuelve
auditable.

## Metodología

La misma del Experimento B de `experiments/cobertura-dimensiones.md`, para que las
cifras sean comparables: **10 perfiles ficticios coherentes**, cada uno con un
`area_esperada` que sirve de criterio externo débil. Se mide si la carrera top-1
cae en esa área.

Diferencia con aquel: además de las respuestas del chat, cada persona **responde
el CIP completo** (150 ítems) en su papel. Esas respuestas se califican con
`cip_fogliatto` y el perfil resultante alimenta el brazo NUEVO.

- Brazo **VIEJO**: `recomendar(respuestas, catálogo)` con el flag apagado.
  Es exactamente el comportamiento actual en producción.
- Brazo **NUEVO**: `recomendar(respuestas, catálogo, perfil_cip)` con el flag
  encendido. El catálogo llega recortado por congruencia CIP y el prompt incluye
  los percentiles como dato medido.

Ambos brazos reciben **las mismas respuestas de chat**, así que la única variable
que cambia es el CIP. Ámbito: catálogo de Quetzaltenango + Totonicapán completo.

## Limitaciones, dichas de frente

- 10 casos ficticios no dan potencia estadística. Es el mismo estándar de los
  experimentos anteriores del proyecto, y sirve para detectar regresiones
  gruesas, no para afirmar una mejora fina.
- Las respuestas del CIP las genera el propio Gemini en el papel de la persona.
  Hay riesgo de circularidad: el modelo que responde y el que recomienda son el
  mismo. Se mitiga en parte porque entre uno y otro media la **calificación
  aritmética** del instrumento, que el modelo no controla.
- `area_esperada` la definí yo al escribir los perfiles. Es un criterio externo
  débil, no un criterio de validez.

## Uso

    uv run python experimento_cip.py --self-check   # sin red
    uv run python experimento_cip.py --responder    # 10 llamadas, cachea el CIP
    uv run python experimento_cip.py                # corre el A/B y reporta
"""

import argparse
import glob
import json
import os

from dotenv import load_dotenv

# ANTES de importar `app.recomendar`: ese módulo resuelve MODELO/MODELO_FINAL con
# os.getenv al importarse, así que si el .env se carga después, el script corre
# con el modelo por defecto del código y no con el del proyecto. Pasó: la primera
# corrida se fue a gemini-2.5-flash y agotó su cuota diaria sin razón.
load_dotenv()

from pydantic import BaseModel  # noqa: E402

from app import cip_filtro, cip_fogliatto, recomendar  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "data", "tests",
                     "experimento_cip_respuestas.json")
DATA = os.path.join(os.path.dirname(__file__), "data")

# (nombre, área esperada, palabras que identifican un acierto, descripción con la
# que Gemini responde el CIP en su papel, respuestas del chat)
PERSONAS = [
    ("Ana", "salud/psicología", ["enfermer", "médic", "psicolog", "fisioterap", "nutric", "odontolog", "dental", "clínic", "radiolog", "optometr", "hemodial", "bioimag", "veterinar"],
     "Le conmueve el sufrimiento ajeno y quiere aliviarlo con sus manos. Le fascina el cuerpo humano y cómo funciona. No le da impresión la sangre ni los hospitales. Detesta el trabajo de oficina y los números.",
     {"departamento": "Quetzaltenango", "temas": "el cuerpo humano, la salud, cuidar a la gente enferma",
      "entorno": "un hospital o una clínica, moviéndome, con pacientes",
      "impacto": "que alguien se recupere gracias a lo que hice"}),
    ("Luis", "informática", ["sistemas", "informátic", "software", "comput", "negocios"],
     "Programa desde los 13 años. Le encanta resolver problemas lógicos y automatizar cosas. Prefiere una pantalla a una reunión. Le aburre memorizar y le incomoda tratar con público.",
     {"departamento": "Quetzaltenango", "temas": "programar, la lógica, construir aplicaciones",
      "entorno": "frente a una computadora, con audífonos, sin que me interrumpan",
      "impacto": "crear algo que mucha gente use todos los días"}),
    ("Mario", "administración", ["administra", "empresa", "mercadot", "market", "comercio", "econom", "hotel", "turismo"],
     "Organiza a todos en los trabajos de grupo. Le gusta negociar, vender y llevar cuentas. Piensa en montar su propio negocio. Le aburre el laboratorio y no le interesa el arte.",
     {"departamento": "Quetzaltenango", "temas": "los negocios, cómo se organiza una empresa, vender",
      "entorno": "una oficina, reuniéndome con gente, tomando decisiones",
      "impacto": "generar empleo en mi comunidad"}),
    ("Sofía", "educación", ["pedagog", "educa", "docen", "profesor", "enseñanza", "psicopedag", "magisterio"],
     "Explica la tarea a sus compañeros y disfruta cuando entienden. Tiene paciencia con los niños. Le interesa por qué unos aprenden y otros no. No le atraen las máquinas ni los números.",
     {"departamento": "Quetzaltenango", "temas": "enseñar, cómo aprenden los niños, la lectura",
      "entorno": "un aula, con estudiantes, explicando",
      "impacto": "que un niño que no sabía leer aprenda conmigo"}),
    ("Diego", "forestal/ambiental", ["forestal", "agronom", "ambient", "agrícola", "tierra", "natural"],
     "Creció en el campo y conoce los árboles por su nombre. Le preocupa la tala y quiere trabajar al aire libre. Odia estar encerrado. No le interesan la oficina ni el comercio.",
     {"departamento": "Quetzaltenango", "temas": "los bosques, el medio ambiente, los cultivos",
      "entorno": "al aire libre, en el campo, caminando entre árboles",
      "impacto": "que se recuperen los bosques de mi región"}),
    ("Carmen", "derecho", ["jurídic", "derecho", "abogac", "notariad", "internacional", "polític"],
     "Discute con argumentos y le indigna la injusticia. Lee sobre leyes y política. Le gusta hablar en público y defender una postura. No le atrae la ciencia ni el trabajo manual.",
     {"departamento": "Quetzaltenango", "temas": "las leyes, la justicia, defender a la gente",
      "entorno": "un tribunal o una oficina jurídica, argumentando",
      "impacto": "que alguien sin recursos tenga una defensa justa"}),
    ("Pablo", "criminalística", ["criminal", "crimino", "forense"],
     "Le apasionan las series de investigación forense. Es observador y metódico, y disfruta armar rompecabezas con pistas. Le interesa el laboratorio aplicado a resolver delitos.",
     {"departamento": "Quetzaltenango", "temas": "investigar delitos, la evidencia, el análisis forense",
      "entorno": "una escena del crimen y un laboratorio, analizando pruebas",
      "impacto": "que un caso se resuelva con evidencia sólida"}),
    ("Lucía", "comunicación", ["comunicac", "periodis", "publicid", "audiovisual", "diseño"],
     "Escribe bien y le gusta contar historias. Maneja las redes del colegio. Quiere entrevistar gente y hacer videos. Le aburren las matemáticas y el laboratorio.",
     {"departamento": "Quetzaltenango", "temas": "contar historias, los medios, hacer videos",
      "entorno": "en la calle entrevistando, o editando en una redacción",
      "impacto": "que se conozcan historias que nadie está contando"}),
    ("Roberto", "contaduría", ["contad", "contabil", "audit", "finanz"],
     "Es ordenado y meticuloso con los números. Lleva las cuentas de la tienda familiar. Le da tranquilidad que las cosas cuadren. No le gusta improvisar ni exponerse en público.",
     {"departamento": "Quetzaltenango", "temas": "los números, la contabilidad, que todo cuadre",
      "entorno": "una oficina ordenada, con mis registros y mi sistema",
      "impacto": "que un negocio sea transparente y no quiebre"}),
    ("Elena", "trabajo social", ["trabajo social", "social", "psicolog", "intercultural", "comunitar"],
     "Participa en actividades de su comunidad y le duele la pobreza que ve. Quiere organizar a la gente para mejorar su barrio. No le atraen la tecnología ni los negocios.",
     {"departamento": "Quetzaltenango", "temas": "las comunidades, la pobreza, organizar a la gente",
      "entorno": "en las comunidades, visitando familias, en reuniones de vecinos",
      "impacto": "que una comunidad organizada resuelva sus propios problemas"}),
]


class _Carrera:
    """Lo mínimo que `recomendar()` y `cip_filtro` leen de una carrera. Se arma
    desde los JSON del catálogo en vez de la BD: el experimento no necesita
    Postgres encendido y así es reproducible en cualquier máquina."""

    def __init__(self, nombre, universidad, centro, departamento, perfil, grupo, sello=None):
        self.nombre, self.universidad, self.centro = nombre, universidad, centro
        self.departamento, self.perfil, self.perfil_grupo, self.sello = departamento, perfil, grupo, sello


def catalogo() -> list[_Carrera]:
    compartidos = json.load(open(os.path.join(DATA, "perfiles_compartidos.json"), encoding="utf-8"))
    out = []
    for archivo in sorted(glob.glob(os.path.join(DATA, "carreras_*.json"))):
        d = json.load(open(archivo, encoding="utf-8"))
        for c in d["carreras"]:
            pid = c.get("perfil_id")
            out.append(_Carrera(c["nombre"], d["universidad"], d["centro"], d["departamento"],
                                compartidos[pid] if pid else c["perfil"], pid, c.get("sello")))
    return out


class RespuestaCip(BaseModel):
    n: int
    r: str


class HojaCip(BaseModel):
    respuestas: list[RespuestaCip]


def responder_cip():
    """Cada persona responde los 150 ítems en su papel. 1 llamada por persona.

    Se cachea: volver a correrlo no vuelve a gastar cuota. Si una persona queda
    incompleta o con respuestas inválidas, se descarta y se vuelve a pedir en la
    siguiente corrida, en vez de rellenarla con un valor por defecto (eso
    falsearía el perfil, que es justo lo que se está midiendo).
    """
    hecho = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    items = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(cip_fogliatto.ITEMS))
    system = (
        "Respondes un cuestionario de intereses profesionales EN EL PAPEL de la "
        "persona que se te describe. Para cada una de las 150 actividades indicas "
        "'D' si le produce desagrado, 'I' si le es indiferente y 'A' si le agrada.\n"
        "Responde como respondería esa persona, no como responderías tú. Sé "
        "coherente con su carácter: si algo no le interesa, marca D, no I por "
        "cortesía. Devuelve las 150 respuestas, con su número de ítem."
    )
    for nombre, _, _, descripcion, _ in PERSONAS:
        if nombre in hecho:
            continue
        print(f"  {nombre}…", end=" ", flush=True)
        resp = recomendar.generar(
            model=recomendar.MODELO_FINAL, system=system, catalogo="",
            variable=f"PERSONA:\n{descripcion}\n\nACTIVIDADES:\n{items}",
            schema=HojaCip, temperature=0.4,
        )
        hoja = HojaCip.model_validate_json(recomendar._texto_seguro(resp))
        r = {x.n: x.r.strip().upper() for x in hoja.respuestas}
        malas = [n for n, v in r.items() if v not in cip_fogliatto.VALOR]
        if len(r) != cip_fogliatto.N_ITEMS or malas:
            print(f"descartada ({len(r)} respuestas, {len(malas)} inválidas) — se reintenta luego")
            continue
        hecho[nombre] = r
        print("ok")
        json.dump(hecho, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    faltan = [p[0] for p in PERSONAS if p[0] not in hecho]
    print(f"\nHojas CIP completas: {len(hecho)}/{len(PERSONAS)}"
          + (f" · faltan {faltan}" if faltan else ""))
    return hecho


def acierta(carrera: str, claves: list[str]) -> bool:
    c = carrera.lower()
    return any(k in c for k in claves)


def correr():
    hojas = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if len(hojas) < len(PERSONAS):
        print("Faltan hojas del CIP. Corre primero: uv run python experimento_cip.py --responder")
        return
    cat = catalogo()
    print(f"Catálogo: {len(cat)} registros carrera-sede · {len(PERSONAS)} perfiles\n")

    filas = []
    for nombre, area, claves, _, respuestas in PERSONAS:
        hoja = {int(k): v for k, v in hojas[nombre].items()}
        # El sexo solo elige la columna del baremo; se fija en femenino para todos
        # para que no introduzca una variable extra en la comparación.
        cal = cip_fogliatto.calificar(hoja, sexo="femenino")

        os.environ["CIP_EN_RECOMENDACION"] = "0"
        viejo, _ = recomendar.recomendar(respuestas, cat)
        os.environ["CIP_EN_RECOMENDACION"] = "1"
        nuevo, _ = recomendar.recomendar(respuestas, cat, perfil_cip=cal["perfil"])
        os.environ["CIP_EN_RECOMENDACION"] = "0"

        tv, tn = viejo.carreras[0], nuevo.carreras[0]
        altas = [e["nombre"] for e in sorted(cal["perfil"], key=lambda x: -x["percentil"])[:3]]
        filas.append({
            "persona": nombre, "area": area, "cip_top3": altas,
            "viejo": tv.carrera, "viejo_af": tv.afinidad, "viejo_ok": acierta(tv.carrera, claves),
            "nuevo": tn.carrera, "nuevo_af": tn.afinidad, "nuevo_ok": acierta(tn.carrera, claves),
        })
        f = filas[-1]
        print(f'{nombre:<8} CIP: {", ".join(altas[:2])}')
        print(f'   VIEJO {"OK " if f["viejo_ok"] else "NO "} {f["viejo"][:50]:<52} {f["viejo_af"]}%')
        print(f'   NUEVO {"OK " if f["nuevo_ok"] else "NO "} {f["nuevo"][:50]:<52} {f["nuevo_af"]}%')

    v = sum(f["viejo_ok"] for f in filas)
    n = sum(f["nuevo_ok"] for f in filas)
    cambios = sum(f["viejo"] != f["nuevo"] for f in filas)
    print(f'\n{"─" * 66}')
    print(f'Top-1 en el área esperada   VIEJO {v}/{len(filas)}   NUEVO {n}/{len(filas)}')
    print(f'Afinidad promedio del top-1 VIEJO {sum(f["viejo_af"] for f in filas) / len(filas):.0f}%'
          f'   NUEVO {sum(f["nuevo_af"] for f in filas) / len(filas):.0f}%')
    print(f'El top-1 cambió en {cambios}/{len(filas)} perfiles')
    print(f'\nVEREDICTO: {"acepta" if n > v else "revierte" if n < v else "empate"} '
          f'(regla 4 del proyecto: si mide peor, se revierte)')
    json.dump(filas, open(os.path.join(DATA, "tests", "experimento_cip_resultados.json"),
                          "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _self_check():
    cat = catalogo()
    assert len(cat) == 202, len(cat)
    assert all(c.nombre and c.perfil and c.departamento for c in cat)
    # El experimento necesita que el catálogo esté codificado, si no el brazo
    # NUEVO sería idéntico al VIEJO y la comparación no mediría nada.
    codificadas = sum(1 for c in cat if cip_filtro.codigo_de(c))
    assert codificadas == len(cat), f"solo {codificadas}/{len(cat)} carreras codificadas"

    assert len(PERSONAS) == 10
    assert len({p[0] for p in PERSONAS}) == 10
    # Cada persona tiene que poder acertar: al menos una carrera del catálogo
    # real debe coincidir con sus palabras clave, o el caso es imposible por
    # construcción y estaría midiendo un catálogo, no un motor.
    for nombre, area, claves, _, _ in PERSONAS:
        posibles = [c.nombre for c in cat if acierta(c.nombre, claves)]
        assert posibles, f"{nombre} ({area}): ninguna carrera del catálogo casa con {claves}"

    assert acierta("Licenciatura en Enfermería", ["enfermer"])
    assert not acierta("Contaduría Pública", ["enfermer"])
    print(f"self-check OK — {len(cat)} carreras ({codificadas} codificadas), "
          f"{len(PERSONAS)} perfiles, todos con acierto posible")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--self-check", action="store_true", help="prueba interna, sin red")
    p.add_argument("--responder", action="store_true", help="genera las hojas del CIP (10 llamadas)")
    a = p.parse_args()
    if a.self_check:
        _self_check()
    else:
        responder_cip() if a.responder else correr()
        # Llama a recomendar.generar() directo (sin FastAPI), así que su consumo no
        # cae en uso_tokens: este contador es el único registro del gasto.
        print(recomendar.resumen_gasto())
