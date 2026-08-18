"""Codifica el catálogo de carreras con el perfil RIASEC que O*NET publica.

## Qué hace y por qué

El bloque de texto con el resultado de Holland en el prompt **no mueve la
recomendación** (medido: 5 de 6 corridas ignoraron el área más alta, ver
`experiments/holland-en-chat.md`). La conclusión de ese experimento fue que si
Holland tiene que pesar, entra como **estructura**, no como prosa: cada carrera
del catálogo con su vector RIASEC, y el ranking ordenado por distancia al vector
del alumno.

Este script produce esa estructura. Para cada perfil del catálogo:

1. busca el nombre de la carrera en el buscador **en español** de O*NET
   (`/mpp/search`, el mismo "Mi Próximo Paso" que sirve el test),
2. toma las `OCUPACIONES` primeras ocupaciones,
3. les pide su perfil de intereses oficial
   (`/online/occupations/{code}/details/interests`, 0-100 por área),
4. promedia los vectores y guarda el resultado.

**El código RIASEC no lo inventa un modelo**: sale de la misma fuente que
califica el test del alumno. Esa es exactamente la ventaja que el CIP no tenía
(ver `experiments/cip-en-recomendacion.md` §6, donde el instrumento simulado
invalidó el A/B).

## Igual que en el CIP

- Se codifica **por perfil, no por registro**: la misma carrera recibe el mismo
  vector en todas sus sedes, por construcción.
- Un solo archivo, `data/holland_catalogo.json`, para que sea revisable a mano.
- Idempotente y resumible: solo pide lo que falta.
- Corre **offline, una vez**. En tiempo de ejecución solo se lee el JSON.

## Esto NO es el producto final

El emparejamiento carrera guatemalteca → ocupación de EE. UU. lo hace un
buscador por palabras: va a fallar en las carreras de nombre local (los
profesorados, los peritos) y en las híbridas. Cada entrada guarda **qué
ocupaciones se usaron** y `"revisado": false` justamente para que la revisión
humana sea posible y quede dicho que hace falta. `--revisar` imprime el informe.

## Uso

    uv run python codificar_holland.py --limite 3     # prueba de humo
    uv run python codificar_holland.py                # el resto
    uv run python codificar_holland.py --revisar      # informe, sin red
    uv run python codificar_holland.py --recodificar  # reaplica los arreglos a mano
"""

import argparse
import glob
import json
import os
import re
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv()

from app import holland  # noqa: E402  (usa el mismo cliente/credenciales del test)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "holland_catalogo.json")
COMPARTIDOS = os.path.join(DATA, "perfiles_compartidos.json")

# Cuántas ocupaciones de la búsqueda se promedian. Con 1 el vector queda a merced
# de que el primer resultado sea el técnico y no el profesional; con muchas se
# diluye. 3 es el punto en que un mal acierto no arrastra al promedio.
# ponytail: número fijo, no ponderado por posición. Si la revisión humana muestra
# que el 3.º suele ser ruido, bajarlo a 2 antes de inventar pesos.
OCUPACIONES = 3
LETRAS = "RIASEC"


def _cliente() -> httpx.Client:
    """El mismo cliente de `app.holland`, pero contra la raíz de la API: acá se
    usan `/mpp/search` y `/online/...`, no solo el Interest Profiler."""
    c = holland._cliente()
    c.base_url = "https://api-v2.onetcenter.org"
    return c


def perfiles_del_catalogo() -> dict[str, dict]:
    """{clave: {nombre, sedes}} — una entrada por perfil distinto.

    Misma convención de clave que `codificar_cip.py` y que `cip_filtro._clave`:
    `perfil_id` si la carrera comparte perfil entre sedes, `"centro::nombre"` si
    lo trae inline. Se copia en vez de importarse porque aquel módulo arrastra a
    Gemini al importarse y esto no necesita ni una llamada de IA.
    """
    out: dict[str, dict] = {}
    for archivo in sorted(glob.glob(os.path.join(DATA, "carreras_*.json"))):
        d = json.load(open(archivo, encoding="utf-8"))
        for c in d["carreras"]:
            clave = c.get("perfil_id") or f'{d["centro"]}::{c["nombre"]}'
            out.setdefault(clave, {"nombre": c["nombre"], "sedes": []})
            out[clave]["sedes"].append(d["centro"])
    return out


