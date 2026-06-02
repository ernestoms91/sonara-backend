# app/services/audio_service.py
import json  
import io
import uuid
from fastapi import Request
from scipy import signal
import soundfile as sf
import re
import numpy as np
from pathlib import Path
from sqlmodel import Session
from sympy import false
from app.core.config import settings
from app.core.logging import get_logger
from app.helpers.generate_peaks import generate_peaks_from_array
from app.models.generated_audio_model import GeneratedAudio
from app.repositories.generated_audio_repository import GeneratedAudioRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.tts_service import TTSService

logger = get_logger(__name__)


class AudioService:
    def __init__(self, db: Session, tts_service: TTSService):
        self.db = db
        self.tts_service = tts_service
        self.profile_repo = ProfileRepository(db)
        self.audio_repo = GeneratedAudioRepository(db)
        self.audios_base_dir = Path(settings.OUTPUT_DIR) / "generated"
        self.waveforms_base_dir = Path(settings.OUTPUT_DIR) / "waveforms"

    def _extract_first_sentence(self, text: str) -> str:
        """
        Extrae la primera oración del texto para usar como título.
        """
        if not text:
            return "Audio sin título"

        clean = text.strip()
        # Buscar primera oración (termina en . ! ?)
        match = re.search(r"(.+?[\.\!\?])(?:\s|$)", clean)
        if match:
            first_sentence = match.group(1).strip()
            # Limitar a 60 caracteres para metadata (evitar problemas)
            if len(first_sentence) > 60:
                first_sentence = first_sentence[:57] + "..."
            return first_sentence

        # Si no encuentra puntuación, tomar primera línea o primeros 60 caracteres
        first_line = clean.splitlines()[0].strip()
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."
        return first_line if first_line else "Audio sin título"
    
    
    def generate_and_save(self, profile_id: int, text: str, created_by: str) -> dict:
        """
        Genera audio y guarda tanto el archivo como los metadatos en BD.
        """
        # 1. Validar perfil
        profile = self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Perfil {profile_id} no encontrado")

        if not profile.active:
            raise ValueError(f"Perfil {profile_id} no está activo")

        # 2. Generar UUID para el audio
        audio_uuid = str(uuid.uuid4())

        # 3. Cargar prompt
        profile_folder = Path(settings.OUTPUT_DIR) / "profiles" / profile.folder_id
        prompt_path = profile_folder / f"{profile.name.lower()}.pt"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt no encontrado: {prompt_path}")

        prompt = self.tts_service.load_prompt(str(prompt_path))

        # 4. Generar audio
        audio_array, sample_rate = self.tts_service.synthesize(prompt, text)
        duration = len(audio_array) / sample_rate
        
        # 5. Generar peaks (waveform)
        peaks = generate_peaks_from_array(audio_array, sample_rate, pixels_per_second=settings.PIXELS_PER_SECOND)

        # Crear estructura del JSON
        waveform_data = {
            "sample_rate": sample_rate,
            "bits": 8,
            "duration": float(duration),
            "channels": 1 if len(audio_array.shape) == 1 else 2,
            "pixels_per_second": 20,
            "data_overview_length": len(peaks),
            "data": peaks,
        }

        # Nombre del archivo de waveform
        waveform_filename = f"{audio_uuid}.json"
        waveform_path = self.waveforms_base_dir / waveform_filename

        # Guardar JSON
        with open(waveform_path, "w", encoding="utf-8") as f:
            json.dump(waveform_data, f, ensure_ascii=False)

        logger.info(f"Waveform guardado en: {waveform_path}")

        # 6. Guardar archivo
        self.audios_base_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{audio_uuid}.wav"
        audio_path = self.audios_base_dir / filename
        
        sf.write(audio_path, audio_array, sample_rate)
        logger.info(f"Audio guardado en: {audio_path}")

        # 7. Guardar metadatos en BD (con espectro)
        audio_metadata = GeneratedAudio(
            audio_id=audio_uuid,
            profile_id=profile_id,
            text=text,
            duration=duration,
            title=self._extract_first_sentence(text),
            waveform=audio_uuid,
            created_by=created_by
        )
        saved_audio = self.audio_repo.create(audio_metadata)

        # 8. Preparar respuesta
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_array, sample_rate, format='wav')
        audio_bytes = audio_buffer.getvalue()

        return {
            "id": saved_audio.id,
            "audio_id": saved_audio.audio_id,
            "audio_bytes": audio_bytes,
            "filename": filename,
            "duration": duration,
            "created_at": saved_audio.created_at,
            "waveform": waveform_data
        }

    def change_audio_duration(self, audio_id: str, target_duration: float) -> dict:
        """
        Cambia la duración de un audio usando scipy.signal.resample.
        Para cambios pequeños (5-10%), la diferencia de tono es imperceptible.
        """
        # 1. Obtener metadatos del audio original
        audio_info = self.audio_repo.get_by_id(audio_id)
        if not audio_info:
            raise ValueError(f"Audio {audio_id} no encontrado")

        # 2. Buscar el archivo original
        original_path = self.audios_base_dir / f"{audio_id}.wav"
        if not original_path.exists():
            raise FileNotFoundError(
                f"Archivo de audio no encontrado: {original_path}")

        # 3. Cargar audio
        audio_array, sample_rate = sf.read(original_path)

        # 4. Asegurar que es mono
        if audio_array.ndim == 2:
            audio_array = np.mean(audio_array, axis=1)
            logger.info("Audio convertido de estéreo a mono")

        # 5. Calcular duración actual
        current_duration = len(audio_array) / sample_rate
        logger.info(
            f"Original: duración={current_duration:.4f}s, sample_rate={sample_rate}")
        logger.info(f"Target: duración={target_duration:.4f}s")

        # 6. Calcular nuevo número de muestras
        new_length = int(round(target_duration * sample_rate))
        logger.info(
            f"Nuevas muestras: {new_length} (original: {len(audio_array)})")

        # 7. Redimensionar usando scipy.resample
        # Nota: esto cambia la duración y el tono ligeramente
        audio_resampled = signal.resample(audio_array, new_length)

        # 8. Verificar resultado
        if audio_resampled.size == 0:
            raise RuntimeError("Resample produjo un audio vacío")

        # 9. Normalizar volumen para evitar saturación
        max_abs = np.max(np.abs(audio_resampled))
        if max_abs > 0:
            audio_resampled = audio_resampled / max_abs * 0.95
            logger.info(f"Volumen normalizado (max original: {max_abs:.4f})")

        # 10. Guardar como nuevo audio
        new_audio_uuid = str(uuid.uuid4())
        new_filename = f"{new_audio_uuid}.wav"
        new_audio_path = self.audios_base_dir / new_filename

        sf.write(new_audio_path, audio_resampled.astype(
            np.float32), sample_rate, subtype='PCM_16')

        # 11. Verificar el resultado
        new_duration = len(audio_resampled) / sample_rate
        logger.info(
            f"Nuevo audio: duración={new_duration:.4f}s, guardado en {new_audio_path}")

        # 12. Guardar metadatos en BD
        new_audio_metadata = GeneratedAudio(
            audio_id=new_audio_uuid,
            profile_id=audio_info["profile_id"],
            text=audio_info["text"],
            duration=new_duration
        )
        saved_audio = self.audio_repo.create(new_audio_metadata)

        # 13. Preparar respuesta
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_resampled, sample_rate,
                 format='WAV', subtype='PCM_16')
        audio_bytes = audio_buffer.getvalue()

        return {
            "id": saved_audio.id,
            "audio_id": saved_audio.audio_id,
            "audio_bytes": audio_bytes,
            "filename": new_filename,
            "original_audio_id": audio_id,
            "original_duration": current_duration,
            "new_duration": new_duration,
            "created_at": saved_audio.created_at
        }

    def get_audios_paginated(
        self,
        page: int = 1,
        size: int = 50,
        actives = True,
        request: Request = None
    ) -> dict:
        """
        Obtiene todos los audios paginados con nombre del perfil.

        Args:
            page: Número de página (default: 1)
            size: Items por página (default: 50, max: 100)

        Returns:
            Dict con items, total, page, size, pages
        """
        # Reglas de negocio: límite máximo de 100 items por página
        if size > 100:
            logger.warning(
                f"Tamaño de página {size} excede el límite, limitando a 100")
            size = 100

        # Validar que page sea al menos 1
        if page < 1:
            logger.warning(f"Página {page} inválida, usando página 1")
            page = 1

        logger.info(
            f"Obteniendo audios paginados - Página: {page}, Tamaño: {size}")

        result = self.audio_repo.get_audios_paginated(page=page, size=size, actives=actives)
        
        if request and result.get("items"):
                base_url = str(request.base_url).rstrip('/')
                for item in result["items"]:
                    audio_id = item.get("audio_id")
                    if audio_id:
                        item["waveform_url"] = f"{base_url}/waveforms/{audio_id}.json"
                        item["audio_url"] = f"{base_url}/audios/{audio_id}.wav"

        # logger.info(
        #     f"Audios obtenidos - Total: {result['total']}, Páginas: {result['pages']}")
        return result
    

    def soft_delete_audio(self, audio_id: str) -> dict:
        """
        Soft delete: desactiva un audio (cambia active a False)
        """
        # 1. Verificar que el audio existe y obtener su estado actual
        audio = self.audio_repo.get_by_id(audio_id)
        
        if not audio:
            raise ValueError(f"Audio {audio_id} no encontrado o se encuentra desactivado")
        
        # 2. Ejecutar soft delete
        self.audio_repo.soft_delete(audio_id)
        
        # 3. Log de la operación
        logger.info(f"Audio {audio_id} desactivado (soft delete)")
        
        # 4. Retornar respuesta
        return {
            "audio_id": audio_id,
            "message": "Audio desactivado correctamente",
            "profile_id": audio["profile_id"],
            "profile_name": audio["profile_name"]
        }
        
    def activate_audio(self, audio_id: str) -> dict:
        """
        Activate: Activa un audio (cambia active a true)
        """
        # 1. Verificar que el audio existe y obtener su estado actual
        audio = self.audio_repo.get_by_id(audio_id, active=0)
        
        if not audio:
            raise ValueError(f"Audio {audio_id} no encontrado")
        
        # 2. Activar
        self.audio_repo.activate(audio_id)
        
        # 3. Log de la operación
        logger.info(f"Audio {audio_id} activado")
        
        # 4. Retornar respuesta
        return {
            "audio_id": audio_id,
            "message": "Audio activado",
            "profile_id": audio["profile_id"],
            "profile_name": audio["profile_name"]
        }