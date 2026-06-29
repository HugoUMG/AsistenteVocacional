import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# psycopg3 usa el driver "postgresql+psycopg"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:dev@localhost:5432/tfg"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
