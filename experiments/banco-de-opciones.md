# Revisión del banco de opciones contra el catálogo completo

**Estado:** APLICADO y MEDIDO 2026-08-23. El banco pasó de 15 a 25 chips en
`gustos` y se reescribieron 5 etiquetas más. La medición está abajo: no prueba
una mejora general, sí prueba que el banco nuevo representa personas que el
viejo no podía representar.

Herramienta: `backend/cobertura_banco.py` (no gasta cuota).

---

## La pregunta

¿Qué temas del catálogo NO tiene forma de nombrar el alumno con las opciones que
le damos?

La depuración anterior (ver [filtro-catalogo-ab.md](filtro-catalogo-ab.md)) fue
carrera por carrera y sobrecontaba: cinco Ingenierías en Sistemas con el mismo
`perfil` son UN tema, no cinco. Acá el clúster es el perfil, que el catálogo ya
agrupa con `perfil_id`: **147 carreras, 90 temas**.

## Por qué importa, dicho con precisión

**No es por el pre-filtro.** El A/B midió que el filtro no mueve el resultado
final, porque `recomendar()` ve el catálogo completo. Si la justificación fuera
esa, este trabajo no se haría.

Importa por dos cosas distintas:

1. **El alumno tiene que reconocerse.** Si le gusta la música, o los idiomas, o
   los animales, y ninguna opción lo nombra, el chip "Otro / especificar" es la
   única salida y hay que saber usarlo.
2. **El texto de las opciones es la señal que lee Gemini.** No por
   emparejamiento de palabras, por significado.

Corolario que conviene no olvidar al editar esto: **las etiquetas se redactan
para el alumno, no para el filtro.** Hubo un intento de reescribirlas para que
empataran con el vocabulario de los perfiles y salía español forzado
("Comunicar, crear, diseñar o investigación"); se descartó.

## Lo que había

**18 de 90 temas** sin ninguna palabra que los tocara, cubriendo 25 carreras:

| Tema | Carreras | Cómo entraba |
|---|---:|---|
| Enfermería | 4 | nada |
| Imágenes médicas (radiología, bio imágenes) | 4 | `estudio` ("el estudio solicitado") |
| Educación, dirección de centros | 4 | `centro`, `liderar` |
| Ciencias de la Educación / Profesorados | 3 | `psicología` |
| Idiomas (inglés x2, maya) | 3 | nada / `escritura` |
| Telecomunicaciones | 2 | `aire` ("viaja a través del aire") |
| Economía y Economía Empresarial | 2 | `realidad` |
| Educación de Lenguaje / de Física y Matemática | 2 | `medio` ("nivel medio") |
| Electrónica | 1 | `funcionan` |
| Agronomía | 1 | nada (el chip decía "agricultura", el perfil dice "agropecuarias", "agronegocios") |
| Música | 1 | nada |
| Teología | 1 | nada |
| Profesorado en TIC | 1 | nada |

Más los cubiertos por un verbo suelto: Comercio Internacional (`libre`),
Relaciones Internacionales (`conflictos`), Psicología Educativa (`trabajar`),
Producción Audiovisual (`movimiento`), Fisioterapia (`directo`).

## Lo que se cambió

**10 chips nuevos en `gustos`**, cada uno por un tema que no tenía forma de
nombrarse:

`Equipos médicos, laboratorio e imágenes` · `Cuerpo, deporte y rehabilitación` ·
`Animales y su cuidado` · `Economía, pobreza y desarrollo del país` ·
`Comercio, política y otros países` · `Música, danza y artes escénicas` ·
`Idiomas y otras culturas` · `Organizar y dirigir equipos o instituciones` ·
`Redes, señal y electrónica` · `Fe, religión y espiritualidad`

**5 etiquetas reescritas**, donde la palabra natural en español además nombra
mejor el tema:

| Antes | Ahora | Por qué |
|---|---|---|
| Salud y cuidar personas | Salud, cuidados y atención a pacientes | era el único chip de enfermería y no la nombraba |
| Negocios, dinero y emprender | Negocios, dinero y emprendimiento | |
| Enseñar y educar | Enseñanza, docencia y educación | la familia más grande del catálogo (14 carreras) colgaba de aquí |
| Medio ambiente y agricultura | Ambiente, agricultura y agronegocios | agronomía es agroindustria, no solo cultivo |
| En medios, un estudio creativo o diseñando | En medios de comunicación o diseñando | `estudio` era por donde entraban Radiología y Teología |

Y en `impacto`, "investigar la realidad" pasó a "hacer investigación", que es lo
que el alumno reconoce.

## Resultado

**De 18 temas descubiertos a 3.** Los 3 que quedan no son huecos de tema, son el
techo conocido de `filtro.py`, que empareja forma exacta de palabra sin lematizar:

- Idioma Maya: el perfil dice `idioma` y `cultura`, el chip dice `idiomas` y `culturas`.
- Profesorado en TIC: el perfil dice `cómputo` y `computadoras`, el chip dice `computación`.
- Educación de la Comunicación y Lenguaje: falso negativo de la propia
  herramienta, que marca `escritura` como falso amigo porque lo es en el perfil
  del idioma maya, pero acá es legítima ("difusión literaria").

