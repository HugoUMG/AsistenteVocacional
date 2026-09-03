"""Experimento A/B: el pre-filtro del catálogo, ¿ayuda o estorba?

`filtro.preseleccionar` recorta el catálogo a 35 carreras antes de mandarlo a
`next-question`, emparejando PALABRA LITERAL entre las respuestas del alumno y
el `perfil` de cada carrera. La depuración del banco de opciones (2026-08-23)
encontró que ese emparejamiento es en buena parte accidental:

- 9 palabras del banco no existen en ningún perfil del catálogo (`cuidar`,
  `emprender`, `educar`, `investigar`...), o sea que esas opciones no aportan
  nada al recorte.
- 85 de 147 carreras (57%) no tienen ninguna palabra específica en común con el
  banco, o cuelgan de una sola, y en 30 casos esa única palabra es un falso
  amigo: las cinco Ingenierías en Sistemas entran por `campo` ("un campo que
  cambia a diario") y por `crear` ("crear soluciones digitales"), Radiología por
  `estudio` ("el estudio solicitado"), Telecomunicaciones por `aire` ("viaja a
  través del aire"), Contaduría por `salud` ("la salud de una organización").
- Economía Empresarial no sobrevive el recorte en NINGUNA simulación: su única
  palabra en común con todo el banco es `historia`.

Este script mide si quitar el recorte cambia algo, y cuánto cuesta en dinero y
en tiempo de respuesta.

## Brazos

Los tres corren el flujo de producción completo (4 fijas + adaptativas +
recomendación) con el MISMO perfil de alumno. Lo único que cambia:

- **A** — producción de hoy: `next-question` ve el top-35 del filtro.
- **A2 (CONTROL)** — idéntico a A, corrido aparte.
- **B** — `next-question` ve el catálogo completo del departamento (185 filas).

`recomendar()` NO usa el filtro en ninguno de los brazos (nunca lo ha usado), así
que la diferencia entra solo por las preguntas que el modelo elige.

## Por qué hace falta A2

Este sistema devuelve resultados distintos con entrada IDÉNTICA: correr el mismo
brazo dos veces cambia el top-1 en 2 a 3 de cada 4 casos (piso de ruido medido el
2026-08-23, ver CLAUDE.md). **A2 es la misma configuración que A**, así que todo
lo que cambie entre ellos es ruido del sistema y nada más. La regla de lectura es
una sola: si la tasa de cambio de A vs B no supera la de A vs A2, no hay efecto
de calidad que reportar.

La primera corrida de este experimento (13/16 vs 12/16) se hizo SIN control y por
eso su conclusión quedó sobreinterpretada.

## Por qué tres conversaciones y no una

En el experimento de edad y grado bastaba una conversación porque el cambio
estaba en el último paso. Aquí no: el filtro cambia lo que el modelo ve al
ELEGIR cada pregunta, así que cada brazo necesita su propia conversación. Cuesta
el triple y no hay forma de evitarlo sin medir otra cosa.

## Qué se mide

1. **Top-1.** ¿Cambia? ¿Y cambia para bien? Cada perfil trae `claves` con lo que
   debería salir.
2. **La carrera objetivo, ¿estaba siquiera disponible?** En el brazo A se
   registra, sin gastar cuota, si la carrera objetivo sobrevivió el recorte en
   cada llamada. Es la prueba directa del mecanismo: si nunca estuvo entre las
   35, el modelo no pudo considerarla al preguntar.
3. **Latencia por llamada**, que es la queja concreta: hoy va de 3-4s a picos de
   10s. Se cronometra CADA llamada de producción por separado
   (`next-question` y `recommend`), y se reportan mediana y p95. Las llamadas
   del alumno simulado NO cuentan: no existen en producción.
4. **Costo real, con alquiler.** Sin filtro el catálogo es constante, así que la
   entrada de caché es estable y sirve a todos los alumnos; con filtro el top-35
   cambia con las respuestas y se crea un caché por llamada. Se cuenta
   `caches_nuevos` por sesión y se suma el alquiler aparte, porque `uso_tokens`
   NO lo registra y sin él el costo sale 38% por debajo del real (factura del
   2026-08-24). ⚠️ El `% cacheado` NO distingue los brazos: un caché recién
   creado ya reporta sus tokens como cacheados. **La métrica es el número de
   cachés.** Ver experiments/cache-compartido.md.

## Los perfiles

Cinco apuntan a carreras que la depuración marcó como rotas (la carrera correcta
no tiene señal en el banco, o la tiene por accidente) y tres son control: hoy
funcionan bien, y sirven para detectar que quitar el filtro no rompa lo que ya
servía.

## Presupuesto

Tope duro de $0.70 (`TOPE_USD`). Se revisa después de cada sesión y el script se
detiene solo, guardando lo que lleva. Con el brazo de control son **24 sesiones**
(8 perfiles x 3 brazos) en vez de 16. Estimado: ~$0.012 por sesión de A/A2 y
~$0.015 de B, contando al alumno simulado, o sea ~$0.33 mas el alquiler.

## Limitaciones, dichas de frente

- 8 perfiles ficticios no dan potencia estadística. Sirve para ver SI el
  mecanismo cambia, no para afirmar una mejora general.
- Circularidad parcial: el alumno simulado y el orientador son el mismo modelo.
- La latencia depende de la carga de Google en ese momento. Los brazos se corren
  intercalados (A, A2, B por perfil) justamente para que una racha lenta de
  Google no le caiga entera a uno solo.
- Con 8 perfiles, el control da una tasa de ruido sobre n=8. Es poco, pero es
  infinitamente mejor que la corrida anterior, que no tenia ninguno.
- La primera sesión de cada brazo paga el caché frío. Se reporta aparte.

## Uso

    uv run python experimento_filtro.py --self-check   # sin red, sin gastar
    uv run python experimento_filtro.py --seco         # solo el mecanismo, sin API
    uv run python experimento_filtro.py                # el A/B (gasta cuota)
    #   reanudable: si se corta, volver a correrlo retoma donde quedo
    uv run python experimento_filtro.py --perfil Byron
"""

