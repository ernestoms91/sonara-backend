# app/api/deps/services.py
from typing import Annotated
from fastapi import Depends
from app.services import audio_service
from app.services.audio_service import AudioService
from app.services.auth_service import AuthService
from app.services.boletin_service import BoletinService
from app.services.profile_service import ProfileService
from app.services.tts_service import TTSService
from app.api.deps.db import DBSession
from app.api.deps.model import ModelDep


def get_tts_service(
    model_service: ModelDep
) -> TTSService:
    return TTSService(model_service)

TTSServiceDep = Annotated[TTSService, Depends(get_tts_service)]


def get_profile_service(
    db: DBSession,
    tts_service: TTSServiceDep
) -> ProfileService:
    return ProfileService(db, tts_service)  # 

ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


def get_audio_service(
    db: DBSession,
    tts_service: TTSServiceDep
) -> AudioService:
    return AudioService(db, tts_service)

AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]

def get_boletin_service(
    db: DBSession,
) -> BoletinService:
    return BoletinService(db)

BoletinServiceDep = Annotated[BoletinService, Depends(get_boletin_service)]


def get_auth_service(session: DBSession) -> AuthService:
    return AuthService(session)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]