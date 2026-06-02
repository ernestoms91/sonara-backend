from pydantic import Field
from pydantic_settings import BaseSettings
import sys
import logging
from pathlib import Path

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = Field(default="sqlite:///./sonara.db", env="DATABASE_URL")
    
    # JWT
    JWT_SECRET: str = Field(..., env="JWT_SECRET", min_length=32)
    JWT_ALG: str = Field(default="HS256", env="JWT_ALG")
    JWT_EXPIRES_MIN: int = Field(default=1440, env="JWT_EXPIRES_MIN")
    
    # API
    PROJECT_NAME: str =  Field(..., env="PROJECT_NAME")

    # TTS MODELS
    MODEL_PATH: str = Field(..., env="MODEL_PATH")
    MODEL_NAME: str = Field(..., env="MODEL_NAME")
    DEVICE: str = Field(..., env="DEVICE")

    # OUTPUT
    OUTPUT_DIR: str = Field(default="files", env="OUTPUT_DIR")
    
    #LOGGING
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ESPECTRO DE AUDIO
    PIXELS_PER_SECOND: int = Field(default=20, env="PIXELS_PER_SECOND", ge=1, le=100)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

try:
    settings = Settings()

    # Validar modelo
    model_folder = Path(settings.MODEL_PATH) / settings.MODEL_NAME
    if not model_folder.exists():
        logging.critical(f"Modelo no encontrado: {model_folder}")
        sys.exit(1)
    
    # Validar device
    if settings.DEVICE not in ["cpu", "cuda", "mps"]:
        logging.critical(f"Device no válido: {settings.DEVICE}. Usar: cpu, cuda")
        sys.exit(1)

    # Crear carpeta de salida si no existe
    output_path = Path(settings.OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Carpeta de salida: {output_path.absolute()}")
    
    # Crear subcarpeta para perfiles dentro de OUTPUT_DIR
    profiles_path = output_path / "profiles"
    profiles_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Carpeta de perfiles: {profiles_path.absolute()}")

    # Crear subcarpeta para waveform dentro de OUTPUT_DIR
    waveform_path = output_path / "waveforms"
    waveform_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Carpeta de waveform: {waveform_path.absolute()}")

except Exception as e:
    logging.critical(f"Error de configuración: {e}")
    sys.exit(1)