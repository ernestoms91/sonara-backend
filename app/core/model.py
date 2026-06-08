# app/core/model.py
import os
import torch
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

class TTSModel:
    _model = None
    _device = None
    
    @classmethod
    def _get_device(cls):
        """Determinar dispositivo (CPU/CUDA)"""
        device = settings.DEVICE.lower()
        
        if device == "cuda" and torch.cuda.is_available():
            logger.info("Usando GPU (CUDA)")
            return "cuda"
        else:
            logger.info("Usando CPU")
            return "cpu"
    
    @classmethod
    def _get_model_path(cls):
        """Construir la ruta completa del modelo"""
        model_path = os.path.join(settings.MODEL_PATH, settings.MODEL_NAME)
        
        if os.path.exists(model_path):
            logger.debug(f"Usando modelo local: {model_path}")
            return model_path
        
        logger.debug(f"Modelo no encontrado localmente, usando Hugging Face: {settings.MODEL_NAME}")
        return settings.MODEL_NAME
    
    @classmethod
    def load(cls):
        """Cargar modelo Qwen3-TTS Base (voice clone)"""
        from qwen_tts import Qwen3TTSModel
        
        if cls._model is not None:
            logger.debug("Modelo ya estaba cargado")
            return cls._model, cls._device
        
        try:
            model_path = cls._get_model_path()
            device = cls._get_device()
            
            logger.info(f"Cargando modelo desde: {model_path}")
            
            if device == "cuda":
                try:
                    import flash_attn
                    logger.info("flash-attn disponible, usando flash_attention_2")
                    dtype = torch.bfloat16
                    attn = "flash_attention_2"
                except ImportError:
                    logger.warning("flash-attn no disponible, fallback a eager")
                    dtype = torch.bfloat16
                    attn = "eager"
            else:
                dtype = torch.float32
                attn = None
            
            kwargs = {"device_map": device, "dtype": dtype}
            if attn:
                kwargs["attn_implementation"] = attn
            
            cls._model = Qwen3TTSModel.from_pretrained(model_path, **kwargs)
            
            # Aplicar Triton kernels si estamos en CUDA
            if device == "cuda":
                try:
                    from qwen3_tts_triton.models.patching import apply_triton_kernels
                    apply_triton_kernels(cls._model.model)
                    logger.info("Triton kernels aplicados (RMSNorm, SwiGLU, M-RoPE, Norm+Residual)")
                except Exception as e:
                    logger.warning(f"No se pudieron aplicar Triton kernels: {e}")
            
            cls._device = device
            logger.info(f"Modelo cargado | device={device} | dtype={dtype} | attn={attn}")
            return cls._model, cls._device
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}", exc_info=True)
            raise
    
    @classmethod
    def unload(cls):
        """Descargar modelo para liberar memoria"""
        if cls._model is not None:
            logger.info("Descargando modelo...")
            cls._model = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("Modelo descargado")
    
    @classmethod
    def get_model(cls):
        """Obtener la instancia del modelo"""
        if cls._model is None:
            cls.load()
        return cls._model, cls._device