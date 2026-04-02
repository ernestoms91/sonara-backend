# app/api/deps.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlmodel import Session
from qwen_tts import Qwen3TTSModel
from app.core.database import get_db
from app.core.model import TTSModel
from app.core.logging import get_logger

logger = get_logger(__name__)

# Dependencia de base de datos
DBSession = Annotated[Session, Depends(get_db)]


# Modelo TTS con manejo de errores mejorado
def get_model() -> Qwen3TTSModel:
    """
    Obtener instancia del modelo TTS
    
    Raises:
        HTTPException: Si el modelo no está disponible
    """
    try:
        model, _ = TTSModel.get_model()
        if model is None:
            logger.error("Modelo TTS no está cargado")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Modelo TTS no disponible"
            )
        return model
    except Exception as e:
        logger.error(f"Error obteniendo modelo TTS: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error accediendo al modelo TTS"
        )


def get_device() -> str:
    """
    Obtener dispositivo de ejecución (cuda/cpu)
    
    Raises:
        HTTPException: Si hay error obteniendo el dispositivo
    """
    try:
        _, device = TTSModel.get_model()
        if not device:
            logger.error("Dispositivo TTS no determinado")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dispositivo no disponible"
            )
        return device
    except Exception as e:
        logger.error(f"Error obteniendo dispositivo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error determinando dispositivo"
        )


# Tipos anotados para inyección de dependencias
ModelDep = Annotated[Qwen3TTSModel, Depends(get_model)]
DeviceDep = Annotated[str, Depends(get_device)]