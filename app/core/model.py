# backend/app/core/model_loader.py
import torch
import logging
from pathlib import Path
from app.core.config import settings
from qwen_tts import Qwen3TTSModel

logger = logging.getLogger(__name__)

class TTSModel:
    _model = None
    _device = None
    
    @classmethod
    def load(cls):
        if cls._model is None:
            try:
                # Configurar device según settings.DEVICE
                if settings.DEVICE == "cuda" and torch.cuda.is_available():
                    cls._device = "cuda:0"
                elif settings.DEVICE == "mps" and torch.backends.mps.is_available():
                    cls._device = "mps"
                else:
                    cls._device = "cpu"
                
                # Ruta del modelo: puede ser ID de HuggingFace o ruta local
                model_path = f"{settings.MODEL_PATH}/{settings.MODEL_NAME}" if settings.MODEL_PATH else settings.MODEL_NAME
                
                logger.info(f"💻 Device: {cls._device}")
                logger.info(f"📂 Cargando modelo desde: {model_path}")
                
                # Cargar modelo con qwen-tts SDK
                cls._model = Qwen3TTSModel.from_pretrained(
                    model_path,
                    device_map=cls._device,
                    dtype=torch.bfloat16,  # Qwen3-TTS recomienda bfloat16
                    attn_implementation="flash_attention_2" if settings.DEVICE == "cuda" else "sdpa",
                )
                
                if cls._device == "cuda:0":
                    logger.info(f"✅ GPU: {torch.cuda.get_device_name(0)}")
                    logger.info(f"✅ Memoria: {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)} GB")
                
                logger.info("✅ Modelo cargado exitosamente!")
                
            except Exception as e:
                logger.critical(f"❌ Error cargando modelo: {e}")
                raise
        
        return cls._model, cls._device

# Cargar modelo al importar
model, device = TTSModel.load()