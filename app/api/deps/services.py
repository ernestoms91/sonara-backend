from typing import Annotated
from fastapi import Depends
from app.services.tts_service import TTSService
from app.api.deps.db import DBSession
from app.api.deps.model import ModelDep

def get_tts_service(
    db: DBSession,
    model_service: ModelDep
) -> TTSService:
    return TTSService(db, model_service)

TTSServiceDep = Annotated[TTSService, Depends(get_tts_service)]