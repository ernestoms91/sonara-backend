# models/profile.py
from sqlmodel import Relationship, SQLModel, Field
from typing import List, Optional
from datetime import datetime, timezone

from app.models.generated_audio_model import GeneratedAudio


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    id: Optional[int] = Field(default=None, primary_key=True)
    folder_id: str = Field(unique=True, index=True)
    name: str = Field(index=True, min_length=1, max_length=50)
    model_type: str = Field(min_length=1, max_length=50)
    active: bool = Field(default=False)
    hours_ready : bool = Field(default=False)
    minutes_ready : bool = Field(default=False)
    connectors_ready  : bool = Field(default=False)
    language: str = Field(default="Spanish")
    ref_text: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    #Relación: Un Profile tiene muchos GeneratedAudio - nombre más claro
    owned_audios: List["GeneratedAudio"] = Relationship(
        back_populates="owner_profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )