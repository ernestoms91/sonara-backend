# main.py
from pathlib import Path

from fastapi_pagination import add_pagination
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from requests import auth
from app.api.errors import  register_exception_handlers
from app.api.routers.audio_router import router as audio_router
from app.api.routers.auth_router import router as auth_router
from app.api.routers.info_router import router as info_router
from app.api.routers.boletin_router import router as boletin_router
from app.api.routers.profile_router import router as profile_router
from app.core.config import settings
from app.core.database import init_db
from app.core.model import TTSModel
from app.core.logging import get_logger, setup_logging

# Configurar logging al inicio
setup_logging()

# Crear logger para este módulo
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(">>> Iniciando servidor...")
    logger.info(f"Proyecto: {settings.PROJECT_NAME}")
    
    # INICIALIZAR BASE DE DATOS (crear tablas si no existen)
    init_db()
    logger.info(">>> Base de datos inicializada")
    
    # Cargar modelo TTS (se guarda en TTSModel._model automáticamente)
    try:
        _, device = TTSModel.load()
        logger.info(">>> Modelo TTS cargado correctamente")
        logger.debug(f"Dispositivo: {device}")
    except Exception as e:
        logger.error(f"Error cargando modelo TTS: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("<<< Cerrando servidor...")
    if hasattr(TTSModel, 'unload'):
        TTSModel.unload()
        logger.info("Modelo descargado")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

add_pagination(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Servir audios generados
app.mount(
    "/audios", 
    StaticFiles(directory=str(Path(settings.OUTPUT_DIR) / "generated")), 
    name="audios"
)

# Servir waveforms (JSON)
app.mount(
    "/waveforms", 
    StaticFiles(directory=str(Path(settings.OUTPUT_DIR) / "waveforms")),  
    name="waveforms"
)


register_exception_handlers(app)

app.include_router(audio_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(boletin_router, prefix="/api/v1")
app.include_router(info_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")


logger.info(f"API {settings.PROJECT_NAME} configurada correctamente")
logger.info(f"Nivel de logging: {settings.LOG_LEVEL}")
logger.info(f"Audios disponibles en: /audios/{{audio_id}}.wav")
logger.info(f"Waveforms disponibles en: /waveforms/{{audio_id}}.json")