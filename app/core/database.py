# app/core/database.py
from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# Crear engine de SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necesario para SQLite
    echo=False  # Cambia a True para ver los queries SQL
)

def get_db():
    """Dependencia para obtener sesión de base de datos"""
    with Session(engine) as session:
        yield session

def init_db():
    """Crear todas las tablas en la base de datos"""
    SQLModel.metadata.create_all(engine)