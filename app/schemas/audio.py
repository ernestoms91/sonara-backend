# app/schemas/audio.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

# --- Request Schemas ---
class GenerateAudioRequest(BaseModel):
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        example="Hola mundo, esta es una prueba"
    )
    
class ChangeDurationRequest(BaseModel):
    target_duration: float = Field(
        ..., 
        gt=0.1, 
        le=60.0,
        description="Duración deseada en segundos",
        example=3.5
    )

# --- Response Schemas ---
class AudioDataResponse(BaseModel):
    audio_id: UUID
    duration: float
    filename: str
    created_at: Optional[datetime] = None

class DurationChangedResponse(BaseModel):
    audio_id: UUID
    original_audio_id: UUID
    original_duration: float
    new_duration: float
    filename: str
    created_at: Optional[datetime] = None

# También puedes tener schemas para otros endpoints
class AudioListItem(BaseModel):
    id: UUID
    profile_name: str
    text_snippet: str
    duration: float
    created_at: datetime
    active: bool