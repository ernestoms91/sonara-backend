from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.core.model import TTSModel
from app.core.logging import get_logger

logger = get_logger(__name__)

def get_device() -> str:
    try:
        _, device = TTSModel.get_model()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dispositivo no disponible"
            )
        return device
    except Exception:
        logger.error("Error obteniendo device", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error determinando dispositivo"
        )

DeviceDep = Annotated[str, Depends(get_device)]