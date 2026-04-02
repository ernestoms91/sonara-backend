# app/api/routers/tts_router.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.api.deps import ModelDep, DeviceDep
from app.services.tts_service import TTSService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    """Solicitud de síntesis de voz"""
    text: str = Field(..., min_length=1, max_length=1000, description="Texto a sintetizar")
    speaker_id: int = Field(default=0, ge=0, description="ID del locutor")
    save_file: bool = Field(default=True, description="Guardar audio en archivo")


class TTSResponse(BaseModel):
    """Respuesta de síntesis de voz"""
    success: bool
    text: str
    speaker_id: int
    device: str
    file: str = None
    duration_estimate: float


@router.post("/synthesize", response_model=TTSResponse, status_code=status.HTTP_200_OK)
async def synthesize(
    request: TTSRequest,
    model: ModelDep,
    device: DeviceDep
) -> TTSResponse:
    """
    Sintetizar texto a voz
    
    - **text**: Texto a convertir a voz
    - **speaker_id**: ID del locutor (default: 0)
    - **save_file**: Guardar audio en archivo (default: true)
    """
    try:
        logger.info(f"Síntesis solicitada: {request.text[:50]}...")
        
        # Estimar duración
        duration = TTSService.estimate_duration(request.text)
        
        if request.save_file:
            # Sintetizar y guardar en archivo
            result = TTSService.synthesize_and_save(
                text=request.text,
                model=model,
                device=device,
                speaker_id=request.speaker_id
            )
        else:
            # Solo sintetizar sin guardar
            result = TTSService.synthesize(
                text=request.text,
                model=model,
                device=device,
                speaker_id=request.speaker_id
            )
        
        return TTSResponse(
            success=result["success"],
            text=result["text"],
            speaker_id=result["speaker_id"],
            device=result["device"],
            file=result.get("file"),
            duration_estimate=duration
        )
        
    except ValueError as e:
        logger.warning(f"Validación fallida: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en síntesis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando síntesis de voz"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health(model: ModelDep, device: DeviceDep):
    """Verificar estado del modelo TTS"""
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "device": device
    }