# El grado académico no es una ocupación y ensucia la búsqueda: con
# "Licenciatura en Ciencias Jurídicas y Sociales" el primer resultado eran
# profesores universitarios; sin el grado, salen los oficiales jurídicos.
# "PEM" se expande porque es una sigla local que O*NET no puede conocer;
# "Profesorado" NO se quita: ahí la docencia sí es la ocupación.
PREFIJOS = ("Licenciatura en la ", "Licenciatura en ", "Técnico Universitario en ",
            "Técnico en ")


# Términos corregidos a mano durante la revisión humana (2026-08-17). El valor
# es (qué se busca en O*NET, por qué). Reemplaza al nombre de la carrera.
#
# El buscador en español de O*NET falla de dos formas sistemáticas:
#
# 1. **Sesgo de "profesor de la materia".** Muchos nombres académicos caen en
#    "Profesores de X de Nivel Postsecundario", o sea el vector de *enseñar* la
#    carrera, no el de *ejercerla*. Se corrige nombrando la ocupación real.
# 2. **"Pedagogía" es una trampa.** Devuelve UNA sola ocupación, "Profesores de
#    Arte, Teatro, y Música", que no tiene nada que ver. Es determinista, no
#    azar. En los profesorados la docencia sí es la ocupación correcta (por eso
#    `termino()` no quita "Profesorado"), lo que estaba mal era la materia.
#
# Rehacer solo estas entradas: `uv run python codificar_holland.py --recodificar`
TERMINOS_REVISADOS: dict[str, tuple[str, str]] = {
    # -- "Pedagogía" -> profesores de arte y música (causa raíz 2) --
    "Pedagogía (PEM en Comunicación y Lenguaje y Lic. en Diseño Curricular)": (
        "Coordinadores Educativos",
        "el vector salía de UNA ocupación, profesores de arte/música; la carrera "
        "es lengua y diseño curricular",
    ),
    "PEM en Pedagogía y Técnico en Administración Educativa": (
        "Administradores Educativos", "la especialidad es gestión escolar, no arte"),
    "PEM en Pedagogía y Técnico en Administración Educativa con Orientación en Medio Ambiente": (
        "Administradores Educativos", "igual que la anterior"),
    "PEM en Pedagogía y Psicología": (
        "Profesores de Psicología", "la materia es psicología, no arte"),
    "PEM en Pedagogía y Educación Intercultural": (
        "Profesores de Educación Intercultural",
        "trae estudios étnicos y culturales, que es la especialidad real"),
    "Profesorado en Pedagogía con Especialización": (
        "Profesores de Educación", "docencia genérica, sin la desviación a arte"),

    # -- "Física" se lee como educación física (causa raíz 2, variante) --
    "Licenciatura en Educación de la Física y Matemática": (
        "Profesores de Física de Nivel Postsecundario",
        "la 1.ª ocupación era 'Especialistas en Educación Física Adaptada': el "
        "buscador leyó 'física' como deporte. Ojo, 'Profesores de Física' a secas "
        "tampoco sirve, mete 'Acondicionamiento Físico' y sube la R de 36 a 49; "
        "hay que pedir la ocupación con nombre completo. R queda en 26.7",
    ),

    # -- Sesgo de "profesor de la materia" (causa raíz 1) --
    "Administración Educativa": (
        "Superintendentes de Educación", "es gestión escolar, no dar clase"),
    "Licenciatura en Administración Educativa": (
        "Superintendentes de Educación", "igual que la anterior"),
    "Economía Empresarial": (
        "Analistas Económicos y Financieros",
        "2 de 3 eran profesores de economía; el egresado analiza, no enseña"),
    "Relaciones Internacionales": (
        "Especialistas en Asuntos Internacionales",
        "2 de 3 eran profesores de ciencias políticas"),
    "Ciencias de la Comunicación Social": (
        "Relaciones Públicas y Comunicación",
        "caía en profesores de comunicación y de literatura"),

    # -- Nombres sueltos que el buscador emparejaba mal --
    "Administración de Empresas": (
        "Gerentes de Servicios Administrativos",
        "el nombre tal cual daba 'Coordinadores de Reciclaje'. Costó tres "
        "intentos: 'Gerentes Generales de Operaciones' arrastró mantenimiento y "
        "energía eólica (R=57.7 en una carrera de oficina) y 'Analistas de "
        "Gestión Empresarial' daba títulos limpios pero el vector de un analista, "
        "no de un administrador (E bajaba a 51, S a 22). Con gerentes de verdad "
        "queda E=91.3",
    ),
    "Licenciatura en Ciencias Jurídicas y Sociales": (
        "Abogados",
        "nunca aparecía 'Abogados': salían oficiales jurídicos y secretarios "
        "legales, que inflan la C con trabajo de asistente",
    ),
    # -- 2.ª pasada (70 restantes): la carrera perdía su rasgo distintivo --
    "Profesorado en Educación Artística (Música y Danza)": (
        "Profesores de Arte, Teatro, y Música",
        "el profesorado de arte era el único perfil de arte SIN arte: A=34.3, "
        "indistinguible de cualquier otra pedagogía. Sube a 61. Irónico, es "
        "justo la ocupación que 'Pedagogía' devolvía de más en las que no la "
        "necesitaban. Cuesta S (93.3 a 70.7), y aun así el rasgo que separa a "
        "esta carrera de las demás es la A",
    ),
    "Ingeniería en Ciencias y Sistemas": (
        "Ingenieros de Software",
        "una carrera de computación cuyas 3 ocupaciones eran tecnólogos "
        "eléctricos, mecánicos y directores de ciencias naturales: cero "
        "computación. I sube de 74.7 a 81",
    ),
    "Ingeniería en Administración de Tierras": (
        "Topógrafos",
        "las 3 ocupaciones (directores de arquitectura, tecnólogos eléctricos y "
        "mecánicos) no tenían nada que ver con la tierra; de hecho eran las "
        "mismas de Ingeniería Mecánica. Ahora agrimensores y cartógrafos",
    ),
    "Licenciatura en Administración de Empresas Turísticas y Hoteleras": (
        "Gerentes de Hospedaje",
        "traía guías, agentes de reservación y recepcionistas de hotel, o sea el "
        "personal de mostrador y no quien administra. La C de 70 era trabajo de "
        "oficina; con gerentes la E sube de 52.7 a 95.7",
    ),
    "Ingeniería Industrial": (
        "Ingenieros Industriales",
        "'Mecánicos de Maquinaria Industrial' es un mecánico, no un ingeniero, e "
        "inflaba la R. Con ingenieros de verdad la I sube de 58.7 a 81.3",
    ),
    "Ingeniería en Agronomía": (
        "Ingenieros Agrónomos",
        "encabezaba un profesor de ciencias agrarias; el vector casi no se mueve "
        "pero ahora lo lidera la ocupación correcta",
    ),
    "Psicología Educativa": (
        "Psicólogos Escolares",
        "las tres psicologías (general, clínica y educativa) compartían un vector "
        "idéntico, o sea que el catálogo no las distinguía. Esta pasa a "
        "psicólogos escolares y orientadores, que es lo suyo",
    ),
    "Trabajo Social": (
        "Trabajadores Sociales",
        "encabezaba un profesor de trabajo social; ahora las 3 son trabajadores "
        "sociales reales, mismo código y sin el sesgo",
    ),

    # -- 3.ª pasada (las 41 que faltaban de revisar) --
    "Ingeniería Agrícola con Énfasis en Gerencia": (
        "Ingenieros Agrónomos",
        "las 3 ocupaciones eran operadores de maquinaria, mecánicos y "
        "contratistas de mano de obra: I=22.7 y A=0.0, el perfil de un jornalero "
        "y no de un ingeniero. Sube la I a 79.7. La 'Gerencia' del nombre se "
        "sigue perdiendo, O*NET no tiene gerencia agrícola en español",
    ),
    "Profesorado en Tecnologías de la Información y la Comunicación": (
        "Profesores de Ciencias de la Computación",
        "un profesorado sin una sola ocupación docente: traía informática "
        "médica, gerentes de proyectos y administradores de redes. La S sube de "
        "35.7 a 63.3, que es lo que corresponde a una carrera de enseñanza",
    ),

    "Licenciatura en Informática y Administración de Empresas": (
        "Gerentes de Sistemas de Computación e Información",
        "la 1.ª ocupación era 'Maestros de Escuela Secundaria', ruido puro que "
        "además inflaba la S. Es una carrera híbrida y O*NET no la representa con "
        "una sola búsqueda: 'Administradores de Redes' daba infraestructura pura y "
        "borraba la mitad administrativa. Los gerentes de sistemas son lo que más "
        "se acerca a las dos mitades",
    ),
}

