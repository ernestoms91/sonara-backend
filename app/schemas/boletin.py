# app/schemas/boletin.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
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
    start_time: datetime = Field(..., description="Nueva fecha y hora de inicio (opcional)")
    
    @field_validator("audio_ids")
    @classmethod
    def validate_audio_ids(cls, v: List[str]) -> List[str]:
        """Validar que no haya duplicados"""
        if len(set(v)) != len(v):
            raise ValueError("No se permiten IDs duplicados en la lista")
        return v
    
    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validar minutos 00 o 30 si se envía start_time"""
        if v is not None:
            if v.minute not in [0, 30]:
                raise ValueError(f"Los minutos deben ser 00 o 30. Recibido: {v.minute:02d}")
            if v.second != 0 or v.microsecond != 0:
                v = v.replace(second=0, microsecond=0)
        return v
    
class AudioInfoResponse(BaseModel):
    """Información de un audio dentro de un boletín"""
    id: int = Field(..., description="ID interno del audio")
    audio_id: str = Field(..., description="ID único del audio (formato UUID)")
    text: Optional[str] = Field(None, description="Texto del audio")
    duration: Optional[float] = Field(None, description="Duración en segundos")
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del audio")
    
    class Config:
        from_attributes = True 

class BoletinDetailResponse(BaseModel):
    """Respuesta detallada de un boletín por ID"""
    id: int = Field(..., description="ID del boletín")
    start_time: datetime = Field(..., description="Fecha y hora de inicio")
    created_by: Optional[str] = Field(None, description="Usuario que creó el boletín")
    created_at: datetime = Field(..., description="Fecha de creación del boletín")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    active: bool = Field(..., description="Estado del boletín")
    audio_count: int = Field(..., description="Cantidad de audios asociados")
    audio_ids: List[str] = Field(..., description="IDs de audios en orden")
    audios: List[AudioInfoResponse] = Field(..., description="Información detallada de los audios")
    
    class Config:
        from_attributes = True

class BoletinListItemResponse(BaseModel):
    """Respuesta resumida para lista de boletines"""
    id: int = Field(..., description="ID del boletín")
    start_time: datetime = Field(..., description="Fecha y hora de inicio")
    created_by: Optional[str] = Field(None, description="Usuario que creó el boletín")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    active: bool = Field(..., description="Estado del boletín")
    audio_count: int = Field(..., description="Cantidad de audios asociados")
    audios: Optional[List[AudioInfoResponse]] = Field(None, description="Primeros 5 audios (si se solicita)")
    
    class Config:
        from_attributes = True

class BoletinListResponse(BaseModel):
    """Respuesta paginada de boletines"""
    total: int = Field(..., description="Total de boletines que cumplen los filtros")
    skip: int = Field(..., description="Número de registros saltados")
    limit: int = Field(..., description="Límite de registros por página")
    items: List[BoletinListItemResponse] = Field(..., description="Lista de boletines")
    
    class Config:
        from_attributes = True

class BoletinDateRangeResponse(BaseModel):
    """Respuesta para búsqueda por rango de fechas"""
    count: int = Field(..., description="Cantidad de boletines encontrados")
    items: List[dict] = Field(..., description="Lista resumida de boletines")
    
    class Config:
        from_attributes = True

class BoletinSoftDeleteResponse(BaseModel):
    """Respuesta después de soft delete o activación"""
    boletin_id: int = Field(..., description="ID del boletín afectado")
    start_time: datetime = Field(..., description="Fecha y hora del boletín")
    message: str = Field(..., description="Mensaje de confirmación")
    
    class Config:
        from_attributes = True