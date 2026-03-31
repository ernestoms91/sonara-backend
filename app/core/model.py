# backend/app/core/model.py
import torch
import logging
from pathlib import Path
from typing import Tuple, Optional
from app.core.config import settings
from qwen_tts import Qwen3TTSModel

logger = logging.getLogger(__name__)

class TTSModel:
    _model: Optional[Qwen3TTSModel] = None
    _device: Optional[str] = None
    
    @classmethod
    def _get_device(cls) -> str:
        """Configurar device basado en settings"""
        if settings.DEVICE == "cuda" and torch.cuda.is_available():
            device = "cuda:0"
            logger.info(f"✅ GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"✅ Memoria: {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)} GB")
        elif settings.DEVICE == "mps" and torch.backends.mps.is_available():
            device = "mps"
            logger.info("✅ MPS disponible")
        else:
            device = "cpu"
            logger.info("✅ Usando CPU")
        
        return device
    
    @classmethod
    def _get_model_path(cls) -> str:
        """Obtener ruta del modelo (local o HF)"""
        if not settings.MODEL_PATH:
            return settings.MODEL_NAME
        
        model_path = Path(settings.MODEL_PATH) / settings.MODEL_NAME
        if model_path.exists():
            return str(model_path)
        
        logger.warning(f"⚠️ Ruta local no encontrada: {model_path}, usando {settings.MODEL_NAME}")
        return settings.MODEL_NAME
    
    @classmethod
    def load(cls) -> Tuple[Qwen3TTSModel, str]:
        """Cargar modelo TTS"""
        if cls._model is None:
            try:
                cls._device = cls._get_device()
                model_path = cls._get_model_path()
                
                logger.info(f"📂 Cargando modelo desde: {model_path}")
                
                cls._model = Qwen3TTSModel.from_pretrained(
                    model_path,
                    device_map=cls._device,
                    dtype=torch.bfloat16,
                    attn_implementation="flash_attention_2" if cls._device == "cuda" else "eager",
                )
                
                logger.info("✅ Modelo cargado exitosamente!")
                
            except ImportError as e:
                logger.critical(f"❌ qwen_tts no instalado: {e}")
                raise
            except torch.cuda.OutOfMemoryError as e:
                logger.critical(f"❌ Memoria GPU insuficiente: {e}")
                raise
            except Exception as e:
                logger.critical(f"❌ Error cargando modelo: {e}")
                raise
        
        return cls._model, cls._device
    
    @classmethod
    def unload(cls):
        """Liberar recursos del modelo"""
        if cls._model is not None:
            del cls._model
            cls._model = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("🗑️ Modelo descargado")