import argparse
import json
import os
import statistics
import time

from dotenv import load_dotenv

# ANTES de importar app.recomendar (resuelve MODELO con os.getenv al importarse).
load_dotenv()

from app import filtro, preguntas, recomendar  # noqa: E402

from experimento_psicometrico import (  # noqa: E402
    DEPARTAMENTO,
    FIJAS,
    _responder,
    _texto_pregunta,
    acierta,
    catalogo,
)

DATA = os.path.join(os.path.dirname(__file__), "data")
SALIDA = os.path.join(DATA, "tests", "experimento_filtro_resultados.json")

# Tope de gasto. Se revisa después de cada sesión: si el acumulado lo pasa, el
# script para y guarda. Es el presupuesto autorizado para esta prueba.
# Subió de $0.45 a $0.70 al agregar el brazo de control: son 50% más sesiones.
TOPE_USD = 0.70

# Los tres brazos, en el orden en que se intercalan por perfil.
# A2 corre EXACTAMENTE lo mismo que A: es el control que mide cuánto se mueve el
# sistema solo, sin que cambie nada. Sin él, cualquier diferencia entre A y B se
# está sobreinterpretando (ver el piso de ruido de CLAUDE.md, 2026-08-23).
BRAZOS = (("A", True), ("A2", True), ("B", False))

# $/1M tokens-hora del SKU `cached content storage token hours`, confirmado en la
# factura del 2026-08-24 ($0.60 de $1.59). uso_tokens NO lo registra, así que hay
# que sumarlo aparte o el costo sale 38% por debajo del real.
PRECIO_ALQUILER_POR_1M_HORA = 1.00


# --- Los 8 perfiles -------------------------------------------------------
#
# 'objetivo' es el nombre EXACTO de la carrera del catálogo que este perfil
# debería recibir. Sirve para la medida 2 (¿sobrevivió el recorte?), que se
# calcula sin gastar cuota.
# 'claves' es lo que cuenta como acierto en el top-1 (subcadenas en minúsculas).
# 'roto' marca los perfiles cuya carrera correcta la depuración señaló como
# inalcanzable o alcanzable solo por accidente.

