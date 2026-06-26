# app/schemas/audio.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Dict, Optional
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
        
        #  1. Buscar todos los marcadores [P1], [P2], [P3], [P4]
        markers = re.findall(r'\[P([1-4])\]', v, re.IGNORECASE)
        
        #  2. Validar que existan los 4 marcadores
        required_markers = {'1', '2', '3', '4'}
        found_markers = set(markers)
        
        if found_markers != required_markers:
            missing = required_markers - found_markers
            raise ValueError(
                f"El texto debe contener los 4 marcadores: [P1], [P2], [P3], [P4]. "
                f"Faltan: {', '.join(f'[P{m}]' for m in sorted(missing, key=int))}"
            )
        
        # 3. Validar cada párrafo individualmente
        for i in range(1, 5):  # 1, 2, 3, 4
            # Buscar el contenido después de [P{i}] hasta el siguiente marcador o final
            if i < 4:
                # Para P1, P2, P3: buscar hasta el siguiente marcador
                pattern = rf'\[P{i}\](.*?)(?=\[P{i+1}\])'
            else:
                # Para P4: buscar hasta el final
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
        
        # 4. Validar que no haya marcadores adicionales
        extra_markers = re.findall(r'\[P([5-9]|0\d+)\]', v, re.IGNORECASE)
        if extra_markers:
            raise ValueError(
                f"El texto contiene marcadores adicionales no permitidos: "
                f"{', '.join(f'[P{m}]' for m in extra_markers)}. "
                f"Solo se permiten [P1], [P2], [P3], [P4]"
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
    """Respuesta para un audio generado normalmente"""
    id: int
    audio_id: UUID
    profile_id: int
    secondary_profile_id: Optional[int] = None
    text: str
    title: Optional[str] = None
    duration: float
    waveform: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    active: bool = True
    character_count: int = 0
    profile_name: Optional[str] = None
    secondary_profile_name: Optional[str] = None
    audio_url: Optional[str] = None
    waveform_url: Optional[str] = None


class DuetAudioDataResponse(BaseModel):
    """Respuesta para un audio dueto generado"""
    id: int
    audio_id: UUID
    profile_id: int  # Perfil A
    secondary_profile_id: Optional[int] = None  # Perfil B
    text: str
    title: Optional[str] = None
    duration: float
    waveform: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    active: bool = True
    character_count: int = 0   
    profile_a: str  # Nombre del perfil A
    profile_b: str  # Nombre del perfil B
    profile_name: Optional[str] = None  # Para consistencia con AudioListItemResponse
    secondary_profile_name: Optional[str] = None
    audio_url: Optional[str] = None
    waveform_url: Optional[str] = None


class DurationChangedResponse(BaseModel):
    """Respuesta para un audio modificado en duración"""
    audio_id: UUID
    original_audio_id: UUID
    original_duration: float
    new_duration: float
    filename: str
    created_at: Optional[datetime] = None


class AudioListItemResponse(BaseModel):
    """Respuesta para items en lista paginada"""
    id: int
    audio_id: UUID
    title: Optional[str] = None
    text: Optional[str] = None
    duration: float
    character_count: int = 0
    created_at: datetime
    profile_id: int
    profile_name: str
    secondary_profile_id: Optional[int] = None  # ✅ NUEVO
    secondary_profile_name: Optional[str] = None  # ✅ NUEVO
    waveform: Optional[str] = None
    waveform_url: Optional[str] = None
    audio_url: Optional[str] = None


class AudioForBoletinRequest(BaseModel):
    """Request para generar audios de un boletín completo (un audio por minuto)"""
    profile_a_id: int = Field(..., description="ID del perfil A (voz para P1)")
    profile_b_id: int = Field(..., description="ID del perfil B (voz para P2)")
    minutos: Dict[str, str] = Field(..., description="Diccionario con los minutos: '1': '[P1]...[P2]...'")