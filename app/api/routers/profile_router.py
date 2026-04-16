# app/api/routers/tts_router.py
from typing import Optional

from fastapi import APIRouter, status, UploadFile, File, Form, Path
from app.api.deps import TTSServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger
from app.schemas.profile import ProfileResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/profile", tags=["PROFILE"])


@router.post(
    "/new",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear perfil de voz clonada",
)
async def create_profile(
    service: TTSServiceDep,
    name: str = Form(..., min_length=1, description="Nombre del narrador"),
    ref_text: str = Form(..., min_length=1,
                         description="Texto de referencia para la voz"),
    language: str = Form(default="Spanish"),
    audio_file: UploadFile = File(...)
) -> CommonResponse:
    logger.info(f"Recibida solicitud para crear perfil: {name}")
    audio_bytes = await audio_file.read()

    profile = service.create_profile(
        name=name,
        ref_text=ref_text,
        audio_bytes=audio_bytes,
        filename=audio_file.filename,
        content_type=audio_file.content_type,
        language=language,
    )

    return CommonResponse.success(
        message="Profile created successfully",
        data=ProfileResponse.model_validate(profile)
    )


@router.post(
    "/{profile_id}/generate-hours",
    response_model=CommonResponse,
    summary="Generar los 12 audios de horas para un perfil",
)
def generate_hours(
    service: TTSServiceDep,
    profile_id: int = Path(..., ge=1, description="ID del perfil"),
) -> CommonResponse:
    service.pre_generate_hours(profile_id)
    return CommonResponse.success(
        message=f"Audios de horas generados correctamente"
    )


@router.post(
    "/generar",
    response_model=CommonResponse,
    summary="Generar audio a partir de un perfil",
)
async def synthesize(
    service: TTSServiceDep,
    profile_id: str = Form(...,
                           description="ID del perfil a usar para la síntesis"),
    text: str = Form(..., min_length=1, description="Texto a sintetizar"),
    language: Optional[str] = Form(
        default="Spanish", description="Idioma del texto a sintetizar")
) -> CommonResponse:  # ✅ Tipado correcto
    audio_bytes = service.synthesize_with_profile(
        profile_id=profile_id,
        text=text,
        language=language or "Spanish"
    )

    # ✅ Devuelve CommonResponse consistente
    return CommonResponse.success(
        message="Audio creado exitosamente",
        # data={
        #     "audio_base64": audio_bytes.hex(),  # O como manejes el audio
        #     "profile_id": profile_id,
        #     "text_length": len(text)
        # }
    )
