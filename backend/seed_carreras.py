"""Carga el catálogo de carreras desde data/*.json a la BD.
Idempotente: actualiza por (centro, nombre) si ya existe. Re-córrelo cuando
agregues más centros. Uso: uv run python seed_carreras.py"""

import glob
import json
import os

from app.db import Base, SessionLocal, engine
from app import models

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def cargar():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    nuevas = actualizadas = 0
    try:
        for ruta in glob.glob(os.path.join(DATA_DIR, "*.json")):
            doc = json.load(open(ruta, encoding="utf-8"))
            centro, uni = doc["centro"], doc["universidad"]
            for c in doc["carreras"]:
                existente = (
                    db.query(models.Carrera)
                    .filter_by(centro=centro, nombre=c["nombre"])
                    .first()
                )
                if existente:
                    existente.perfil = c["perfil"]
                    existente.universidad = uni
                    actualizadas += 1
                else:
                    db.add(models.Carrera(
                        nombre=c["nombre"], centro=centro,
                        universidad=uni, perfil=c["perfil"],
                    ))
                    nuevas += 1
        db.commit()
    finally:
        db.close()
    print(f"Carreras nuevas: {nuevas}, actualizadas: {actualizadas}")


if __name__ == "__main__":
    cargar()