No se siguió persiguiendo formas de palabra: sería contorsionar el español para
un filtro que ya se midió que no decide el resultado.

## Pendiente aparte: el móvil

**Mirar el móvil.** `.options.choices.chips` cae a 1 columna abajo de 560px:
25 chips son 25 filas de scroll. La palanca es dejarlo en 2 columnas también en
móvil, no recortar el banco.

---

## La medición (2026-08-23)

Script: `backend/experimento_banco.py` · 6 personas · dos rondas · $0.20.

### Por qué NO se midió con `claves`

El primer diseño puntuaba con `claves`: se define de antemano qué carrera
debería salir y se cuenta si el top-1 la contiene. Para un banco de opciones eso
está roto, y hay que decirlo porque es tentador reusarlo:

1. El perfil del alumno simulado se escribe para llevar a esa carrera, así que
   las respuestas ya vienen elegidas para que ese resultado gane.
2. Si el brazo nuevo propone una carrera **distinta pero igual de sensata**, la
   métrica la cuenta como fallo.

El banco viejo ganaba por construcción. Se cambió a **personas** descritas sin
ninguna carrera en mente (un self-check verifica que ningún perfil nombre
carreras ni repita etiquetas del banco) y un **juez ciego** que puntúa coherencia
con la persona, con el orden de las listas sorteado.

### El arnés tenía un sesgo, y corregirlo dio vuelta el marcador

**Ronda 1:** el alumno simulado contestaba las fijas con un párrafo y la etiqueta
se recuperaba buscándola como subcadena. Cuando parafraseaba, la respuesta se
guardaba como texto libre: **15 de 48 veces**, y asimétricamente (6 en A, 9 en B),
porque son las etiquetas NUEVAS las que no se reconocían. El sesgo iba contra el
brazo que se estaba probando.

**Ronda 2:** `_marcar()` pide índices de las opciones, que es lo que hace el
alumno real en `Chat.jsx` (toca chips, y solo escribe si usa 'Otro'). Caídas a
texto libre: **0 de 48**.

| | A (banco viejo) | B (banco nuevo) |
|---|---:|---:|
| Ronda 1, arnés sesgado | 3 | 2 (+1 empate) |
| **Ronda 2, arnés corregido** | **2** | **4** |
| Coherencia media R2 (1-5) | 4.17 | 4.33 |
| Top-1 distinto entre brazos, R2 | 4 de 6 | |

**Las dos rondas están dentro del ruido y ninguna prueba una mejora general.**
De 6 personas, 3 cambiaron de veredicto entre rondas. Con el piso de ruido
conocido (3 de 8 perfiles cambian solos), un 2-4 no es un resultado. Lo que sí
quedó demostrado es que **el marcador de la ronda 1 no era confiable**.

### Lo único que se repitió en las dos rondas

**Wendy** toca marimba desde los 12. `Profesorado en Educación Artística (Música
y Danza)` aparece en el top-3 del banco nuevo en **las dos rondas** (top-1 en la
1, top-2 en la 2) y en el del banco viejo en **ninguna de las dos**. Con el banco
viejo su música se pierde: marca "Arte, diseño y creatividad" y sale
psicopedagogía o educación primaria.

Esa carrera existe en el catálogo y antes no había forma de llegar a ella. Es la
afirmación que este experimento sostiene: **el banco nuevo representa gente que
el viejo no podía representar.** No sostiene que recomiende mejor en general.

Los chips nuevos se marcan: las 6 personas usaron al menos uno en la ronda 2.

### Evidencia en contra, sin maquillarla

- **Rosa** (quiere salud pero con aparatos, no trato largo con pacientes). En la
  ronda 2 el banco nuevo le dio Fisioterapia, **Ingeniería Mecánica Industrial**
  y **Cirujano Dentista**, peor que el viejo. Más chips también puede dispersar.
- **Kevin.** El banco nuevo perdió las dos rondas. En la 1 metió Administración
  de Empresas, que él había rechazado explícitamente.
- **El juez no es un instrumento estable.** Trabajo Social como top-1 le pareció
  un acierto en una ronda y lo castigó en la otra, según el resto de la lista.
  Es una segunda opinión, no un veredicto.

### Veredicto

El banco nuevo **se queda**, por la razón por la que se hizo: cubre 18 temas del
catálogo que no tenían forma de nombrarse, los chips se usan, y el caso Wendy se
repitió. **No se afirma que mejore el ranking**, porque no se midió eso.

Antes de subirlo a MiOrienta conviene mirar el caso Rosa con más n: si dispersar
resulta ser un patrón y no un caso, la palanca es afinar la redacción de los
chips de salud, no volver al banco de 15.

### Lo que este experimento deja para el resto del repo

El diseño "personas + juez ciego + coherencia" sirve para releer experimentos
viejos cuyo veredicto dependía de `claves` fijadas de antemano. En particular
[adaptativas-desempate.md](adaptativas-desempate.md), donde la pregunta no es
"¿acertó?" sino "¿la pregunta extra separó dos carreras hermanas?".