# Revisadas a mano y **dejadas como estaban**: el emparejamiento es imperfecto y
# aun así es lo mejor que O*NET ofrece en español. Se anota el techo para que la
# próxima revisión no gaste el intento de nuevo.
SIN_MEJOR_TERMINO: dict[str, str] = {
    "Técnico Universitario en Hemodiálisis":
        "O*NET no tiene la ocupación en español; 'Técnicos de Diálisis' devuelve "
        "laboratorio clínico genérico, que es justo lo que ya tiene",
    "Arquitectura":
        "buscar 'Arquitectos' sale peor (navales, paisajistas, diseñadores de "
        "bases de datos); lo que ya tiene es más cercano",
    "Profesorado en Enseñanza Media en Cultura e Idioma Maya":
        "O*NET es el mercado laboral de EE. UU. y no tiene lenguas mayas; "
        "profesores de idiomas e intérpretes es lo más cercano que existe",
    "Profesorado en Idioma Maya, Ciencias Sociales e Interculturalidad":
        "igual que la anterior",
    "Profesorado en Emprendimiento para la Productividad":
        "busca mal ('Atletas y Competidores Deportivos') y no hay término en "
        "español que lo arregle; techo del buscador, no de la revisión",

    # -- 2.ª pasada: se probó una alternativa y MIDIÓ PEOR. La lista de títulos
    # mejoraba y el vector empeoraba, que es la trampa de esta revisión. --
    "Teología":
        "'Clero' trae sepultureros y coordinadores de servicios fúnebres: la I "
        "cae de 54 a 18.3 y la E salta de 29 a 66.7. Los profesores de filosofía "
        "y religión describen mejor el perfil contemplativo",
    "Teología Sistemática": "igual que Teología",
    "Técnico en Ejecución Musical Popular y Contemporánea":
        "'Músicos y Cantantes' baja la A de 82.3 a 64.7 (mete 'Mensajeros y "
        "Repartidores'). El 'Profesores de Inglés y Literatura' que parecía "
        "ruido puro es el que sostiene la A",
    "Chef Profesional e Internacional (Técnico Universitario)":
        "'Chefs y Primeros Chefs' baja la I de 47.7 a 26.7: se pierde a los "
        "científicos de alimentos, que es la parte técnica de la carrera",
    "Ingeniería Mecánica":
        "'Ingenieros Mecánicos' trae 'Operadores de Caldera': la R salta a 91 y "
        "la I CAE de 67.3 a 50.7. Un ingeniero debe tener I alta",
    "Ingeniería Química":
        "mismo caso que Ingeniería Mecánica: 'Ingenieros Químicos' arrastra "
        "operadores de caldera y la I cae de 82.7 a 65",
    "Licenciatura en Marketing and Business Analytics":
        "'Analistas de Investigación de Mercado' deja el perfil de un gerente de "
        "mercadeo (E=77.3) y borra la mitad analítica (I de 84 a 55.3). El "
        "profesor que encabeza es 1 de 3; los otros dos son analítica real",
    "Criminología y Política Criminal":
        "'Detectives e Investigadores Criminales' da el perfil de un supervisor "
        "policial (E=66.7) y baja la I de 70.7 a 45; la criminología es estudio",
    "Técnico Universitario en Criminología y Criminalística":
        "'Técnicos en Ciencias Forenses' cambia el ruido de 'Asistentes de "
        "Estadísticas' por el de 'Técnico de Ciencias de los Alimentos'",
    "Profesorado en Tecnología Educativa":
        "'Diseñadores Instruccionales' hunde la S de 93.3 a 60 en una carrera "
        "docente y sigue sin traer nada de tecnología",

    # -- 2.ª pasada: el término correcto devuelve las mismas ocupaciones. El
    # sesgo de profesor era aparente, el vector ya estaba bien. --
    "Licenciatura en Economía":
        "'Economistas' devuelve las mismas 3 ocupaciones, vector idéntico",
    "Ingeniería Civil":
        "'Ingenieros Civiles' devuelve las mismas 3, vector idéntico",
    "Psicología Clínica":
        "'Psicólogos Clínicos y de Consejería' devuelve las mismas 3, vector "
        "idéntico. Comparte vector con 'Psicología (PEM y Licenciatura)' y no "
        "hay forma de separarlas con este método",

    # -- 3.ª pasada: probadas y rechazadas --
    "Licenciatura en Administración de Telecomunicaciones":
        "techo duro. 'Especialistas en Ingeniería de Telecomunicaciones', "
        "'Ingenieros de Telecomunicaciones' y 'Gerentes de Telecomunicaciones e "
        "Ingeniería' devuelven LAS MISMAS 3 ocupaciones, 2 de ellas "
        "instaladores de líneas: O*NET en español no tiene gestión de "
        "telecomunicaciones. La R=80.3 es de obrero y está mal para una "
        "licenciatura, pero 'Gerentes de Sistemas de Computación' la dejaría con "
        "el vector EXACTO de Informática y Adm. de Empresas y sin telecom",
    "Ingeniería Mecánica Industrial":
        "'Ingenieros Industriales' sube la I de 71.7 a 81.3 pero borra la mitad "
        "mecánica y deja el vector idéntico al de Ingeniería Industrial. La I "
        "actual ya es alta; el profesor es 1 de 3",
    "Licenciatura en Ciencias de la Educación":
        "'Administradores Educativos' la vuelve pura gestión (I de 60.7 a 44) y "
        "es una carrera de educación amplia, no de administración",
    "Licenciatura en la Enseñanza de la Matemática y la Física":
        "ya tiene profesores de matemática Y de física, que es lo correcto. "
        "'Profesores de Física de Nivel Postsecundario' hunde la I de 79 a 51.3 "
        "y pierde la matemática. Ojo, no confundir con 'Licenciatura en "
        "Educación de la Física y Matemática', que sí tenía el bug de educación "
        "física y sí se corrigió con ese término",
    "PEM en Matemática y Física":
        "cambia una materia faltante por otra: hoy le falta física, con "
        "'Profesores de Física' le faltaría matemática, y encima baja I y S",
    "Profesorado en Física y Matemática":
        "igual que el anterior: la I bajaría de 63.7 a 51.3",
}

