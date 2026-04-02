# app/services/tts_service.py
import os
from pathlib import Path
from qwen_tts import Qwen3TTSModel
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class TTSService:
    """Servicio para síntesis de voz con Qwen3-TTS"""
    
    @staticmethod
    def synthesize(
        text: str,
        model: Qwen3TTSModel,
        device: str,
        speaker_id: int = 0,
        output_path: str = None
    ) -> dict:
        """
        Sintetizar texto a voz
        
        Args:
            text: Texto a sintetizar
            model: Instancia del modelo Qwen3TTS
            device: Dispositivo (cuda/cpu)
            speaker_id: ID del locutor (por defecto 0)
            output_path: Ruta para guardar el audio (opcional)
        
        Returns:
            Dict con información del audio sintetizado
        """
        try:
            if not text or not text.strip():
                raise ValueError("El texto no puede estar vacío")
            
            logger.debug(f"Sintetizando texto: {text[:50]}...")
            
            # Generar audio
            samples = model.generate(
                text,
                speaker_id=speaker_id,
                show_tqdm=False
            )
            
            # Guardar archivo si se especifica
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Usar el método save del modelo
                model.save_wav(
                    samples,
                    str(output_path),
                    sr=model.sample_rate
                )
                
                logger.info(f"Audio guardado en: {output_path}")
                
                return {
                    "success": True,
                    "file": str(output_path),
                    "text": text,
                    "speaker_id": speaker_id,
                    "device": device
                }
            
            return {
                "success": True,
                "samples": samples,
                "text": text,
                "speaker_id": speaker_id,
                "device": device
            }
            
        except Exception as e:
            logger.error(f"Error sintetizando texto: {e}", exc_info=True)
            raise
    
    @staticmethod
    def synthesize_and_save(
        text: str,
        model: Qwen3TTSModel,
        device: str,
        speaker_id: int = 0,
        filename: str = None
    ) -> dict:
        """
        Sintetizar texto a voz y guardar en la carpeta de salida configurada
        
        Args:
            text: Texto a sintetizar
            model: Instancia del modelo Qwen3TTS
            device: Dispositivo (cuda/cpu)
            speaker_id: ID del locutor
            filename: Nombre del archivo (generado automáticamente si no se proporciona)
        
        Returns:
            Dict con información del archivo guardado
        """
        import uuid
        from datetime import datetime
        
        # Generar nombre de archivo si no se proporciona
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
        
        # Construir ruta completa
        output_path = Path(settings.OUTPUT_DIR) / filename
        
        return TTSService.synthesize(
            text=text,
            model=model,
            device=device,
            speaker_id=speaker_id,
            output_path=str(output_path)
        )
    
    @staticmethod
    def estimate_duration(text: str) -> float:
        """
        Estimar duración aproximada del audio en segundos
        
        Estimación simple: ~200 palabras por minuto
        """
        words = len(text.split())
        minutes = words / 200
        return minutes * 60
