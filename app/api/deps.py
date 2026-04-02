# app/core/dependencies.py
from typing import Annotated, Tuple
from fastapi import Depends
from sqlmodel import Session
from app.core.database import get_db
from qwen_tts import Qwen3TTSModel
from app.core.database import get_db
from app.core.model import TTSModel

# Dependencia de base de datos
DBSession = Annotated[Session, Depends(get_db)]

# Modelo TTS
def get_model() -> Qwen3TTSModel:
    model, _ = TTSModel.get_model()
    return model

def get_device() -> str:
    _, device = TTSModel.get_model()
    return device

ModelDep = Annotated[Qwen3TTSModel, Depends(get_model)]
DeviceDep = Annotated[str, Depends(get_device)]