# Revisadas y **correctas sin cambio**: la búsqueda por el nombre de la carrera
# ya devuelve las ocupaciones que la ejercen (Médico y Cirujano → cirujanos,
# Enfermería → enfermeros, Contaduría → contadores y auditores). Se listan para
# que `revisado` signifique "alguien la miró", no solo "alguien la corrigió".
# No se les probó alternativa porque no hay hipótesis de mejora que probar.
YA_CORRECTAS: frozenset[str] = frozenset({
    "Administración de Hotelería, Turismo y Gastronomía",
    "Artes Culinarias y Negocios Gastronómicos",
    "Cirujano Dentista",
    "Contaduría Pública y Auditoría",
    "Fisioterapia",
    "Ingeniería Ambiental",
    "Ingeniería Forestal",
    "Ingeniería en Electrónica",
    "Ingeniería en Gestión Ambiental Local",
    "Licenciatura en Administración de Sistemas Informáticos",
    "Licenciatura en Administración en Desarrollo de Recursos Humanos",
    "Licenciatura en Ciencias de la Comunicación (Técnico en Publicidad)",
    "Licenciatura en Comercio Internacional",
    "Licenciatura en Comunicación y Diseño",
    "Licenciatura en Educación Primaria con Especialización en Gestión Educativa Intercultural",
    "Licenciatura en Educación de la Comunicación y Lenguaje",
    "Licenciatura en Enfermería",
    "Licenciatura en Informática e Inteligencia de Negocios",
    "Licenciatura en Nutrición",
    "Licenciatura en Producción Audiovisual y Artes Cinematográficas",
    "Licenciatura en Producción de Imágenes Diagnósticas",
    "Licenciatura en Publicidad con Especialidad en Diseño Gráfico",
    "Licenciatura en Química Biológica",
    "Médico y Cirujano",
    "PEM en Comunicación y Lenguaje",
    "PEM en Historia y Ciencias Sociales",
    "PEM en Lenguaje e Historia",
    "Profesorado de Enseñanza Media en Inglés",
    "Profesorado en Ciencias Naturales, Química y Biología",
    "Profesorado en Educación Inicial y Preprimaria",
    "Profesorado en Educación Primaria",
    "Profesorado en Psicopedagogía",
    "Psicología (PEM y Licenciatura)",
    "Técnico Universitario en Desarrollo de Software",
    "Técnico Universitario en Enfermería Veterinaria",
    "Técnico Universitario en Gerencia de Ventas",
    "Técnico Universitario en Laboratorio Clínico",
    "Técnico Universitario en Optometría",
    "Técnico Universitario en Radiología e Imágenes Diagnósticas",
    "Técnico Universitario en Visita Médica y Mercadeo",
    "Técnico en Laboratorio Dental",
})


