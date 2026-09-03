# Test corto de personalidad, valores y estilo cognitivo (pre-chat, 2026-08-17)

Pestaña `/personalidad`, modo opcional igual que Holland ("Perfil corto y
luego el chat" en el inicio). Backend: `backend/app/personalidad.py`.
Frontend: `frontend/src/Personalidad.jsx`.

## Qué es

48 ítems Likert 1-5, sin llamada a Gemini (califica por reglas, igual que
Holland). Cubre 3 de las 7 dimensiones vocacionales del chat
(`docs/motor-ia.md`):

| Dimensión | Ítems | Rasgos |
|---|---|---|
| Personalidad | 24 | organización, liderazgo, estabilidad, apertura, interpersonal, logro (subconjunto de `psicometrico.PERSONALIDAD`, mismo banco validado) |
| Valores | 12 | ayuda_social, seguridad_economica, autonomia_creativa, justicia |
| Estilo cognitivo | 12 | logico_estructurado, creativo_intuitivo, practico_manual, analitico_critico (gana el de mayor puntaje) |

## Cómo se integra al chat

Igual patrón que Holland: el resultado se guarda en
`localStorage['personalidad-perfil']` y el chat lo manda como `personalidad`
en `/api/next-question` y `/api/recommend`. El backend arma un bloque de
texto (`personalidad.bloque()`) que entra como CONTEXTO del prompt, igual que
`holland.bloque()`. **No delimita el catálogo** — eso ya se probó dos veces
(CIP y el catálogo codificado con RIASEC de Holland, ver `docs/holland.md`) y
las dos veces cortó carreras correctas. Se guarda en `resultados_personalidad`
si hay `session_id`.

⚠️ **MEDIDO (2026-08-17) y revertido: NO siembra la cobertura de
dimensiones.** El diseño original marcaba personalidad/valores/estilo_cognitivo
como cubiertas desde el inicio de la sesión para que el chat solo preguntara
por habilidades. El experimento A/B
([experiments/personalidad-en-chat.md](../experiments/personalidad-en-chat.md))
mostró que con eso el chat termina en **1 sola pregunta adaptativa en vez de
4**, el top-1 cambió en 3 de 5 perfiles simulados y la confianza nunca subió —
mismo patrón que `experiments/psicometrico-en-chat.md`: quitarle preguntas al
chat le quita señal, sin importar si la fuente de esa señal es "medida" o
estimada por Gemini. Se revirtió esa parte (`app/main.py` ya no llama a
`personalidad_cobertura`); el bloque de texto se queda como CONTEXTO nada
más, sin acortar la conversación. `app/preguntas.py` conserva el parámetro
`personalidad_cobertura` para que el experimento lo pueda seguir probando con
un piso mínimo de preguntas (ver "Qué cambiar antes de reintentarlo" en el
experimento) antes de reactivarlo.

## Independiente del `/psicometrico` de 100 ítems

Este test es aparte del examen psicométrico grande (`docs/psicometrico.md`):
no lo reemplaza ni lo modifica. Ese examen sigue sin alimentar el chat ni la
recomendación, por diseño.
