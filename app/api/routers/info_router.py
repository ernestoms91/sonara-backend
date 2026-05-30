from app.core.config import settings
from fastapi import APIRouter, status

router = APIRouter(prefix="/info", tags=["Info"])

@router.get("/", status_code=status.HTTP_200_OK)
def root():
    return {
        "status": "ok",
        "model": settings.MODEL_NAME,
        "runing_on": settings.DEVICE,
        "audio_output_dir": str(settings.OUTPUT_DIR),
    }
