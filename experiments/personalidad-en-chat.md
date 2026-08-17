# Test corto de personalidad antes del chat: ¿ayuda o le quita señal al chat?

**2026-08-17.** Script: `backend/experimento_personalidad.py`. Resultados:
`backend/data/tests/experimento_personalidad_resultados.json`.

## Lo que se midió

Los 5 perfiles de `experimento_psicometrico.py` (Kevin, Dulce, Brandon,
Melany, Josué), cada uno con VIEJO (producción de hoy, 4 fijas + hasta 8
adaptativas) contra NUEVO (test corto de 48 ítems antes del chat, mismas 4
fijas, cobertura de personalidad/valores/estilo_cognitivo sembrada).

| Perfil | VIEJO top1 (afinidad, preguntas) | NUEVO top1 (afinidad, preguntas) | ¿Coincide? |
|---|---|---|---|
| Kevin | Ing. en Ciencias y Sistemas (35%, 4) | Ing. en Ciencias y Sistemas (35%, 1) | Sí |
| Dulce | Lic. en Enfermería (65%, 4) | Lic. en Comunicación y Diseño (45%, 1) | **No** |
| Brandon | Ing. Mecánica (35%, 4) | Ing. en Ciencias y Sistemas (35%, 1) | **No** |
| Melany | Lic. Informática e Inteligencia de Negocios (35%, 4) | Contaduría Pública y Auditoría (35%, 1) | **No** |
| Josué | Ing. en Agronomía (45%, 4) | Ing. en Agronomía (35%, 1) | Sí |

**El top-1 coincidió en 2 de 5.** En los 5 casos, NUEVO terminó con **1 sola
pregunta adaptativa** en vez de 4, y la afinidad del top-1 fue igual o menor
(nunca mayor) que en VIEJO.

## Por qué pasa esto

No es que el bloque de personalidad "confunda" al chat — es aritmético.
`PRIORITARIAS` tiene 4 dimensiones; el test corto precarga 3
(personalidad/valores/estilo_cognitivo), así que solo queda `habilidades`
pendiente. En cuanto el chat cubre esa, `pendientes` queda vacío y
`preguntas.siguiente_pregunta` deja de forzar `terminado=false` — nada en el
código exige un mínimo de preguntas independiente de la cobertura (pese a que
`MIN_ADAPTATIVAS=4` existe como constante, solo se usa para el texto que lee
Gemini, no como un guard duro). Con 3 de 4 dimensiones ya "resueltas" por el
test, el chat entra en su primera oportunidad de terminar y la toma.

El caso de **Dulce** ilustra el costo: en VIEJO, sus 4 adaptativas incluyeron
la pregunta de "escenario libre" que la hizo admitir que dibuja y edita
video — el canal que en `experiments/psicometrico-en-chat.md` se documentó
como "los chips revelan lo que las preguntas directas no". Con 1 sola
pregunta, NUEVO no tuvo espacio para que apareciera ese matiz por otra vía;
que haya llegado a Comunicación y Diseño parece un acierto, pero es
casualidad de UNA corrida a temperatura 0.5, no algo que este diseño
garantice — pudo salir Enfermería igual de fácil con menos preguntas y menos
confianza.

## Sobre la repetición reportada

Con solo 1 pregunta adaptativa y siempre apuntando a `habilidades`, el
usuario reportó que esa pregunta se siente repetida entre corridas manuales
("resolver problemas con lógica" vs "organizar y clasificar"). En las 5
corridas de este experimento el TEXTO no fue idéntico (cada apertura se
personalizó con lo que dijo el alumno), pero el **patrón de fondo** sí se
repite seguido: "algo técnico/manual" vs "algo analítico/lógico" aparece en
4 de 5 perfiles. Es consistente con la causa de arriba: al quedar
`habilidades` como la ÚNICA dimensión posible, el chat pierde la variedad que
antes venía de mezclar 4 dimensiones distintas, y para esa dimensión sola el
modelo tiende al mismo par de opciones "obvias".

## Conclusión

**No se integra tal cual.** El mecanismo funciona exactamente como se
diseñó (cobertura sembrada, menos preguntas, menos tokens), pero el efecto
medido es el mismo patrón que `experiments/psicometrico-en-chat.md` ya
documentó con el examen de 100 ítems: **quitarle preguntas al chat le quita
señal**, aunque la fuente de esa señal ahora sea "medida" en vez de
estimada por Gemini. El top-1 cambió en 3 de 5 casos y la confianza nunca
subió.

Queda **igual que Holland**: el test corto sirve como experiencia (perfil
propio, conversación más corta) pero no debe usarse para recortar preguntas
por debajo de un piso razonable.

## Qué cambiar antes de reintentarlo

1. **Poner un piso duro de preguntas adaptativas** independiente de la
   cobertura (p. ej. `MIN_ADAPTATIVAS` como guard real, no solo como texto
   informativo) — así el test corto ahorra preguntas REDUNDANTES sin bajar
   de un mínimo de exploración.
2. Con ese piso, medir de nuevo si el top-1 se mantiene y si sigue habiendo
   más tokens ahorrados que con Holland.

## Limitaciones

Mismas de siempre: 5 perfiles ficticios, 1 corrida por brazo (temperatura
0.5/0.3, no determinista), quien responde el chat y quien recomienda son el
mismo modelo. No da potencia estadística; sirve para ver el mecanismo.
