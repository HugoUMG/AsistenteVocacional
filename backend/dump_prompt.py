"""Vuelca a docs/ el prompt EXACTO que recibe Gemini en la primera pregunta
adaptativa (justo después de las 5 preguntas fijas), sin llamar a la API.

Reconstruye lo mismo que arma /api/next-question: catálogo filtrado por
departamento -> pre-filtro de app/filtro.py -> texto de catálogo + estado de
cobertura. Útil para la tesis y para revisar el prompt sin gastar cuota.

    uv run python dump_prompt.py [departamento]     # default: Quetzaltenango
"""

import json
import os
import sys

from app.db import SessionLocal
from app.models import Carrera
from app.preguntas import (
    COBERTURA_INICIAL,
    MAX_ADAPTATIVAS,
    MIN_ADAPTATIVAS,
    PRIORITARIAS,
    SYSTEM,
    SiguientePaso,
    _historial,
    _texto_cobertura,
)
from app.filtro import preseleccionar
from app.recomendar import MODELO, _catalogo_texto

TEMPERATURA = 0.5  # el valor que usa siguiente_pregunta()
DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

# Las 5 respuestas fijas de un estudiante de ejemplo (mismas claves que
# FIJAS en frontend/src/Chat.jsx).
RESPUESTAS = {
    "nombre": "Hugo",
    "departamento": sys.argv[1] if len(sys.argv) > 1 else "Quetzaltenango",
    "impacto": "Ayudar, enseñar o cuidar a las personas, Construir, diseñar o hacer que las cosas funcionen",
    "estilo": "Con personas, en trato directo, De forma práctica, con las manos",
    "entorno": "En un hospital, clínica o consultorio, En un laboratorio o taller técnico",
    "gustos": "Salud y cuidar personas, Tecnología y computación, Construcción, máquinas y cómo funcionan las cosas",
}


def main():
    db = SessionLocal()
    q = db.query(Carrera)
    depto = RESPUESTAS["departamento"]
    if depto != "Ambos":
        q = q.filter(Carrera.departamento.in_([d.strip() for d in depto.split(",")]))
    carreras = q.all()
    db.close()

    candidatas = preseleccionar(RESPUESTAS, carreras)
    catalogo = (
        "CATÁLOGO DE CARRERAS (solo para tu razonamiento; no menciones nombres):\n"
        f"{_catalogo_texto(candidatas)}"
    )
    # Primera adaptativa: cobertura inicial, 0 preguntas hechas, 4 pendientes.
    variable = (
        f"RESPUESTAS DEL ESTUDIANTE HASTA AHORA:\n{_historial(RESPUESTAS)}\n\n"
        f"COBERTURA DE DIMENSIONES (estado real, no lo infieras del historial): "
        f"{_texto_cobertura(COBERTURA_INICIAL)}.\n"
        f"Llevas 0 pregunta(s) adaptativa(s) de mínimo {MIN_ADAPTATIVAS} y "
        f"máximo {MAX_ADAPTATIVAS}. "
        f"Dimensiones prioritarias AÚN PENDIENTES: {', '.join(PRIORITARIAS)} — tu "
        "siguiente pregunta DEBE apuntar a una de estas (usa ese valor exacto en "
        "'dimension_objetivo'). terminado DEBE ser false.\n"
    )

    datos = {
        "endpoint": "POST /api/next-question",
        "momento": "primera pregunta adaptativa, después de las 5 preguntas fijas",
        "modelo": MODELO,
        "temperature": TEMPERATURA,
        "response_mime_type": "application/json",
        "como_se_arma": (
            "system_instruction = system; contents = catalogo + '\\n\\n' + variable "
            "(el catálogo va PRIMERO para que el caching implícito de Gemini pueda "
            "reusar el prefijo). Ver _generar_con_cliente en app/recomendar.py."
        ),
        "cuerpo_http_de_entrada": {"session_id": "<uuid>", "respuestas": RESPUESTAS},
        "system_instruction": SYSTEM,
        "contents": {"catalogo": catalogo, "variable": variable},
        "contents_texto_enviado": f"{catalogo}\n\n{variable}",
        "response_schema": SiguientePaso.model_json_schema(),
        "medidas": {
            "carreras_en_el_departamento": len(carreras),
            "carreras_tras_el_prefiltro": len(candidatas),
            "chars_system": len(SYSTEM),
            "chars_catalogo": len(catalogo),
            "chars_variable": len(variable),
        },
    }

    ruta_json = os.path.join(DOCS, "prompt-next-question-ejemplo.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    # El mismo contenido en Markdown, porque un prompt con \n escapados dentro
    # de un JSON es ilegible para un humano.
    ruta_md = os.path.join(DOCS, "prompt-next-question-ejemplo.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(
            f"""# Prompt exacto de la primera pregunta adaptativa

Generado con `uv run python dump_prompt.py {depto}` (regenerar si cambia el
prompt o el catálogo). Es lo que recibe Gemini justo después de las 5 preguntas
fijas, sin llamar a la API.

| | |
|---|---|
| Endpoint | `POST /api/next-question` |
| Modelo | `{MODELO}` |
| Temperature | {TEMPERATURA} |
| Salida | JSON validado con el schema `SiguientePaso` (ver más abajo) |
| Carreras en {depto} | {len(carreras)} |
| Carreras tras el pre-filtro de `app/filtro.py` | {len(candidatas)} |

La llamada se arma así (`_generar_con_cliente` en `app/recomendar.py`):
`system_instruction` = el bloque 1; `contents` = bloque 2 + `\\n\\n` + bloque 3.
El catálogo va **primero** para que el caching implícito de Gemini pueda reusar
ese prefijo entre llamadas.

---

## 1. system_instruction ({len(SYSTEM)} caracteres)

```text
{SYSTEM}
```

---

## 2. contents — catálogo ({len(catalogo)} caracteres)

Recortado por el pre-filtro sin IA a las {len(candidatas)} carreras con más
solapamiento de palabras con las respuestas del estudiante.

```text
{catalogo}
```

---

## 3. contents — parte variable ({len(variable)} caracteres)

Lo único que cambia entre llamadas: el historial del estudiante y el estado de
cobertura de dimensiones que lleva el backend.

```text
{variable}
```

---

## 4. response_schema

Gemini está obligado a responder un JSON con esta forma (`SiguientePaso`):

```json
{json.dumps(SiguientePaso.model_json_schema(), ensure_ascii=False, indent=2)}
```

---

## Respuestas fijas usadas en este ejemplo

```json
{json.dumps(RESPUESTAS, ensure_ascii=False, indent=2)}
```
"""
        )
    print(f"escrito:\n  {os.path.normpath(ruta_json)}\n  {os.path.normpath(ruta_md)}")


if __name__ == "__main__":
    main()