def _revisada(nombre: str) -> bool:
    """Si una persona tomó una decisión explícita sobre esta carrera.

    Las tres formas de estarlo: se le corrigió el término (`TERMINOS_REVISADOS`),
    se le probó una alternativa que no mejoró (`SIN_MEJOR_TERMINO`), o se miró y
    no había hipótesis que probar (`YA_CORRECTAS`).
    """
    return (nombre in TERMINOS_REVISADOS or nombre in SIN_MEJOR_TERMINO
            or nombre in YA_CORRECTAS)


def termino(nombre: str) -> str:
    """El nombre de la carrera como palabras que O*NET pueda buscar."""
    if nombre in TERMINOS_REVISADOS:
        return TERMINOS_REVISADOS[nombre][0]
    t = re.sub(r"\s*\([^)]*\)", "", nombre).strip()  # "(Técnico Universitario)" y demás
    for p in PREFIJOS:
        if t.startswith(p):
            t = t[len(p):]
            break
    return re.sub(r"^PEM en ", "Profesorado de Enseñanza Media en ", t)


def _buscar(cli: httpx.Client, nombre: str) -> list[dict]:
    """Las primeras ocupaciones de O*NET para el nombre de una carrera."""
    r = cli.get("/mpp/search",
                params={"keyword": termino(nombre), "start": 1, "end": OCUPACIONES})
    r.raise_for_status()
    return r.json().get("career", [])[:OCUPACIONES]


