# app/api/routers/profile_router.py
from fastapi import APIRouter, status, UploadFile, File, Form, Path
from app.api.deps import ProfileServiceDep
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
    profile_service: ProfileServiceDep,
    name: str = Form(..., min_length=1, description="Nombre del narrador"),
    ref_text: str = Form(..., min_length=1,
                         description="Texto de referencia para la voz"),
    language: str = Form(default="Spanish"),
    audio_file: UploadFile = File(...)
) -> CommonResponse:
    logger.info(f"Recibida solicitud para crear perfil: {name}")
    audio_bytes = await audio_file.read()

    profile = profile_service.create_profile(
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
    

