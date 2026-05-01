# app/schemas/boletin.py
from pydantic import BaseModel, Field, field_validator
from typing import List
import re


class BoletinCreateRequest(BaseModel):
    """Schema para crear un boletín"""
    start_time: str = Field(..., min_length=5, max_length=5, description="Horario HH:MM")
    audio_ids: List[str] = Field(..., min_length=30, max_length=30, description="Lista de 30 IDs de audios")
    
    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        """Validar formato HH:MM"""

        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError(f"Formato inválido: {v}. Use HH:MM (ej: 06:00, 23:30)")
        return v
    
    @field_validator("audio_ids")
    @classmethod
    def validate_audio_ids(cls, v: List[str]) -> List[str]:
        """Validar que no haya duplicados"""
        if len(set(v)) != len(v):
            raise ValueError("No se permiten IDs duplicados en la lista")
        return v