def _intereses(cli: httpx.Client, code: str) -> dict[str, int]:
    """{letra: 0-100} del perfil de intereses oficial de una ocupación."""
    r = cli.get(f"/online/occupations/{code}/details/interests")
    r.raise_for_status()
    # `name` viene en inglés (Realistic, Investigative, ...) y las seis iniciales
    # son distintas, igual que en `app.holland`.
    return {e["name"][0].upper(): e["occupational_interest"] for e in r.json()["element"]}


def _codigo(vector: dict[str, float]) -> str:
    """Las 3 letras más altas; empates por orden canónico RIASEC, como en el test."""
    orden = sorted(LETRAS, key=lambda l: (-vector.get(l, 0), LETRAS.index(l)))
    return "".join(orden[:3])


def codificar_una(cli: httpx.Client, nombre: str) -> dict | None:
    ocupaciones = _buscar(cli, nombre)
    if not ocupaciones:
        return None
    vectores = [_intereses(cli, o["code"]) for o in ocupaciones]
    vector = {l: round(sum(v.get(l, 0) for v in vectores) / len(vectores), 1) for l in LETRAS}
    return {
        "nombre": nombre,
        "vector": vector,
        "codigo": _codigo(vector),
        # Se guarda con qué ocupaciones se armó: sin esto, la revisión humana
        # tendría que adivinar por qué una carrera salió como salió.
        "ocupaciones": [{"code": o["code"], "title": o["title"]} for o in ocupaciones],
        "revisado": _revisada(nombre),
    }


