# Decisión: la recomendación la hace un LLM, no una red neuronal entrenada

**Fecha:** inicio del proyecto (vigente).
**Estado:** aceptada. **No revertir sin releer esto.**

## Motivo

> La recomendación la hace un **LLM (Gemini)**, NO una red neuronal entrenada.
> Motivo: el requisito del TFG es "aprovechar la IA para simplificar el proceso"
> (no exige un modelo entrenado con métricas) y no hay datos de entrenamiento
> etiquetados. Entrenar una red con datos simulados sería circular. El LLM además
> entiende el texto libre del cuestionario.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Red neuronal / scikit-learn entrenado | No hay dataset etiquetado real (alumno → carrera acertada). Entrenar con datos simulados por el mismo modelo es circular: mide su propio sesgo. |
| Sistema de reglas puro (sin IA) | No entiende el texto libre ("qué temas te apasionan"), y el catálogo cambia; habría que reescribir reglas por cada centro nuevo. |
| Híbrido: heurística que decide y LLM que redacta | Se aplicó parcialmente: hay una heurística **sin IA** (`app/filtro.py`) pero solo como pre-filtro de tokens, no como decisor. Ver [filtro-catalogo.md](filtro-catalogo.md). |

## Consecuencias técnicas

- El costo del sistema es **cuota de API**, no cómputo de entrenamiento: ver
  [gemini-costos-y-caching.md](gemini-costos-y-caching.md).
- La calidad se valida con **experimentos A/B sobre perfiles simulados**, no con
  accuracy sobre un test set: ver `experiments/`.
- El catálogo es la fuente de verdad y los prompts son catálogo-agnósticos:
  agregar carreras no requiere reentrenar ni tocar código.
- El `README.md` mencionó scikit-learn hasta 2026-08-01 (residuo del Sprint 1);
  ya está corregido. Si vuelve a aparecer en documentación, es un error.

## Modelo elegido

`gemini-3.1-flash-lite` (configurable con `GEMINI_MODEL` en `backend/.env`).
Se eligió por su cuota gratuita amplia (~500 req/día) y por ser el más barato de
los tres evaluados; el detalle de la comparación está en
[gemini-costos-y-caching.md](gemini-costos-y-caching.md).
