# app/schemas/profile.py
from typing import Optional

from pydantic import BaseModel
from datetime import datetime
from sqlmodel import Field, SQLModel


class ProfileCreate(SQLModel):
    name: str = Field(..., min_length=1, description="Nombre del narrador")
    language: str = Field(default="Spanish", description="Idioma: Auto, Chinese, English, Spanish...")
    ref_text: str = Field(..., description="Transcripción del audio de referencia")
    
class ProfileResponse(BaseModel):
    id: int
    folder_id: str
    name: str
    language: Optional[str] = None
    ref_text: Optional[str] = None
    model_type: Optional[str] = None
    active: bool = True
    connectors_ready: bool = False
    hours_ready: bool = False
    minutes_ready: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True