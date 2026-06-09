# app/schemas/audio.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from uuid import UUID


class GenerateAudioRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        example="Hola mundo, esta es una prueba"
    )


class GenerateDuetRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Texto con marcadores [P1], [P2], [P3], etc. Cada párrafo máximo 1000 caracteres.",
        example="[P1] Hola, soy la primera voz. [P2] Y yo soy la segunda voz. [P3] Volvemos con la primera. [P4] Cerramos con la segunda."
    )

    @field_validator("text")
    @classmethod
    def validate_paragraphs(cls, v: str) -> str:
        import re
        markers = re.findall(r'\[P(\d+)\]', v, re.IGNORECASE)
        if not markers:
            raise ValueError("El texto debe contener al menos un marcador [P1]")

        total = max(int(m) for m in markers)

        for i in range(1, total + 1):
            if i < total:
                pattern = rf'\[P{i}\](.*?)(?=\[P{i+1}\])'
            else:
                pattern = rf'\[P{i}\](.*?)$'

            match = re.search(pattern, v, re.DOTALL | re.IGNORECASE)
            if not match:
                raise ValueError(f"No se encontró el marcador [P{i}]")

            paragraph = match.group(1).strip()
            if not paragraph:
                raise ValueError(f"El marcador [P{i}] está vacío")

            if len(paragraph) > 1000:
                raise ValueError(
                    f"El párrafo [P{i}] excede los 1000 caracteres ({len(paragraph)} caracteres)"
                )

        return v


class ChangeDurationRequest(BaseModel):
    target_duration: float = Field(
        ...,
        gt=0.1,
        le=300.0,
        description="Duración deseada en segundos (máx 300s / 5 minutos)",
        example=3.5
    )


class AudioDataResponse(BaseModel):
    audio_id: UUID
    duration: float
    original_duration: Optional[float] = None
    was_compressed: bool = False
    character_count: int = 0
    filename: str
    created_at: Optional[datetime] = None


class DuetAudioDataResponse(BaseModel):
    audio_id: UUID
    duration: float
    original_duration: Optional[float] = None
    was_compressed: bool = False
    character_count: int = 0
    filename: str
    created_at: Optional[datetime] = None
    profile_a: str
    profile_b: str


class DurationChangedResponse(BaseModel):
    audio_id: UUID
    original_audio_id: UUID
    original_duration: float
    new_duration: float
    filename: str
    created_at: Optional[datetime] = None