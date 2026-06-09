# app/repositories/generated_audio_repository.py
from app.models.profile_model import Profile
from sqlmodel import Session, select
from app.models.generated_audio_model import GeneratedAudio
from app.core.logging import get_logger
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination import Params

logger = get_logger(__name__)


class GeneratedAudioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, audio: GeneratedAudio) -> GeneratedAudio:
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        logger.info(f"Audio guardado con ID: {audio.id}, audio_id: {audio.audio_id}")
        return audio

    def get_by_id(self, audio_id: str, active=True) -> dict | None:
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.original_duration,
            GeneratedAudio.was_compressed,
            GeneratedAudio.character_count,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.active,
            GeneratedAudio.title,
            GeneratedAudio.created_by,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(GeneratedAudio.id == audio_id, GeneratedAudio.active == active)

        result = self.db.exec(statement).first()
        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "active": result.active,
            "duration": result.duration,
            "original_duration": result.original_duration,
            "was_compressed": result.was_compressed,
            "character_count": result.character_count,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name,
            "title": result.title,
            "created_by": result.created_by,
        }

    def get_by_audio_id(self, audio_id: str, active=True) -> dict | None:
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.original_duration,
            GeneratedAudio.was_compressed,
            GeneratedAudio.character_count,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.active,
            GeneratedAudio.title,
            GeneratedAudio.created_by,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(GeneratedAudio.audio_id == audio_id, GeneratedAudio.active == active)

        result = self.db.exec(statement).first()
        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "active": result.active,
            "duration": result.duration,
            "original_duration": result.original_duration,
            "was_compressed": result.was_compressed,
            "character_count": result.character_count,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name,
            "title": result.title,
            "created_by": result.created_by,
        }

    def get_by_audio_id_with_relationship(self, audio_id: str, active: bool = True) -> GeneratedAudio | None:
        statement = select(GeneratedAudio).where(
            GeneratedAudio.audio_id == audio_id,
            GeneratedAudio.active == active
        )
        return self.db.exec(statement).first()

    def get_audios_paginated(self, page: int = 1, size: int = 50, actives=True) -> dict:
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.title,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.original_duration,
            GeneratedAudio.was_compressed,
            GeneratedAudio.character_count,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.waveform,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(
            GeneratedAudio.active == actives
        ).order_by(GeneratedAudio.created_at.desc())

        params = Params(page=page, size=size)
        result = paginate(self.db, statement, params, unique=False)
        items = [dict(item._mapping) for item in result.items]

        return {
            "items": items,
            "total": result.total,
            "page": result.page,
            "size": result.size,
            "pages": result.pages
        }

    def soft_delete(self, audio_id: str) -> None:
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        audio.active = False
        self.db.add(audio)
        self.db.commit()

    def activate(self, audio_id: str) -> None:
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        audio.active = True
        self.db.add(audio)
        self.db.commit()