# app/schemas/boletin.py
from pydantic import BaseModel, Field, field_validator
from typing import List
import re


class BoletinCreateRequest(BaseModel):
    """Schema para crear un boletín"""
    start_time: str = Field(..., min_length=5, max_length=5, description="Horario HH:MM")
    audio_ids: List[str] = Field(..., min_length=30, max_length=30, description="Lista de 30 IDs de audios")
    bol_date: str = Field(..., min_length=10, max_length=10, description="Fecha del boletín en formato YYYY-MM-DD")
    
    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        """Validar formato HH:MM"""

        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError(f"Formato inválido: {v}. Use HH:MM (ej: 06:00, 23:30)")
        return v
    
    @field_validator("bol_date")
    @classmethod
    def validate_bol_date(cls, v: str) -> str:
        """Validar formato YYYY-MM-DD"""
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError(f"Formato inválido: {v}. Use YYYY-MM-DD (ej: 2026-05-03)")
        
        # Validar que sea una fecha real (días, meses válidos)
        try:
            year, month, day = map(int, v.split('-'))
            from datetime import date
            date(year, month, day)  # Si es inválido, lanza ValueError
        except ValueError:
            raise ValueError(f"Fecha inválida: {v}. Verifique año, mes o día")
        
        return v
    
    @field_validator("audio_ids")
    @classmethod
    def validate_audio_ids(cls, v: List[str]) -> List[str]:
        """Validar que no haya duplicados"""
        if len(set(v)) != len(v):
            raise ValueError("No se permiten IDs duplicados en la lista")
        return v
    

class BoletinUpdateRequest(BaseModel):
    """Schema para actualizar un boletín"""
    audio_ids: List[str] = Field(..., min_length=30, max_length=30, description="Lista de 30 IDs de audios")
    
    @field_validator("audio_ids")
    @classmethod
    def validate_audio_ids(cls, v: List[str]) -> List[str]:
        """Validar que no haya duplicados"""
        if len(set(v)) != len(v):
            raise ValueError("No se permiten IDs duplicados en la lista")
        return v