PERFILES = [
    {
        "nombre": "Byron",
        "roto": True,
        "objetivo": "Economía Empresarial",
        "claves": ["econom"],
        "nota": "no sobrevive el recorte en NINGUNA simulación; su unica palabra "
                "en comun con el banco es 'historia'",
        "contexto": (
            "18 anios, recien graduado de perito contador en Quetzaltenango. Le "
            "obsesiona entender por que hay tanta pobreza en Guatemala y por que "
            "unos paises se desarrollan y otros no. Lee sobre inflacion y sobre "
            "politica economica. Le gustan las estadisticas y hacer graficas con "
            "datos reales."),
        "guion": (
            "Habla de causas y estructuras, no de empresas. Si te preguntan por "
            "negocios, aclara que no te interesa administrar una empresa sino "
            "entender la economia de un pais. NO nombres ninguna carrera."),
    },
    {
        "nombre": "Kimberly",
        "roto": True,
        "objetivo": "Ingeniería en Telecomunicaciones",
        "claves": ["telecomunicac"],
        "nota": "entra por 'aire' (viaja a traves del aire), no por su chip de tecnologia",
        "contexto": (
            "17 anios, quinto bachillerato en Quetzaltenango. En su aldea la senial "
            "de internet es pesima y eso la enoja. Le fascina como viaja la "
            "informacion por el aire y por la fibra, las antenas, la cobertura. No "
            "le interesa programar aplicaciones, le interesa la infraestructura que "
            "conecta a la gente."),
        "guion": (
            "Cuando te pregunten por tecnologia, distingue: no quieres hacer "
            "software, quieres que la senial llegue. NO nombres ninguna carrera."),
    },
    {
        "nombre": "Dilan",
        "roto": True,
        "objetivo": "Criminología y Política Criminal",
        "claves": ["criminolog"],
        "nota": "raspa el borde del recorte (puesto 30 de 35); solo empata en 'justicia'",
        "contexto": (
            "19 anios, termino diversificado. Quiere entender POR QUE la gente "
            "delinque: las causas, la prevencion, las politicas de seguridad. Le "
            "interesa el analisis de patrones y el disenio de programas de "
            "prevencion, no litigar en tribunales ni el trabajo de laboratorio "
            "forense."),
        "guion": (
            "Si te ofrecen algo de leyes, aclara que no quieres ser abogado ni "
            "estar en un juzgado. Si te ofrecen laboratorio, aclara que no es lo "
            "tuyo. NO nombres ninguna carrera."),
    },
    {
        "nombre": "Yesenia",
        "roto": True,
        "objetivo": "Técnico Universitario en Radiología e Imágenes Diagnósticas",
        "claves": ["radiolog", "imágenes", "imagenes", "bio im"],
        "nota": "entra por 'estudio' (el estudio solicitado), que viene del chip "
                "'un estudio creativo'",
        "contexto": (
            "18 anios, bachillerato en ciencias y letras. Quiere trabajar en salud "
            "pero no aguanta el trato largo con pacientes ni la sangre. Le atrae el "
            "equipo medico: los aparatos, las maquinas de rayos X y de resonancia, "
            "la precision tecnica de operarlos. Quiere algo corto, de dos o tres "
            "anios."),
        "guion": (
            "Insiste en que quieres estar en salud pero con maquinas, no cuidando "
            "gente todo el dia. Menciona que quieres una carrera corta. NO nombres "
            "ninguna carrera."),
    },
    {
        "nombre": "Alfredo",
        "roto": True,
        "objetivo": "Profesorado en Inglés como Idioma Extranjero",
        "claves": ["inglés", "ingles", "idioma"],
        "nota": "no hay ningun chip de idiomas; entra por 'practica' (la practica "
                "constante del idioma)",
        "contexto": (
            "20 anios, termino magisterio. Aprendio ingles solo, viendo series y "
            "hablando con turistas en Xela. Da clases particulares de ingles a "
            "ninios del barrio y le encanta. Quiere dedicarse a ensenar idiomas."),
        "guion": (
            "Habla de idiomas y de ensenar. Si te ofrecen algo de comunicacion o "
            "medios, aclara que no quieres ser periodista. NO nombres ninguna "
            "carrera."),
    },
    {
        "nombre": "Josué",
        "roto": False,
        "objetivo": "Ingeniería en Ciencias y Sistemas",
        "claves": ["sistemas", "informátic", "informatic", "software", "comput"],
        "nota": "CONTROL: hoy acierta, aunque entre por los falsos amigos 'campo' y 'crear'",
        "contexto": (
            "17 anios, quinto bachillerato en computacion en Quetzaltenango. Arma "
            "paginas web y le paga un negocio de la zona por mantenerle el sistema "
            "de inventario. Disfruta resolver problemas de logica y aprender "
            "lenguajes nuevos solo."),
        "guion": "Responde con naturalidad. NO nombres ninguna carrera.",
    },
    {
        "nombre": "Marisol",
        "roto": False,
        "objetivo": "Enfermería",
        "claves": ["enfermer"],
        "nota": "CONTROL: sin senial especifica, solo la tocan 'salud', 'comunicacion' "
                "y 'hacer'",
        "contexto": (
            "18 anios, bachillerato en ciencias y letras. Cuido a su abuela enferma "
            "dos anios y descubrio que se le da bien. Quiere estar en un hospital, "
            "con pacientes, tomando decisiones rapidas bajo presion."),
        "guion": "Responde con naturalidad. NO nombres ninguna carrera.",
    },
    {
        "nombre": "Andrea",
        "roto": False,
        "objetivo": "Licenciatura en Ciencias Jurídicas y Sociales",
        "claves": ["jurídic", "juridic", "abogad", "derecho"],
        "nota": "CONTROL: 'justicia', 'leyes' y 'debate' si son senial legitima",
        "contexto": (
            "17 anios, quinto bachillerato. Es la que siempre discute en clase y "
            "gana. Le indigna la injusticia y le interesan los derechos humanos y "
            "el derecho indigena. Se imagina defendiendo a gente que no puede "
            "pagarse un abogado."),
        "guion": "Responde con naturalidad. NO nombres ninguna carrera.",
    },
]


# --- Los dos brazos -------------------------------------------------------

def _sin_filtro(respuestas, carreras, top=None):
    """Reemplazo de `preseleccionar` para el brazo B: no recorta nada.

    ponytail: monkeypatch en el experimento en vez de un flag en producción. Si
    el A/B sale a favor, el cambio de verdad es BORRAR la llamada en
    `preguntas.siguiente_pregunta`, no agregar una bifurcación que mantener.
    """
    return carreras


