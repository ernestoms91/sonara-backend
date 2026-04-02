# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.info_router import router as info_router
from app.core.config import settings
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
    
    # Cargar modelo TTS (se guarda en TTSModel._model automáticamente)
    try:
        model, device = TTSModel.load()
        logger.info(">>> Modelo TTS cargado correctamente")
        logger.debug(f"Dispositivo: {device}")
        # ✅ No guardar en app.state - el singleton ya mantiene el modelo
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(info_router, prefix="/api/v1")

logger.info(f"API {settings.PROJECT_NAME} configurada correctamente")
logger.info(f"Nivel de logging: {settings.LOG_LEVEL}")