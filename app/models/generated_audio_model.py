# app/models/generated_audio_model.py

from sqlmodel import SQLModel, Field, Relationship  
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
import sqlalchemy as sa

from app.models.boletin_audio_link import BoletinAudioLink

class GeneratedAudio(SQLModel, table=True):
    __tablename__ = "generated_audios"

    id: Optional[int] = Field(default=None, primary_key=True)
    audio_id: str = Field(unique=True, index=True)
    profile_id: int = Field(foreign_key="profiles.id", index=True)
    secondary_profile_id: Optional[int] = Field(
        default=None, 
        foreign_key="profiles.id", 
        index=True
    )
    text: str = Field(sa_type=sa.Text)
    title: Optional[str] = None
    duration: float  # Duración final del audio en segundos
    waveform: Optional[str] = None  # UUID del waveform
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)
    character_count: int = Field(default=0)  # Cantidad de caracteres del texto original
    
    owner_profile: Optional["Profile"] = Relationship(
        back_populates="owned_audios",
        sa_relationship_kwargs={"foreign_keys": "[GeneratedAudio.profile_id]"}
    )
    
    secondary_profile: Optional["Profile"] = Relationship(
        back_populates="secondary_audios",
        sa_relationship_kwargs={"foreign_keys": "[GeneratedAudio.secondary_profile_id]"}
    )
    
    
    boletines: List["Boletin"] = Relationship(
        back_populates="audios",
        link_model=BoletinAudioLink
    )