def _solo_etiquetas(respuesta: str, opciones: list) -> str:
    """Lo que producción guarda de una pregunta fija: las ETIQUETAS elegidas, no
    la prosa.

    El alumno simulado contesta con un párrafo ("Analizando datos, ideas y
    lógica. Es que me la paso viendo por qué el país no avanza..."). Guardar ese
    párrafo le regala al filtro un vocabulario que un alumno real, que solo hace
    clic en unos chips, nunca produce, y eso infla al brazo con filtro. En
    Chat.jsx lo que se guarda es la etiqueta de cada opción marcada, así que aquí
    se recorta igual. Si no marcó ninguna conocida, se deja el texto tal cual:
    ese es el caso de 'Otro / especificar'.
    """
    norm = respuesta.lower()
    elegidas = [o for o in opciones if o.lower() in norm]
    return ", ".join(elegidas) if elegidas else respuesta.strip()


def _sesion(perfil, cat, con_filtro, brazo=None):
    """Una conversación completa de producción, cronometrada llamada por llamada.

    Devuelve (resultado, log). El log trae, por cada llamada de producción, los
    segundos que tardó y sus tokens. Las llamadas del alumno simulado se
    cronometran aparte y NO entran en la latencia reportada.

    `brazo` se pasa explícito porque A y A2 corren la MISMA configuración
    (con_filtro=True) y necesitan session_id distinto: si compartieran el id,
    compartirían el estado de cobertura y A2 dejaría de ser una repetición
    independiente.
    """
    if brazo is None:
        brazo = "A" if con_filtro else "B"
    # Cachés que ya existían antes de esta sesión: lo que aparezca de más es lo
    # que este alumno tuvo que crear (los que reusa no cuentan). Ver
    # experiments/cache-compartido.md.
    caches_antes = set(recomendar._caches)
    respuestas = {"nombre": perfil["nombre"], "departamento": DEPARTAMENTO}
    log = {"brazo": brazo, "perfil": perfil["nombre"], "llamadas": [],
           "fijas": {}, "adaptativas": [], "objetivo_en_candidatas": []}

    # Las 4 fijas: las contesta el alumno simulado, sin pasar por el orientador.
    for clave, texto, opciones in FIJAS:
        previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
        r = _responder(perfil, f"{texto}\nOpciones: {' / '.join(opciones)}", previo)
        etiquetas = _solo_etiquetas(r, opciones)
        respuestas[clave] = etiquetas
        log["fijas"][clave] = {"elegido": etiquetas, "dijo": r}
        print(f"    [fija:{clave}] -> {etiquetas[:80]}")

    # El pre-filtro se quitó de producción el 2026-08-24 (cache-compartido.md
    # §9), así que preguntas ya no expone `preseleccionar` y AMBOS brazos ven el
    # catálogo completo: el A/B de calidad quedó cerrado. El monkeypatch se
    # conserva por si se reintroduce el filtro; con getattr no crashea si no está.
    original = getattr(preguntas, "preseleccionar", None)
    if not con_filtro and original is not None:
        preguntas.preseleccionar = _sin_filtro
    sid = f"filtro-{brazo}-{perfil['nombre']}"
    preguntas._COBERTURA_POR_SESION.pop(sid, None)
    try:
        for _ in range(preguntas.MAX_ADAPTATIVAS):
            # Medida 2, gratis: ¿la carrera objetivo sobrevive el recorte AHORA?
            # Se calcula siempre (también en el brazo B) para poder decir en qué
            # momento de la conversación entra o sale.
            candidatas = filtro.preseleccionar(respuestas, cat)
            log["objetivo_en_candidatas"].append(
                any(c.nombre == perfil["objetivo"] for c in candidatas))

            t0 = time.perf_counter()
            paso, uso = preguntas.siguiente_pregunta(respuestas, cat, sid)
            dt = time.perf_counter() - t0
            log["llamadas"].append({"tipo": "next-question", "segundos": round(dt, 2), **uso})
            print(f"    [{brazo}] next-question {dt:5.2f}s  "
                  f"({uso['prompt_tokens']:,} prompt / {uso['cached_tokens']:,} cache)")

            if paso.terminado:
                log["adaptativas"].append({"terminado": True,
                                           "ranking": [r.model_dump() for r in paso.ranking]})
                break
            texto = _texto_pregunta(paso)
            previo = "\n".join(f"P: {k}\nR: {v}" for k, v in respuestas.items() if k != "nombre")
            respuesta = _responder(perfil, texto, previo)
            respuestas[paso.pregunta_texto] = respuesta
            log["adaptativas"].append({
                "dimension": paso.dimension_objetivo,
                "pregunta": paso.pregunta_texto,
                "opciones": [o.label for o in paso.opciones],
                "respuesta": respuesta,
                "ranking": [r.model_dump() for r in paso.ranking],
            })
            print(f"       [{paso.dimension_objetivo or '-'}] {paso.pregunta_texto[:65]}")
            print(f"       -> {respuesta[:80]}")
    finally:
        if original is not None:
            preguntas.preseleccionar = original

    t0 = time.perf_counter()
    res, uso = recomendar.recomendar(respuestas, cat)
    dt = time.perf_counter() - t0
    log["llamadas"].append({"tipo": "recommend", "segundos": round(dt, 2), **uso})
    log["caches_nuevos"] = len(set(recomendar._caches) - caches_antes)
    print(f"    [{brazo}] recommend      {dt:5.2f}s   "
          f"(caches nuevos de este alumno: {log['caches_nuevos']})")
    return res, log


