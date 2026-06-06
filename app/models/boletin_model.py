# app/models/boletin_model.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone
from app.models.generated_audio_model import GeneratedAudio
from app.models.boletin_audio_link import BoletinAudioLink

class Boletin(SQLModel, table=True):
    __tablename__ = "boletin"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(
        description="Fecha y hora de inicio (formato ISO: YYYY-MM-DD HH:MM:SS)"
    )
    created_by: Optional[str] = Field(default=None, description="Usuario que creó el boletín")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    
    active: bool = Field(default=True)
    
    # Relación muchos a muchos
    audios: List["GeneratedAudio"] = Relationship(
        back_populates="boletines",
        link_model=BoletinAudioLink
    )