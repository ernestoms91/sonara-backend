# app/core/logging.py
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Formatos de log
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_production_logging():
    """Configuración de logging para producción"""
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Nivel según entorno
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Configuración principal
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": DETAILED_FORMAT,
                "datefmt": DATE_FORMAT,
            },
            "simple": {
                "format": SIMPLE_FORMAT,
                "datefmt": DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "simple",
                "level": log_level,
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 10_485_760,  # 10 MB
                "backupCount": 5,
                "formatter": "detailed",
                "level": log_level,
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/error.log",
                "maxBytes": 10_485_760,
                "backupCount": 5,
                "formatter": "detailed",
                "level": logging.ERROR,
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file_app", "file_error"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file_app"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file_error"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file_app"],
                "level": log_level,
                "propagate": False,
            },
        },
    }
    
    import logging.config
    logging.config.dictConfig(logging_config)
    
    return logging.getLogger("app")

def get_logger(name: str) -> logging.Logger:
    """Obtener logger para módulos específicos"""
    return logging.getLogger(f"app.{name}")