def _top(res, n=3):
    """Los primeros n nombres de carrera del resultado, sea dict o modelo."""
    carreras = res["carreras"] if isinstance(res, dict) else res.carreras
    out = []
    for c in carreras[:n]:
        nombre = c["carrera"] if isinstance(c, dict) else c.carrera
        af = c["afinidad"] if isinstance(c, dict) else c.afinidad
        out.append({"carrera": nombre, "afinidad": af})
    return out


# --- Estadística de la corrida --------------------------------------------

def _latencias(logs, tipo=None, saltar_primera=False):
    """Segundos de todas las llamadas de producción de esos logs."""
    vistos = set()
    out = []
    for lg in logs:
        primera = True
        for ll in lg["llamadas"]:
            if tipo and ll["tipo"] != tipo:
                continue
            if saltar_primera and lg["brazo"] not in vistos:
                vistos.add(lg["brazo"])
                primera = False
                continue
            out.append(ll["segundos"])
        del primera
    return out


def _p(valores, q):
    if not valores:
        return 0.0
    v = sorted(valores)
    i = min(len(v) - 1, int(round(q * (len(v) - 1))))
    return v[i]


def _resumen_brazo(logs, brazo):
    lg = [x for x in logs if x["brazo"] == brazo]
    if not lg:
        return None
    todas = _latencias(lg)
    nq = _latencias(lg, "next-question")
    rec = _latencias(lg, "recommend")
    prompt = sum(ll["prompt_tokens"] for x in lg for ll in x["llamadas"])
    cache = sum(ll["cached_tokens"] for x in lg for ll in x["llamadas"])
    out = sum(ll["output_tokens"] for x in lg for ll in x["llamadas"])
    caches = sum(x.get("caches_nuevos", 0) for x in lg)
    # Alquiler: cada caché distinto renta su contenido 1h (TTL de _get_cache).
    # Se aproxima su tamaño con el promedio de tokens cacheados por llamada.
    tok_por_cache = cache / max(len(todas), 1)
    alquiler = caches * tok_por_cache * PRECIO_ALQUILER_POR_1M_HORA / 1e6
    tokens_usd = recomendar.costo_usd(
        {"prompt_tokens": prompt, "cached_tokens": cache, "output_tokens": out})
    return {
        "sesiones": len(lg),
        "llamadas": len(todas),
        "seg_mediana": round(statistics.median(todas), 2) if todas else 0,
        "seg_p95": round(_p(todas, 0.95), 2),
        "seg_max": round(max(todas), 2) if todas else 0,
        "nq_mediana": round(statistics.median(nq), 2) if nq else 0,
        "nq_p95": round(_p(nq, 0.95), 2),
        "rec_mediana": round(statistics.median(rec), 2) if rec else 0,
        "seg_por_sesion": round(sum(todas) / len(lg), 1),
        "prompt_tokens": prompt,
        "cached_tokens": cache,
        "pct_cacheado": round(100 * cache / prompt, 1) if prompt else 0,
        "caches": caches,
        "costo_usd": round(tokens_usd, 4),
        "alquiler_usd": round(alquiler, 4),
        "total_usd": round(tokens_usd + alquiler, 4),
    }


