# app/schemas/boletin.py
from pydantic import BaseModel, Field, field_validator
from typing import List
from datetime import datetime

class BoletinCreateRequest(BaseModel):
    start_time: datetime = Field(..., description="Fecha y hora ISO 8601")
    audio_ids: List[str] = Field(..., min_length=30, max_length=30)
    
    @field_validator("start_time")
    @classmethod  # ← Añadir esto
    def validate_start_time(cls, v: datetime) -> datetime:  # ← cls en lugar de self
        # Validar minutos 00 o 30
        if v.minute not in [0, 30]:
            raise ValueError(f"Los minutos deben ser 00 o 30. Recibido: {v.minute:02d}")
        
        # Normalizar segundos a 0
        if v.second != 0 or v.microsecond != 0:
            v = v.replace(second=0, microsecond=0)
        
        return v
    
    @field_validator("audio_ids")
    @classmethod  # ← Añadir esto también
    def validate_audio_ids(cls, v: List[str]) -> List[str]:  # ← cls
        # Validar que no haya duplicados
        if len(set(v)) != len(v):
            raise ValueError("No se permiten IDs duplicados en la lista")
        
        # Validar cantidad exacta
        if len(v) != 30:
            raise ValueError(f"Debe tener exactamente 30 audios. Tiene: {len(v)}")
        
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