# app/helpers/audio_processing.py
from pydub import AudioSegment
from pathlib import Path
from typing import Dict, List, Optional
from io import BytesIO
import os
import numpy as np
import soundfile as sf
import pyrubberband as pyrb
from app.core.logging import get_logger


logger = get_logger(__name__)


class AudioMerger:
    """Helper para unir archivos de audio usando pydub y Rubberband para estiramiento de tiempo."""

    @staticmethod
    def merge_audio_files(
        audio_paths: List[str],
        output_path: str,
        output_format: str = "mp3",
        crossfade_ms: int = 0,
        silence_thresh: int = -40,
        silence_len: int = 100,
        tags: Optional[Dict[str, str]] = None,
        normalize_segments: bool = True,
        target_dBFS: float = -20.0,
    ) -> str:
        """
        Une múltiples archivos de audio en uno solo, recortando silencio innecesario.

        Args:
            audio_paths: Lista de rutas a los archivos de audio
            output_path: Ruta donde guardar el audio unido
            output_format: Formato de salida ('mp3', 'wav', etc.)
            crossfade_ms: Milisegundos de crossfade entre pistas (0 = sin fade)
            silence_thresh: Umbral de volumen considerado silencio (dB)
            silence_len: Mínimo ms seguidos de silencio para recortar

        Returns:
            str: Ruta del archivo de salida

        Ejemplo:
            >>> AudioMerger.merge_audio_files(
            ...     ["audio1.mp3", "audio2.mp3"],
            ...     "output/merged.mp3",
            ...     crossfade_ms=50
            ... )
        """
        if not audio_paths:
            raise ValueError("No se proporcionaron archivos de audio")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        combined = AudioSegment.from_file(audio_paths[0])
        combined = combined.strip_silence(
            silence_len=silence_len,
            silence_thresh=silence_thresh,
            padding=0
        )
        if normalize_segments:
            combined = AudioMerger.match_target_amplitude(combined, target_dBFS)
        logger.info(
            f"Audio cargado: {audio_paths[0]} "
            f"(duración: {combined.duration_seconds:.2f}s)"
        )

        for path in audio_paths[1:]:
            next_audio = AudioSegment.from_file(path)
            next_audio = next_audio.strip_silence(
                silence_len=silence_len,
                silence_thresh=silence_thresh,
                padding=0
            )
            if normalize_segments:
                next_audio = AudioMerger.match_target_amplitude(next_audio, target_dBFS)

            if crossfade_ms > 0:
                combined = combined.append(next_audio, crossfade=crossfade_ms)
            else:
                combined += next_audio

            logger.info(
                f"  + {path} (duración: {next_audio.duration_seconds:.2f}s)"
            )

        export_format = output_format
        export_codec = None
        if output_format == "m4a":
            export_format = "mp4"
            export_codec = "aac"

        combined.export(output_path, format=export_format, codec=export_codec, tags=tags)

        logger.info(
            f"Audio unido guardado: {output_path} "
            f"(duración total: {combined.duration_seconds:.2f}s)"
        )

        return output_path
     
    @staticmethod
    def match_target_amplitude(
        audio_segment: AudioSegment,
        target_dBFS: float = -20.0,
    ) -> AudioSegment:
        """Ajusta el nivel a un dBFS objetivo sin afectar la duración."""
        if audio_segment.dBFS == float("-inf"):
            return audio_segment
        change_in_dBFS = target_dBFS - audio_segment.dBFS
        return audio_segment.apply_gain(change_in_dBFS)

    @staticmethod
    def concatenate_audio_files(
        audio_paths: List[str],
        output_path: str,
        output_format: str = "mp3",
        crossfade_ms: int = 0,
        tags: Optional[Dict[str, str]] = None,
        normalize_segments: bool = True,
        target_dBFS: float = -20.0,
    ) -> str:
        """Concatena archivos de audio sin recortar silencios adicionales."""
        if not audio_paths:
            raise ValueError("No se proporcionaron archivos de audio")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        combined = AudioSegment.from_file(audio_paths[0])
        if normalize_segments:
            combined = AudioMerger.match_target_amplitude(combined, target_dBFS)

        for path in audio_paths[1:]:
            next_audio = AudioSegment.from_file(path)
            if normalize_segments:
                next_audio = AudioMerger.match_target_amplitude(next_audio, target_dBFS)
            if crossfade_ms > 0:
                combined = combined.append(next_audio, crossfade=crossfade_ms)
            else:
                combined += next_audio

        export_format = output_format
        export_codec = None
        if output_format == "m4a":
            export_format = "mp4"
            export_codec = "aac"

        combined.export(output_path, format=export_format, codec=export_codec, tags=tags)
        return output_path

    @staticmethod
    def enforce_duration(
        audio_path: str,
        output_path: str,
        target_seconds: float = 60.0,
        output_format: str = "mp3",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Ajusta un audio a una duración exacta, truncando o rellenando con silencio."""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"No se encuentra: {audio_path}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        audio = AudioSegment.from_file(audio_path)
        target_ms = int(target_seconds * 1000)

        if len(audio) > target_ms:
            audio = audio[:target_ms]
        elif len(audio) < target_ms:
            audio = audio + AudioSegment.silent(duration=target_ms - len(audio))

        export_format = output_format
        export_codec = None
        if output_format == "m4a":
            export_format = "mp4"
            export_codec = "aac"

        audio.export(output_path, format=export_format, codec=export_codec, tags=tags)
        return output_path

    @staticmethod
    def calculate_duration_difference(
        audio_path: str,
        target_seconds: float = 60.0,
    ) -> float:
        """
        Calcula la diferencia entre la duración actual del audio y el objetivo.
        
        Args:
            audio_path: Ruta del archivo de audio
            target_seconds: Duración objetivo en segundos (por defecto 60)
            
        Returns:
            float: Diferencia en segundos (positivo = falta, negativo = sobra)
            
        Ejemplo:
            >>> diff = AudioMerger.calculate_duration_difference("audio.m4a", 60)
            >>> if diff > 0:
            ...     print(f"Faltan {diff:.2f} segundos")
            >>> elif diff < 0:
            ...     print(f"Sobran {abs(diff):.2f} segundos")
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"No se encuentra: {audio_path}")
        
        audio = AudioSegment.from_file(audio_path)
        current_duration = audio.duration_seconds
        
        diferencia = target_seconds - current_duration
        
        logger.info(f"Duración actual: {current_duration:.2f}s | Objetivo: {target_seconds:.2f}s | Diferencia: {diferencia:.2f}s")
        
        return diferencia
    

    @staticmethod
    def get_duration(
        audio_path: str,
    ) -> int:
        """
        Obtiene la duración de un archivo de audio en segundos (redondeado a entero).
        
        Args:
            audio_path: Ruta del archivo de audio
            
        Returns:
            int: Duración en segundos (redondeado)
            
        Ejemplo:
            >>> duracion = AudioMerger.get_duration("audio.m4a")
            >>> print(f"El audio dura {duracion} segundos")
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"No se encuentra: {audio_path}")
        
        audio = AudioSegment.from_file(audio_path)
        duration = round(audio.duration_seconds)
        
        logger.info(f"Duración del audio {audio_path}: {duration}s")
        
        return duration

    @staticmethod
    def get_duration_seconds(
        audio_path: str,
    ) -> float:
        """Obtiene la duración de un archivo de audio en segundos como float."""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"No se encuentra: {audio_path}")

        audio = AudioSegment.from_file(audio_path)
        duration = audio.duration_seconds

        logger.info(f"Duración del audio {audio_path}: {duration:.3f}s")
        return duration

    @staticmethod
    def adjust_duration(
        input_path: str,
        output_path: str,
        target_seconds: float = 60.0,
        output_format: str = "mp3",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Ajusta la duración de un audio usando Rubberband para mantener el tono original.
        Optimizado para voz hablada con reducciones moderadas (hasta 25%).
        
        Si el audio es más largo, lo acelera (time-stretch) manteniendo el pitch.
        Si es más corto, lo ralentiza (time-stretch) manteniendo el pitch.
        """
        if not Path(input_path).exists():
            raise FileNotFoundError(f"No se encuentra: {input_path}")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        audio = AudioSegment.from_file(input_path)
        current_seconds = audio.duration_seconds
        
        if target_seconds <= 0 or current_seconds <= 0:
            raise ValueError(f"Duración inválida: current={current_seconds}, target={target_seconds}")

        stretch_ratio = target_seconds / current_seconds
        
        logger.info(
            f"adjust_duration: {current_seconds:.2f}s -> {target_seconds:.2f}s "
            f"({stretch_ratio*100:.1f}%)"
        )

        if abs(current_seconds - target_seconds) <= 0.05:
            audio.export(output_path, format=output_format, tags=tags)
            logger.info(f"Sin cambios necesarios")
            return output_path

        logger.info(f"Aplicando Rubberband optimizado para voz...")
        
        temp_wav = Path(output_path).parent / f"temp_{Path(input_path).stem}.wav"
        audio.export(temp_wav, format="wav")
        
        try:
            y, sr = sf.read(str(temp_wav))
            
            stretch_ratio = target_seconds / current_seconds
            
            y_stretched = pyrb.time_stretch(
                y, 
                sr, 
                stretch_ratio,
                rbargs={
                    '--crispness': 6,
                    '--finer': True,
                    '--window': 'long',
                }
            )
            
            temp_stretched_wav = Path(output_path).parent / f"stretched_{Path(input_path).stem}.wav"
            sf.write(str(temp_stretched_wav), y_stretched, sr)
            
            stretched_audio = AudioSegment.from_wav(str(temp_stretched_wav))
            
            if abs(stretched_audio.duration_seconds - target_seconds) > 0.01:
                target_ms = int(target_seconds * 1000)
                if len(stretched_audio) > target_ms:
                    stretched_audio = stretched_audio[:target_ms]
                elif len(stretched_audio) < target_ms:
                    stretched_audio = stretched_audio + AudioSegment.silent(duration=target_ms - len(stretched_audio))
            
            export_format = output_format
            export_codec = None
            if output_format == "m4a":
                export_format = "mp4"
                export_codec = "aac"
            
            stretched_audio.export(output_path, format=export_format, codec=export_codec, tags=tags)
            
            try:
                temp_wav.unlink()
                temp_stretched_wav.unlink()
            except:
                pass
            
            logger.info(
                f"Audio ajustado con Rubberband: {current_seconds:.2f}s -> {stretched_audio.duration_seconds:.2f}s "
                f"(target: {target_seconds:.2f}s)"
            )
            
        except Exception as e:
            logger.warning(f"Rubberband fallo, usando speedup: {e}")
            speed_factor = current_seconds / target_seconds
            audio = audio.speedup(playback_speed=speed_factor)
            audio.export(output_path, format=output_format, tags=tags)
        
        return output_path