def _gastado():
    total = {k: sum(g[k] for g in recomendar._GASTO.values())
             for k in ("llamadas", "prompt_tokens", "output_tokens", "cached_tokens")} \
        if recomendar._GASTO else {"prompt_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
    return recomendar.costo_usd(total)


def correr(solo=None):
    cat = catalogo()
    cat = [c for c in cat if c.departamento == DEPARTAMENTO]
    perfiles = [p for p in PERFILES if not solo or p["nombre"].lower() == solo.lower()]

    # Reanudable: si Gemini devuelve 503 a media corrida, lo hecho no se repite.
    hechos = {}
    if os.path.exists(SALIDA):
        hechos = {(r["perfil"], r["brazo"]): r
                  for r in json.load(open(SALIDA, encoding="utf-8"))["sesiones"]}
        print(f"Reanudando: {len(hechos)} sesiones ya hechas en {SALIDA}")

    resultados = list(hechos.values())
    detenido = None
    # Intercalado A,A2,B por perfil: una racha lenta de Google no le cae entera a
    # un solo brazo. A2 es el BRAZO DE CONTROL: misma configuración que A, corrida
    # aparte. A vs A2 mide el ruido del sistema; A vs B solo significa algo si su
    # diferencia supera esa. Ver el piso de ruido de CLAUDE.md.
    for p in perfiles:
        for brazo, con_filtro in BRAZOS:
            if (p["nombre"], brazo) in hechos:
                continue
            if _gastado() >= TOPE_USD:
                detenido = f"tope de ${TOPE_USD} alcanzado antes de {p['nombre']}/{brazo}"
                break
            print(f"\n=== {p['nombre']} · brazo {brazo} "
                  f"({'con filtro' if con_filtro else 'SIN filtro'}"
                  f"{', CONTROL' if brazo == 'A2' else ''}) ===")
            res, log = _sesion(p, cat, con_filtro, brazo)
            top3 = _top(res)
            log.update({
                "top3": top3,
                "top1": top3[0]["carrera"] if top3 else "",
                "acierta": acierta(top3[0]["carrera"], p["claves"]) if top3 else False,
                "objetivo_en_top3": any(
                    t["carrera"] == p["objetivo"] for t in top3),
                "objetivo": p["objetivo"],
                "roto": p["roto"],
            })
            resultados.append(log)
            json.dump({"sesiones": resultados}, open(SALIDA, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"    top-1: {log['top1']}  ({'ACIERTA' if log['acierta'] else 'falla'})"
                  f"   gastado: ${_gastado():.4f}")
        if detenido:
            break

    _reporte(resultados, detenido)
    _borrar_caches()
    return resultados


def _borrar_caches():
    """Borra los CachedContent que la corrida creó. Sin esto, cada caché sigue
    rentando almacenamiento ($1/1M tok/hora) hasta que expira su TTL de 1h: la
    causa del susto del 2026-08-24, cuando una corrida dejó decenas de cachés
    rentando y el gasto apareció horas después por la latencia de la consola.
    Los nombres viven en recomendar._caches, indexados por key_label."""
    from google import genai

    clientes = {"primaria": os.getenv("GEMINI_API_KEY"),
                "respaldo": os.getenv("GEMINI_API_KEY_RESPALDO")}
    borrados = 0
    for (_model, _hash, key_label), name in list(recomendar._caches.items()):
        if not name or not clientes.get(key_label):
            continue
        try:
            genai.Client(api_key=clientes[key_label]).caches.delete(name=name)
            borrados += 1
        except Exception as e:  # noqa: BLE001
            print(f"  no se pudo borrar {name}: {type(e).__name__}")
    print(f"Caches borrados: {borrados} (dejan de rentar almacenamiento)")


def _reporte(logs, detenido=None):
    print("\n" + "=" * 72)
    print("RESULTADO A/B DEL PRE-FILTRO")
    print("=" * 72)
    if detenido:
        print(f"!! CORRIDA DETENIDA: {detenido}")

    por = {(x["perfil"], x["brazo"]): x for x in logs}
    nombres = [p["nombre"] for p in PERFILES if (p["nombre"], "A") in por and (p["nombre"], "B") in por]

    # 0) EL CONTROL PRIMERO. A2 corre lo mismo que A, así que todo lo que cambie
    # entre ellos es ruido del sistema. Si A vs B no supera esto, no hay efecto
    # que reportar por más bonita que se vea la tabla de abajo.
    ctrl_n = [p["nombre"] for p in PERFILES
              if (p["nombre"], "A") in por and (p["nombre"], "A2") in por]
    ruido = None
    if ctrl_n:
        ruido = sum(por[(n, "A")]["top1"] != por[(n, "A2")]["top1"] for n in ctrl_n)
        print(f"\n0) PISO DE RUIDO (control A vs A2, misma configuración)")
        for n in ctrl_n:
            a, a2 = por[(n, "A")], por[(n, "A2")]
            igual = "==" if a["top1"] == a2["top1"] else "!="
            print(f"{n:10s} {a['top1'][:30]:32s} {igual} {a2['top1'][:30]:32s}")
        print(f"\n   top-1 distinto SIN cambiar nada: {ruido}/{len(ctrl_n)}")

    print("\n1) TOP-1 Y DISPONIBILIDAD DE LA CARRERA OBJETIVO")
    print(f"{'perfil':10s} {'A: con filtro':32s} {'B: sin filtro':32s} {'obj en 35':9s}")
    cambios = a_ok = b_ok = 0
    for n in nombres:
        a, b = por[(n, "A")], por[(n, "B")]
        disp = a["objetivo_en_candidatas"]
        marca = f"{sum(disp)}/{len(disp)}" if disp else "-"
        if a["top1"] != b["top1"]:
            cambios += 1
        a_ok += a["acierta"]
        b_ok += b["acierta"]
        print(f"{n:10s} {a['top1'][:30]:32s} {b['top1'][:30]:32s} {marca:9s}")
        print(f"{'':10s} {'ACIERTA' if a['acierta'] else 'falla':32s} "
              f"{'ACIERTA' if b['acierta'] else 'falla':32s}")
    if nombres:
        print(f"\n   Aciertos: A {a_ok}/{len(nombres)}   B {b_ok}/{len(nombres)}"
              f"   |  top-1 distinto en {cambios}/{len(nombres)}")
        if ruido is not None:
            tasa_ruido = ruido / len(ctrl_n)
            tasa_efecto = cambios / len(nombres)
            print(f"   Contra el control: efecto {cambios}/{len(nombres)} vs "
                  f"ruido {ruido}/{len(ctrl_n)}  ->  "
                  + ("EL RUIDO IGUALA O SUPERA AL EFECTO, no hay señal de calidad"
                     if tasa_efecto <= tasa_ruido
                     else "el efecto supera al ruido, mirar si es para bien"))
        rotos = [n for n in nombres if por[(n, "A")]["roto"]]
        if rotos:
            ra = sum(por[(n, "A")]["acierta"] for n in rotos)
            rb = sum(por[(n, "B")]["acierta"] for n in rotos)
            print(f"   Solo los perfiles 'rotos': A {ra}/{len(rotos)}   B {rb}/{len(rotos)}")
        ctrl = [n for n in nombres if not por[(n, "A")]["roto"]]
        if ctrl:
            ca = sum(por[(n, "A")]["acierta"] for n in ctrl)
            cb = sum(por[(n, "B")]["acierta"] for n in ctrl)
            print(f"   Solo los control (regresión): A {ca}/{len(ctrl)}   B {cb}/{len(ctrl)}")

    print("\n2) LATENCIA Y COSTO")
    print(f"{'':16s} {'A: con filtro':>16s} {'A2: control':>16s} {'B: sin filtro':>16s}")
    ra, r2, rb = (_resumen_brazo(logs, "A"), _resumen_brazo(logs, "A2"),
                  _resumen_brazo(logs, "B"))
    if ra and rb:
        vacio = {k: "-" for k in ra}
        for etiq, k in [("sesiones", "sesiones"), ("llamadas", "llamadas"),
                        ("mediana (s)", "seg_mediana"), ("p95 (s)", "seg_p95"),
                        ("max (s)", "seg_max"),
                        ("next-q mediana", "nq_mediana"), ("next-q p95", "nq_p95"),
                        ("recommend med.", "rec_mediana"),
                        ("seg/sesión", "seg_por_sesion"),
                        ("prompt tok", "prompt_tokens"), ("% cacheado", "pct_cacheado"),
                        ("CACHES", "caches"),
                        ("costo tokens", "costo_usd"),
                        ("alquiler", "alquiler_usd"),
                        ("TOTAL USD", "total_usd")]:
            print(f"{etiq:16s} {ra[k]:>16} {(r2 or vacio)[k]:>16} {rb[k]:>16}")
        if ra["seg_por_sesion"]:
            print(f"\n   Sobrecosto de tiempo por sesión: "
                  f"{rb['seg_por_sesion'] - ra['seg_por_sesion']:+.1f}s "
                  f"({100 * rb['seg_por_sesion'] / ra['seg_por_sesion'] - 100:+.0f}%)")
        if ra["total_usd"]:
            por_a = ra["total_usd"] / ra["sesiones"]
            por_b = rb["total_usd"] / rb["sesiones"]
            print(f"   Costo por sesión (con alquiler): A ${por_a:.4f}  B ${por_b:.4f}  "
                  f"->  B es el {100 * por_b / por_a:.0f}% de A")
            print(f"   Solo tokens, que es lo que veria uso_tokens: "
                  f"A ${ra['costo_usd'] / ra['sesiones']:.4f}  "
                  f"B ${rb['costo_usd'] / rb['sesiones']:.4f}")

    print(recomendar.resumen_gasto())
    print(f"\nGastado en total: ${_gastado():.4f} de ${TOPE_USD} autorizados")
    print(f"Detalle completo en {SALIDA}")


# --- Corrida seca: el mecanismo, sin gastar un centavo --------------------

def seco():
    """Sin API: el MEJOR puesto que la carrera objetivo de cada perfil puede
    alcanzar eligiendo opciones del banco.

    Marcar todas las opciones a la vez NO es el máximo de señal: el puntaje es
    una suma y el ranking es relativo, así que agregar opciones que favorecen a
    otras carreras empuja la propia hacia abajo. Por eso se barre: cada opción
    sola, y después cada par de opciones. Si con el mejor par la carrera sigue
    fuera de las 35, ninguna conversación real la va a rescatar.
    """
    import itertools

    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    print(f"Catálogo de {DEPARTAMENTO}: {len(cat)} filas, "
          f"{len({c.nombre for c in cat})} carreras únicas. Recorte a "
          f"{filtro.TOP_DEFAULT}.\n")
    opciones = [o for _, _, ops in FIJAS for o in ops]
    combos = [(o,) for o in opciones] + list(itertools.combinations(opciones, 2))

    def puesto_de(objetivo, respuesta):
        top = filtro.preseleccionar({"gustos": respuesta}, cat)
        return next((i for i, c in enumerate(top, 1) if c.nombre == objetivo), None)

    print(f"{'perfil':10s} {'carrera objetivo':46s} {'mejor':>6s}  con qué opciones")
    for p in PERFILES:
        mejor, con = None, None
        for combo in combos:
            q = puesto_de(p["objetivo"], " ".join(combo))
            if q and (mejor is None or q < mejor):
                mejor, con = q, combo
        print(f"{p['nombre']:10s} {p['objetivo'][:44]:46s} "
              f"{(mejor if mejor else 'FUERA'):>6}  "
              f"{' + '.join(c[:34] for c in con) if con else '(ninguna combinación la mete)'}")
    print(f"\n({len(combos)} combinaciones probadas por perfil: cada opción sola y "
          "cada par.\n Es la mejor jugada posible sin escribir en 'Otro'.)")


def _self_check():
    """Sin red: valida el mecanismo del experimento, no sus resultados."""
    cat = [c for c in catalogo() if c.departamento == DEPARTAMENTO]
    assert len(cat) > filtro.TOP_DEFAULT, "el catálogo debe ser mayor que el recorte"

    # El brazo B realmente no recorta, y el A sí.
    assert len(_sin_filtro({"gustos": "x"}, cat)) == len(cat)
    assert len(filtro.preseleccionar({"gustos": "tecnología"}, cat)) == filtro.TOP_DEFAULT

    # El monkeypatch entra y sale, solo si el filtro sigue existiendo. Se quitó
    # de producción el 2026-08-24, así que hoy este bloque no aplica (getattr).
    original = getattr(preguntas, "preseleccionar", None)
    if original is not None:
        preguntas.preseleccionar = _sin_filtro
        assert preguntas.preseleccionar is not original
        preguntas.preseleccionar = original
        assert preguntas.preseleccionar is original, "el finally debe restaurar el filtro"

    # Cada perfil apunta a una carrera que EXISTE en el catálogo (si no, la
    # medida 2 mediría siempre 'FUERA' por un typo).
    nombres = {c.nombre for c in cat}
    for p in PERFILES:
        assert p["objetivo"] in nombres, f"objetivo inexistente: {p['objetivo']}"
        assert acierta(p["objetivo"], p["claves"]), \
            f"las claves de {p['nombre']} no reconocen su propio objetivo"

    # Percentiles y latencias.
    assert _p([1, 2, 3, 4, 5], 0.95) == 5
    assert _p([], 0.5) == 0.0
    falso = [{"brazo": "A", "llamadas": [{"tipo": "next-question", "segundos": 3.0},
                                         {"tipo": "recommend", "segundos": 9.0}]}]
    assert _latencias(falso) == [3.0, 9.0]
    assert _latencias(falso, "recommend") == [9.0]

    # Las fijas guardan etiquetas, no prosa: es lo que hace Chat.jsx y es lo
    # único que el filtro puede emparejar en producción.
    ops = ["Matemáticas y números", "Tecnología y computación", "Salud y cuidar personas"]
    assert _solo_etiquetas("Tecnología y computación. Es que me la paso programando", ops) \
        == "Tecnología y computación"
    assert _solo_etiquetas("Matemáticas y números, junto con Tecnología y computación", ops) \
        == "Matemáticas y números, Tecnología y computación"
    # sin etiqueta reconocible = el alumno escribió en 'Otro': se guarda tal cual
    assert _solo_etiquetas("  la música y la danza  ", ops) == "la música y la danza"

    # _top acepta dict o modelo.
    assert _top({"carreras": [{"carrera": "X", "afinidad": 40},
                              {"carrera": "Y", "afinidad": 30}]}, 1) == \
        [{"carrera": "X", "afinidad": 40}]

    # El tope de gasto es el autorizado y se lee sin llamadas hechas.
    assert TOPE_USD == 0.70
    assert _gastado() == 0.0

    # El control tiene que ser IDENTICO a A en configuracion y DISTINTO en
    # etiqueta: si comparten session_id comparten el estado de cobertura y A2
    # deja de ser una repeticion independiente.
    assert dict(BRAZOS)["A2"] == dict(BRAZOS)["A"] is True, "A2 corre con filtro, igual que A"
    assert dict(BRAZOS)["B"] is False
    assert len({b for b, _ in BRAZOS}) == 3, "tres etiquetas distintas"

    # _sesion respeta la etiqueta que se le pasa (de ahi sale el session_id).
    import inspect
    assert "brazo" in inspect.signature(_sesion).parameters

    print("ok: mecanismo del experimento validado, sin gastar cuota")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-check", action="store_true", help="valida el script, sin red")
    ap.add_argument("--seco", action="store_true", help="solo el mecanismo del filtro, sin API")
    ap.add_argument("--perfil", help="corre un solo perfil")
    a = ap.parse_args()
    if a.self_check:
        _self_check()
    elif a.seco:
        seco()
    else:
        correr(a.perfil)
