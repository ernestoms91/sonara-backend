import logging
import app.core.logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.info_router import router as info_router
from app.core.config import settings
from app.core.model import TTSModel 

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando servidor...")
    print(f"✅ Iniciando")
    # Cargar modelo TTS
    try:
        model, device = TTSModel.load()
        logger.info("✅ Modelo TTS cargado correctamente")
        # Opcional: guardar en app.state para acceder desde los endpoints
        app.state.model = model
        app.state.device = device
    except Exception as e:
        logger.error(f"❌ Error cargando modelo TTS: {e}")
        raise
    
    yield  # Aquí corre la aplicación
    
    # Shutdown
    logger.info("🛑 Cerrando servidor...")
    # Opcional: descargar modelo para liberar memoria
    TTSModel.unload()  # Si agregaste el método unload
    logger.info("✅ Modelo descargado")

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