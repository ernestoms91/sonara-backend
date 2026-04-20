# app/api/routers/audio_router.py
from fastapi import APIRouter, status, Path, Form, Body
from app.api.deps.services import AudioServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["AUDIO"])


@router.post(
    "/generate/{profile_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar audio a partir de texto usando un perfil de voz clonada",
)
async def generate_audio(
    audio_service: AudioServiceDep,
    profile_id: int = Path(..., gt=0, description="ID del perfil"),
    text: str = Form(..., min_length=1, max_length=1000, description="Texto a sintetizar"),
) -> CommonResponse:
    """
    Genera un audio usando la voz clonada del perfil.
    """
    result = audio_service.generate_and_save(
        profile_id=profile_id,
        text=text
    )
    
    return CommonResponse.success(
        message="Audio generated successfully",
        data={
            "audio_id": result["audio_id"],
            "duration": result["duration"],
            "filename": result["filename"],
            "created_at": result["created_at"].isoformat() if result["created_at"] else None
        }
    )


@router.post(
    "/{audio_id}/change-duration",
    response_model=CommonResponse,
    summary="Cambiar la duración de un audio existente",
)
async def change_audio_duration(
    audio_service: AudioServiceDep,
    audio_id: str = Path(..., description="UUID del audio original"),
    target_duration: float = Form(..., gt=0.1, le=60.0, description="Duración deseada en segundos (0.1 - 60)"),
) -> CommonResponse:
    """
    Cambia la duración de un audio manteniendo el tono.
    """
    result = audio_service.change_audio_duration(
        audio_id=audio_id,
        target_duration=target_duration
    )
    
    return CommonResponse.success(
        message=f"Audio duration changed to {target_duration} seconds",
        data={
            "audio_id": result["audio_id"],
            "original_audio_id": result["original_audio_id"],
            "original_duration": result["original_duration"],
            "new_duration": result["new_duration"],
            "filename": result["filename"],
            "created_at": result["created_at"].isoformat() if result["created_at"] else None
        }
    )