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