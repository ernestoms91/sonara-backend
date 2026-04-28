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


    def get_audios_paginated(self, page: int = 1, size: int = 50) -> dict:
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
            GeneratedAudio.active == True
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