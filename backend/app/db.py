import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()


def url_sqlalchemy(url: str) -> str:
    """Normaliza la URL de la base al driver que este proyecto tiene instalado.

    Los servicios administrados (Render entre ellos) entregan la URL como
    `postgres://` o `postgresql://`. Con esos esquemas SQLAlchemy busca psycopg2,
    que no esta en las dependencias, y el arranque muere con un ImportError que
    no dice nada util. Aqui se reescribe al driver de psycopg 3."""
    for viejo in ("postgresql+psycopg://", "postgres://", "postgresql://"):
        if url.startswith(viejo):
            return "postgresql+psycopg://" + url[len(viejo):]
    return url


DATABASE_URL = url_sqlalchemy(
    os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:dev@localhost:5432/tfg")
)

# pool_pre_ping: los servicios administrados cortan las conexiones ociosas sin
# avisar. Sin esto, la primera consulta despues de un rato falla con la conexion
# ya cerrada en vez de reconectar.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _self_check():
    psycopg = "postgresql+psycopg://"
    assert url_sqlalchemy("postgres://u:p@host/db") == psycopg + "u:p@host/db"
    assert url_sqlalchemy("postgresql://u:p@host/db") == psycopg + "u:p@host/db"
    # Una URL que ya viene con el driver correcto no se toca.
    assert url_sqlalchemy(psycopg + "u:p@host/db") == psycopg + "u:p@host/db"
    # Y una de otro motor tampoco: no es asunto de esta funcion.
    assert url_sqlalchemy("sqlite:///local.db") == "sqlite:///local.db"
    print("db self-check OK: URL normalizada al driver de psycopg 3")


if __name__ == "__main__":
    _self_check()
