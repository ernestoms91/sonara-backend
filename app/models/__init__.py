# app/models/__init__.py
"""Modelos de la base de datos"""

# Importar todos los modelos para que SQLModel los registre
from app.models.profile_model import Profile
from app.models.generated_audio_model import GeneratedAudio
from app.models.boletin_model import Boletin
from app.models.boletin_audio_link import BoletinAudioLink
from app.models.user import User


__all__ = ["Profile", "GeneratedAudio", "Boletin", "BoletinAudioLink", "User"]