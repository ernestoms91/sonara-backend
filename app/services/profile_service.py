# app/services/profile_service.py
import uuid
import io
import tempfile
import shutil
import soundfile as sf
from pathlib import Path
from sqlmodel import Session
from app.core.logging import get_logger
from app.models.profile_model import Profile
from app.repositories.profile_repository import ProfileRepository
from app.services.tts_service import TTSService
from app.utils.validators.audio_validator import AudioValidator
from app.core.config import settings

logger = get_logger(__name__)


class ProfileService:
    def __init__(self, db: Session, tts_service: TTSService):
        self.repo = ProfileRepository(db)
        self.db = db
        self.tts_service = tts_service
        self.profiles_base_dir = Path(settings.OUTPUT_DIR) / "profiles"
        self.audios_base_dir = Path(settings.OUTPUT_DIR) / "generated"

    def create_profile(
        self,
        name: str,
        ref_text: str,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        language: str = "Spanish"
    ) -> Profile:
        """
        Crea perfil de forma ATÓMICA con folder_id UUID
        """
        AudioValidator.validate(audio_bytes, filename, content_type)

        ext = Path(filename).suffix.lower()
        temp_path = None
        profile_folder = None

        # Generar folder_id antes de crear la carpeta
        folder_id = str(uuid.uuid4())

        try:
            # 1. Crear carpeta con folder_id + nombre
            safe_name = "".join(c for c in name.strip()
                                if c.isalnum() or c in " ._-")
            folder_name = f"{folder_id}"
            profile_folder = self.profiles_base_dir / folder_name
            profile_folder.mkdir(parents=True, exist_ok=True)

            audio_path = profile_folder / f"{name.strip().capitalize()}{ext}"
            prompt_path = profile_folder / f"{name.lower()}.pt"

            # 2. Guardar audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            shutil.copy2(temp_path, audio_path)
            logger.info(f"Audio guardado: {audio_path}")

            # 3. Generar prompt
            self.tts_service.generate_and_save_prompt(
                audio_path=str(audio_path),
                ref_text=ref_text,
                prompt_path=prompt_path
            )

            # 4. Guardar en BD (el id auto-incremento lo pone la BD)
            profile = Profile(
                folder_id=folder_id,
                name=name.strip(),
                language=language,
                ref_text=ref_text.strip(),
                model_type=settings.MODEL_NAME,
                active=False,
                hours_ready=False,
                minutes_ready=False,
                connectors_ready=False
            )

            profile = self.repo.create(profile, None)
            logger.info(
                f"Perfil '{name}' creado con ID: {profile.id}, folder_id: {folder_id}")

            return profile

        except Exception as e:
            logger.error(f"Error creando perfil: {e}")
            if profile_folder and profile_folder.exists():
                shutil.rmtree(profile_folder)
            raise

        finally:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)

    def generate_audio_by_profile(self, profile_id: int, text: str) -> bytes:
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {profile_id} not found")

        if not profile.active:
            raise ValueError(f"Profile with ID {profile_id} is not active yet")

        if profile.model_type != settings.MODEL_NAME:
            raise ValueError(
                f"Profile with ID {profile_id} is not compatible with the current model")

        prompt_path = self.profiles_base_dir / \
            profile.folder_id / f"{profile.name.lower()}.pt"

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found for profile ID {profile_id}")

        prompt = self.tts_service.load_prompt(str(prompt_path))

        audio , sample_rate = self.tts_service.synthesize(
            prompt=prompt,
            text=text
        )

        return self._save_generated_audio(
            profile_id=profile_id,
            profile_name=profile.name,
            text=text,
            audio=audio,
            sample_rate=sample_rate
        )


    def _save_generated_audio(
        self,
        profile_id: int,
        profile_name: str,
        text: str,
        audio,
        sample_rate: int
    ) -> dict:
        """
        Guarda el audio generado en la carpeta generated
        """
        # Crear nombre de archivo único
        import time
        timestamp = int(time.time())
        # Limpiar el texto para el nombre del archivo (primeros 50 caracteres)
        clean_text = "".join(
            c for c in text[:50] if c.isalnum() or c in " ._-").strip()
        if not clean_text:
            clean_text = "audio"

        filename = f"{profile_name}_{clean_text}_{timestamp}.wav"

        # Crear la carpeta si no existe
        self.audios_base_dir.mkdir(parents=True, exist_ok=True)

        # Ruta completa del archivo
        audio_path = self.audios_base_dir / filename

        # Guardar el archivo de audio
        sf.write(audio_path, audio, sample_rate)
        logger.info(f"Audio guardado en: {audio_path}")

        # También devolver los bytes para compatibilidad con la API
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio, sample_rate, format='wav')
        audio_bytes = audio_buffer.getvalue()

        return {
            "audio_bytes": audio_bytes,
            "audio_path": str(audio_path),
            "filename": filename,
            "sample_rate": sample_rate,
            "duration": len(audio) / sample_rate if audio is not None else 0
        }
