# app/repositories/generated_audio_repository.py
from app.models.profile_model import Profile
from sqlmodel import Session, select, update
from app.models.generated_audio_model import GeneratedAudio
from app.core.logging import get_logger
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination import Params

logger = get_logger(__name__)


class GeneratedAudioRepository:
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

    def get_by_audio_id(self, audio_id: str, active = True) -> dict | None:
        """
        Busca un audio por su ID público.
        Hace JOIN con Profile para traer también el nombre del perfil.
        """
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.active,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(GeneratedAudio.id == audio_id, GeneratedAudio.active == active  )

        result = self.db.exec(statement).first()

        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "active":result.active,
            "duration": result.duration,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name
        }

    def get_audios_paginated(self, page: int = 1, size: int = 50, actives = True) -> dict:
        """
        Obtiene todos los audios paginados con el nombre del perfil.
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
        ).where(
            GeneratedAudio.active == actives
        ).order_by(GeneratedAudio.created_at.desc())

        params = Params(page=page, size=size)
        result = paginate(self.db, statement, params)

        items = [dict(item._mapping) for item in result.items]

        return {
            "items": items,
            "total": result.total,
            "page": result.page,
            "size": result.size,
            "pages": result.pages
        }

    def soft_delete(self, audio_id: str) -> None:
        """Soft delete: cambia active a False"""
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        audio.active = False
        self.db.add(audio)
        self.db.commit()
        
    def activate(self, audio_id: str) -> None:
        """Activate: cambia active a True"""
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        audio.active = True
        self.db.add(audio)
        self.db.commit()