def codificar(limite: int | None = None):
    perfiles = perfiles_del_catalogo()
    hecho = json.load(open(SALIDA, encoding="utf-8")) if os.path.exists(SALIDA) else {}
    pendientes = [(k, v) for k, v in perfiles.items() if k not in hecho][:limite or None]
    if not pendientes:
        print(f"Nada pendiente: los {len(perfiles)} perfiles ya están codificados.")
        return

    print(f"{len(perfiles)} perfiles · {len(hecho)} ya codificados · "
          f"{len(pendientes)} por codificar ({(1 + OCUPACIONES) * len(pendientes)} llamadas a O*NET)")
    with _cliente() as cli:
        for i, (clave, v) in enumerate(pendientes, 1):
            try:
                entrada = codificar_una(cli, v["nombre"])
            except httpx.HTTPError as e:
                print(f"  [{i}/{len(pendientes)}] {v['nombre']}: falló ({e})")
                continue
            if not entrada:
                print(f"  [{i}/{len(pendientes)}] {v['nombre']}: O*NET no devolvió ocupaciones")
                continue
            hecho[clave] = entrada
            print(f"  [{i}/{len(pendientes)}] {v['nombre']} -> {entrada['codigo']} "
                  f"({entrada['ocupaciones'][0]['title']})")
            # Se guarda en cada vuelta: si se corta, no se repite lo hecho.
            json.dump(dict(sorted(hecho.items())), open(SALIDA, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
    print(f"\n{SALIDA} · {len(hecho)} carreras codificadas")


def recodificar():
    """Rehace las entradas de `TERMINOS_REVISADOS` y corrige el flag `revisado`.

    Existe porque los arreglos a mano se estaban aplicando con scripts sueltos
    que mutaban el JSON: el resultado quedaba, pero no el motivo ni la forma de
    repetirlo. Acá el término corregido vive en el código, con su porqué, y esta
    función lo vuelve a aplicar cuando haga falta.

    De paso arregla el flag: venía en `true` en las 90 entradas sin que nadie las
    hubiera mirado, así que no servía para medir el avance de la revisión. Pasa a
    significar una sola cosa: el nombre está en `TERMINOS_REVISADOS` (se corrigió)
    o en `SIN_MEJOR_TERMINO` (se probó una alternativa y no mejoró) o en
    `YA_CORRECTAS` (se miró y no había nada que probar).
    """
    hecho = json.load(open(SALIDA, encoding="utf-8"))
    objetivo = {k: v for k, v in hecho.items() if v["nombre"] in TERMINOS_REVISADOS}
    print(f"{len(objetivo)} entradas con término corregido a mano · "
          f"{(1 + OCUPACIONES) * len(objetivo)} llamadas a O*NET")
    with _cliente() as cli:
        for i, (clave, v) in enumerate(objetivo.items(), 1):
            nombre, antes = v["nombre"], v["codigo"]
            try:
                entrada = codificar_una(cli, nombre)
            except httpx.HTTPError as e:
                print(f"  [{i}/{len(objetivo)}] {nombre}: falló ({e})")
                continue
            if not entrada:
                print(f"  [{i}/{len(objetivo)}] {nombre}: O*NET no devolvió ocupaciones")
                continue
            hecho[clave] = entrada
            print(f"  [{i}/{len(objetivo)}] {nombre[:42]:<42} {antes} -> {entrada['codigo']}  "
                  + "; ".join(o["title"] for o in entrada["ocupaciones"]))
    for v in hecho.values():
        v["revisado"] = _revisada(v["nombre"])
    json.dump(dict(sorted(hecho.items())), open(SALIDA, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{SALIDA} · {sum(1 for v in hecho.values() if v['revisado'])}/{len(hecho)} "
          f"revisadas a mano")


def revisar():
    """Informe para la revisión humana. Sin red."""
    hecho = json.load(open(SALIDA, encoding="utf-8"))
    perfiles = perfiles_del_catalogo()
    faltan = [v["nombre"] for k, v in perfiles.items() if k not in hecho]
    print(f"{len(hecho)}/{len(perfiles)} perfiles codificados · "
          f"{sum(1 for v in hecho.values() if v['revisado'])} revisados a mano")
    print("Distribución de códigos: "
          + ", ".join(f"{c}={n}" for c, n in Counter(v["codigo"] for v in hecho.values()).most_common(10)))
    if faltan:
        print(f"Sin codificar ({len(faltan)}): " + ", ".join(faltan[:10]))
    print("\nCarrera -> código · ocupaciones de O*NET con las que se armó:")
    for v in sorted(hecho.values(), key=lambda v: v["nombre"]):
        marca = " " if v["revisado"] else "·"
        print(f" {marca} {v['nombre'][:48]:<48} {v['codigo']}  "
              + "; ".join(o["title"] for o in v["ocupaciones"]))


def _self_check():
    assert _codigo({"R": 90, "I": 80, "A": 10, "S": 70, "E": 5, "C": 5}) == "RIS"
    # Empate: manda el orden canónico RIASEC, no el del diccionario.
    assert termino("Licenciatura en Economía") == "Economía"
    assert termino("PEM en Matemática y Física") == "Profesorado de Enseñanza Media en Matemática y Física"
    assert termino("Chef Profesional e Internacional (Técnico Universitario)") == "Chef Profesional e Internacional"
    assert termino("Profesorado en Educación Primaria") == "Profesorado en Educación Primaria"
    assert _codigo({"C": 50, "A": 50, "R": 50, "I": 1, "S": 1, "E": 1}) == "RAC"
    p = perfiles_del_catalogo()
    assert len(p) > 50, len(p)
    assert all(v["sedes"] for v in p.values())

    # El término corregido gana sobre el nombre de la carrera.
    assert termino("Administración de Empresas") == "Gerentes de Servicios Administrativos"
    # Un nombre mal escrito en los dicts no haría nada, y en silencio: la
    # entrada se codificaría con el término malo y seguiría contando como
    # revisada. Por eso se comparan contra el catálogo real.
    nombres = {v["nombre"] for v in p.values()}
    huerfanos = (set(TERMINOS_REVISADOS) | set(SIN_MEJOR_TERMINO) | YA_CORRECTAS) - nombres
    assert not huerfanos, f"nombres que no existen en el catálogo: {sorted(huerfanos)}"
    # Una carrera no puede estar corregida y sin arreglo posible a la vez.
    grupos = {"TERMINOS_REVISADOS": set(TERMINOS_REVISADOS),
              "SIN_MEJOR_TERMINO": set(SIN_MEJOR_TERMINO),
              "YA_CORRECTAS": set(YA_CORRECTAS)}
    for a, b in (("TERMINOS_REVISADOS", "SIN_MEJOR_TERMINO"),
                 ("TERMINOS_REVISADOS", "YA_CORRECTAS"),
                 ("SIN_MEJOR_TERMINO", "YA_CORRECTAS")):
        repetidos = grupos[a] & grupos[b]
        assert not repetidos, f"en {a} y {b} a la vez: {sorted(repetidos)}"

    revisadas = len(TERMINOS_REVISADOS) + len(SIN_MEJOR_TERMINO) + len(YA_CORRECTAS)
    print(f"self-check OK — {len(p)} perfiles en el catálogo · "
          f"{len(TERMINOS_REVISADOS)} corregidos · "
          f"{len(SIN_MEJOR_TERMINO)} sin mejor término · "
          f"{len(YA_CORRECTAS)} ya correctos · {revisadas}/{len(p)} revisados")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limite", type=int, help="codifica solo N perfiles pendientes")
    ap.add_argument("--revisar", action="store_true", help="informe, sin red")
    ap.add_argument("--recodificar", action="store_true",
                    help="rehace las entradas con término corregido a mano")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.revisar:
        revisar()
    elif a.recodificar:
        recodificar()
    else:
        codificar(a.limite)
