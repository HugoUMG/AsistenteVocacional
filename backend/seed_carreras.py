"""Carga el catálogo de carreras desde data/*.json a la BD.
Idempotente: actualiza por (centro, nombre) si ya existe. Re-córrelo cuando
agregues más centros. Uso: uv run python seed_carreras.py"""

import glob
import json
import os

from app.db import Base, SessionLocal, engine
from app import models

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PERFILES_COMPARTIDOS = os.path.join(DATA_DIR, "perfiles_compartidos.json")


def _perfil_y_grupo(c: dict, compartidos: dict) -> tuple[str, str | None]:
    """Una carrera trae 'perfil' inline (sede única) O 'perfil_id' que apunta a
    perfiles_compartidos.json (misma carrera en varias sedes, evita repetir el
    mismo banco de palabras N veces)."""
    perfil_id = c.get("perfil_id")
    if perfil_id:
        return compartidos[perfil_id], perfil_id
    return c["perfil"], None


def cargar():
    Base.metadata.create_all(bind=engine)
    compartidos = json.load(open(PERFILES_COMPARTIDOS, encoding="utf-8"))
    db = SessionLocal()
    nuevas = actualizadas = 0
    try:
        for ruta in glob.glob(os.path.join(DATA_DIR, "*.json")):
            if ruta == PERFILES_COMPARTIDOS:
                continue
            doc = json.load(open(ruta, encoding="utf-8"))
            depto, centro, uni = doc["departamento"], doc["centro"], doc["universidad"]
            for c in doc["carreras"]:
                perfil, grupo = _perfil_y_grupo(c, compartidos)
                sello = c.get("sello")
                existente = (
                    db.query(models.Carrera)
                    .filter_by(centro=centro, nombre=c["nombre"])
                    .first()
                )
                if existente:
                    existente.perfil = perfil
                    existente.perfil_grupo = grupo
                    existente.sello = sello
                    existente.universidad = uni
                    existente.departamento = depto
                    actualizadas += 1
                else:
                    db.add(models.Carrera(
                        nombre=c["nombre"], departamento=depto, centro=centro,
                        universidad=uni, perfil=perfil, perfil_grupo=grupo, sello=sello,
                    ))
                    nuevas += 1
        db.commit()
    finally:
        db.close()
    print(f"Carreras nuevas: {nuevas}, actualizadas: {actualizadas}")


if __name__ == "__main__":
    cargar()
