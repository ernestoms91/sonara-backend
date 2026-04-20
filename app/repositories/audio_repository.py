# app/repositories/audio_repository.py
from app.models.profile_model import Profile
from sqlmodel import Session, select
from app.models.generated_audio_model import GeneratedAudio
from app.core.logging import get_logger

logger = get_logger(__name__)


class AudioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, audio: GeneratedAudio) -> GeneratedAudio:
        """Guarda un audio generado en BD"""
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        logger.info(
            f"Audio guardado con ID: {audio.id}, audio_id: {audio.audio_id}")
        return audio

    def get_by_audio_id(self, audio_id: str) -> dict | None:
        """
        Busca un audio por su UUID público.
        Hace JOIN con Profile para traer también el nombre del perfil.
        """
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(GeneratedAudio.audio_id == audio_id)

        result = self.db.exec(statement).first()

        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "duration": result.duration,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name
        }

    def get_by_profile_id(self, profile_id: int) -> list[GeneratedAudio]:
        """Obtiene todos los audios de un perfil"""
        statement = select(GeneratedAudio).where(
            GeneratedAudio.profile_id == profile_id)
        return list(self.db.exec(statement).all())

    def delete(self, audio_id: str) -> bool:
        """Elimina un audio de la BD (solo metadatos)"""
        audio = self.get_by_audio_id(audio_id)
        if audio:
            self.db.delete(audio)
            self.db.commit()
            logger.info(f"Audio {audio_id} eliminado de BD")
            return True
        return False
