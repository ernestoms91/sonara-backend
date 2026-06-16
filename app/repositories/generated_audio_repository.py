# app/repositories/generated_audio_repository.py
from sqlalchemy.orm import joinedload

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

    def get_by_id(self, audio_id: str, active: bool = True) -> dict | None:
        """Obtiene un audio por su ID numérico."""
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.character_count,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.active,
            GeneratedAudio.title,
            GeneratedAudio.created_by,
            GeneratedAudio.waveform,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(
            GeneratedAudio.id == audio_id,  # Nota: audio_id es el ID numérico
            GeneratedAudio.active == active
        )

        result = self.db.exec(statement).first()
        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "active": result.active,
            "duration": result.duration,
            "character_count": result.character_count,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name,
            "title": result.title,
            "created_by": result.created_by,
            "waveform": result.waveform,
        }

    def get_by_audio_id(self, audio_uuid: str, active: bool = True) -> dict | None:
        """Obtiene un audio por su UUID (audio_id)."""
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.text,
            GeneratedAudio.duration,
            GeneratedAudio.character_count,
            GeneratedAudio.created_at,
            GeneratedAudio.profile_id,
            GeneratedAudio.active,
            GeneratedAudio.title,
            GeneratedAudio.created_by,
            GeneratedAudio.waveform,
            Profile.name.label("profile_name")
        ).join(
            Profile, GeneratedAudio.profile_id == Profile.id
        ).where(
            GeneratedAudio.audio_id == audio_uuid,
            GeneratedAudio.active == active
        )

        result = self.db.exec(statement).first()
        if not result:
            return None

        return {
            "id": result.id,
            "audio_id": result.audio_id,
            "text": result.text,
            "active": result.active,
            "duration": result.duration,
            "character_count": result.character_count,
            "created_at": result.created_at,
            "profile_id": result.profile_id,
            "profile_name": result.profile_name,
            "title": result.title,
            "created_by": result.created_by,
            "waveform": result.waveform,
        }

    def get_by_audio_uuid(self, audio_uuid: str, active: bool = True) -> GeneratedAudio | None:
        """Obtiene el objeto GeneratedAudio completo por su UUID."""
        statement = select(GeneratedAudio).where(
            GeneratedAudio.audio_id == audio_uuid,
            GeneratedAudio.active == active
        )
        return self.db.exec(statement).first()

    def get_audios_paginated(self, page: int = 1, size: int = 50, actives: bool = True) -> dict:
        """Obtiene audios paginados."""
        statement = select(
            GeneratedAudio.id,
            GeneratedAudio.audio_id,
            GeneratedAudio.title,
            GeneratedAudio.text,
            GeneratedAudio.duration,
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
        """Soft delete por ID numérico."""
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        if audio:
            audio.active = False
            self.db.add(audio)
            self.db.commit()
            logger.info(f"Audio {audio_id} desactivado")
        else:
            logger.warning(f"Audio {audio_id} no encontrado para soft delete")

    def activate(self, audio_id: str) -> None:
        """Activar audio por ID numérico."""
        statement = select(GeneratedAudio).where(GeneratedAudio.id == audio_id)
        audio = self.db.exec(statement).first()
        if audio:
            audio.active = True
            self.db.add(audio)
            self.db.commit()
            logger.info(f"Audio {audio_id} activado")
        else:
            logger.warning(f"Audio {audio_id} no encontrado para activar")
            
    def get_by_audio_id_with_relationship(self, audio_id: str):
        """
        Obtiene un audio con la relación owner_profile cargada.
        Retorna un objeto GeneratedAudio con el perfil accesible como .owner_profile
        """
        statement = (
            select(GeneratedAudio)
            .options(joinedload(GeneratedAudio.owner_profile))
            .where(GeneratedAudio.audio_id == audio_id, GeneratedAudio.active == True)
        )
        result = self.db.exec(statement).unique().first()
        return result