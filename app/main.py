# main.py
from fastapi_pagination import add_pagination
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.api.errors import http_exception_handler, general_exception_handler, validation_exception_handler, value_error_handler
from app.api.routers.audio_router import router as audio_router
from app.api.routers.info_router import router as info_router
from app.api.routers.profile_router import router as tts_router
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

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)

app.include_router(audio_router, prefix="/api/v1")
app.include_router(info_router, prefix="/api/v1")
app.include_router(tts_router, prefix="/api/v1")

logger.info(f"API {settings.PROJECT_NAME} configurada correctamente")
logger.info(f"Nivel de logging: {settings.LOG_LEVEL}")