# app/models/generated_audio_model.py
import uuid
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

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