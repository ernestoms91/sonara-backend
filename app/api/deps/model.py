from typing import Annotated
from fastapi import Depends, HTTPException, status
from qwen_tts import Qwen3TTSModel
from app.core.model import TTSModel
from app.core.logging import get_logger

logger = get_logger(__name__)

def get_model() -> Qwen3TTSModel:
    try:
        model, _ = TTSModel.get_model()
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Modelo TTS no disponible"
            )
        return model
    except Exception as e:
        logger.error("Error obteniendo modelo", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error accediendo al modelo TTS"
        )

ModelDep = Annotated[Qwen3TTSModel, Depends(get_model)]