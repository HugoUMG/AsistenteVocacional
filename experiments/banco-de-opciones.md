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

Script: `backend/experimento_banco.py` · $0.1012 · 6 personas, 12 sesiones.

### Por qué NO se midió con `claves`

El primer diseño puntuaba con `claves`: se define de antemano qué carrera
debería salir y se cuenta si el top-1 la contiene. Para un banco de opciones eso
está roto, y hay que decirlo porque es tentador reusarlo:

1. El perfil del alumno simulado se escribe para llevar a esa carrera, así que
   las respuestas ya vienen elegidas para que ese resultado gane.
2. Si el brazo nuevo propone una carrera **distinta pero igual de sensata**, la
   métrica la cuenta como fallo.

El banco viejo ganaba por construcción. Así que se cambió a: **personas**
descritas sin ninguna carrera en mente (un self-check verifica que ningún perfil
nombre carreras ni repita etiquetas del banco), y un **juez ciego** que puntúa
COHERENCIA con la persona, con el orden de las listas sorteado.

### Marcador

| | A (banco viejo) | B (banco nuevo) |
|---|---:|---:|
| Juez ciego prefiere | 3 | 2 (+1 empate) |
| Coherencia media (1-5) | 4.33 | 4.17 |
| Top-1 distinto entre brazos | 3 de 6 | |

**El marcador no dice nada** con n=6 y el piso de ruido conocido (3 de 8
perfiles cambian solos entre corridas). Lo informativo son los casos.

### El caso que justifica el cambio: Wendy

Toca marimba y guitarra desde los 12, organiza los ensayos, le gusta enseñarle a
los más chiquitos.

| | Marcó | Recomendación top-1 |
|---|---|---|
| A, banco viejo | "Arte, diseño y creatividad" | Profesorado en Psicopedagogía (35%) |
| B, banco nuevo | "Música, danza y artes escénicas" | **Profesorado en Educación Artística (Música y Danza)** (45%) |

Con el banco viejo su música **desaparece**: el top-3 entero es psicopedagogía.
El juez ciego le dio a B un 5 contra 3, y su razón fue literalmente que la otra
lista "ignora por completo su faceta artística y musical".

Educación Artística existe en el catálogo. Antes no había forma de llegar a ella.

### Los chips nuevos se usan

5 de 6 personas marcaron al menos uno: Elmer "Redes, señal y electrónica", Rosa
"Equipos médicos, laboratorio e imágenes", Kevin "Economía, pobreza y desarrollo
del país", Diego "Cuerpo, deporte y rehabilitación" y "Animales y su cuidado".
No son decorativos.

### Dónde ganó el banco viejo, sin maquillarlo

- **Kevin.** B puso Economía de top-1 (mejor que A, que la puso de 2), pero metió
  Administración de Empresas de 3, y Kevin había dicho que lo administrativo lo
  aburre. El juez castigó eso y tiene razón.
- **Ixchel.** Gana A, pero **su brazo B está contaminado**: las 4 respuestas fijas
  cayeron a texto libre porque el alumno simulado parafraseó en vez de marcar, así
  que nunca "marcó" el chip de idiomas. Ese caso no prueba nada sobre el banco.

### Defecto conocido del arnés

El alumno simulado a veces parafrasea en vez de repetir la etiqueta, y entonces
`_solo_etiquetas` deja la prosa. Pasó 6 de 24 veces en A y 9 de 24 en B, o sea
que la asimetría juega en contra de B. Se arregla pidiéndole al simulador que
devuelva los índices de las opciones que marca, no texto.

### Qué queda

- Rehacer Ixchel y arreglar el defecto del arnés antes de sacar conclusiones más
  fuertes.
- El juez es el mismo modelo que recomienda. La salida legible
  (`data/tests/experimento_banco_para_leer.md`) está para que la revise una
  persona, idealmente la psicóloga.
