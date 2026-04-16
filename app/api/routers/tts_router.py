# app/api/routers/tts_router.py
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import Optional
from app.api.deps import DBSession, ModelDep
from app.services.tts_service import TTSService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])

@router.post(
    "/create-profile",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear perfil de voz clonada",
)
async def create_profile(
    db: DBSession,
    model: ModelDep,
    name: str = Form(..., min_length=1, max_length=50),
    ref_text: str = Form(..., min_length=1, max_length=500),
    audio_file: UploadFile = File(...),
    language: str = Form(default="Spanish"),
    user_id: Optional[int] = Form(default=None),
) -> dict:
    
    audio_bytes = await audio_file.read()
    
    service = TTSService(db, model)
    profile = service.create_profile(
        name=name,
        ref_text=ref_text,
        audio_bytes=audio_bytes,
        filename=audio_file.filename,
        content_type=audio_file.content_type,
        language=language,
        user_id=user_id
    )
    
    return {
        "success": True,
        "profile_id": profile.id,
        "profile_uuid": profile.profile_id,
        "name": profile.name,
        "language": profile.language,
        "message": "Perfil de voz creado exitosamente"
    }