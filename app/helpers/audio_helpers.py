# app/helpers/audio_helpers.py
import io
import uuid
from pathlib import Path
from typing import List, Union
import numpy as np
import soundfile as sf
from pydub import AudioSegment

from app.core.logging import get_logger

logger = get_logger(__name__)


class AudioMerger:
    """
    Helper para unir múltiples archivos de audio.
    Soporta diferentes formatos y estrategias de unión.
    """
    
    @staticmethod
    def merge_audio_files(
        audio_paths: List[Union[str, Path]],
        output_format: str = "wav",
        crossfade_ms: int = 0
    ) -> bytes:
        """
        Une múltiples archivos de audio en uno solo usando pydub.
        
        Args:
            audio_paths: Lista de rutas a los archivos de audio
            output_format: Formato de salida (wav, mp3, ogg, etc.)
            crossfade_ms: Milisegundos de crossfade entre pistas (0 = sin fade)
            
        Returns:
            bytes: Audio unido en formato bytes
        """
        if not audio_paths:
            raise ValueError("No se proporcionaron archivos de audio")
        
        # Cargar el primer audio
        combined = AudioSegment.from_file(audio_paths[0])
        
        # Unir el resto con crossfade opcional
        for path in audio_paths[1:]:
            next_audio = AudioSegment.from_file(path)
            if crossfade_ms > 0:
                combined = combined.append(next_audio, crossfade=crossfade_ms)
            else:
                combined += next_audio
        
        # Exportar a bytes
        buffer = io.BytesIO()
        combined.export(buffer, format=output_format)
        buffer.seek(0)
        
        logger.info(f"Audio unido: {len(audio_paths)} archivos, "
                   f"duración total: {len(combined)/1000:.2f}s")
        
        return buffer.getvalue()
    
    @staticmethod
    def merge_audio_arrays(
        audio_arrays: List[np.ndarray],
        sample_rate: int
    ) -> np.ndarray:
        """
        Une arrays de numpy (útil si ya tienes audio cargado en memoria).
        
        Args:
            audio_arrays: Lista de arrays numpy con los audios
            sample_rate: Frecuencia de muestreo (debe ser la misma para todos)
            
        Returns:
            np.ndarray: Audio unido
        """
        if not audio_arrays:
            raise ValueError("No se proporcionaron arrays de audio")
        
        # Asegurar que todos sean mono
        mono_arrays = []
        for arr in audio_arrays:
            if arr.ndim == 2:
                mono_arrays.append(np.mean(arr, axis=1))
            else:
                mono_arrays.append(arr)
        
        # Concatenar
        merged = np.concatenate(mono_arrays)
        
        logger.info(f"Arrays unidos: {len(audio_arrays)} archivos, "
                   f"total muestras: {len(merged)}")
        
        return merged