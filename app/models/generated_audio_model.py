# app/models/generated_audio_model.py

from sqlmodel import SQLModel, Field, Relationship  
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
import sqlalchemy as sa

class GeneratedAudio(SQLModel, table=True):
    __tablename__ = "generated_audios"

    id: Optional[int] = Field(default=None, primary_key=True)
    audio_id: UUID = Field(default_factory=uuid4, unique=True, index=True)
    profile_id: int = Field(foreign_key="profiles.id", index=True)
    text: str = Field(sa_type=sa.Text)
    title: Optional[str] = None
    duration: float  # Duración final del audio en segundos
    waveform: Optional[str] = None  # UUID del waveform
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)
    
    # NUEVOS CAMPOS
    original_duration: Optional[float] = None  # Duración original antes de comprimir
    was_compressed: bool = Field(default=False)  # Si fue comprimido o no
    character_count: int = Field(default=0)  # Cantidad de caracteres del texto original
    
    owner_profile: Optional["Profile"] = Relationship(back_populates="owned_audios")
    
    boletines: List["Boletin"] = Relationship(
        back_populates="audios",
        link_model="BoletinAudioLink"
    )