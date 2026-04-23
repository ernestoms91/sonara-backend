# app/models/generated_audio_model.py
from sqlmodel import Relationship, SQLModel, Field
from typing import List, Optional
from datetime import datetime, timezone

from app.models.boletin_model import Boletin

class GeneratedAudio(SQLModel, table=True):
    __tablename__ = "generated_audio"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    audio_id: str = Field(
        unique=True, 
        index=True,
        description="UUID único para identificar el audio"
    )
    text: str = Field(max_length=1000)
    duration: float  # segundos
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profile_id: int = Field(foreign_key="profile.id", index=True)
    
     # Relación muchos a muchos (inversa)
    boletines: List["Boletin"] = Relationship(
        back_populates="audios",
        link_model="BoletinAudioLink"
    )