# app/core/database.py
from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# Engine lazy-loaded
_engine = None

def get_engine():
    """Obtener o crear el engine de forma lazy"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
            echo=False
        )
    return _engine

def get_db():
    """Dependencia para obtener sesión de base de datos"""
    engine = get_engine()
    with Session(engine) as session:
        yield session

def init_db():
    """Crear todas las tablas en la base de datos"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)