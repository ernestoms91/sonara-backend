# app/core/logging.py
import logging as logging_module
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Formatos de log
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging():
    """Configuración de logging para producción"""
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Nivel según entorno con valor por defecto seguro
    default_level = "INFO"
    log_level_str = getattr(settings, 'LOG_LEVEL', default_level).upper()
    
    # Validar que sea un nivel válido de logging
    if not hasattr(logging_module, log_level_str):
        log_level_str = default_level
    
    log_level = getattr(logging_module, log_level_str)
    
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
                "maxBytes": 10_485_760,
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
                "level": logging_module.ERROR,
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
    
    root_logger = logging_module.getLogger("app")
    
    if log_level_str != getattr(settings, 'LOG_LEVEL', default_level).upper():
        root_logger.warning(f"LOG_LEVEL no válido, usando {default_level}")
    else:
        root_logger.info(f" Sistema de logging configurado - Nivel: {log_level_str}")

def get_logger(name: str) -> logging_module.Logger:
    """Obtener logger para módulos específicos"""
    return logging_module.getLogger(f"app.{name}")