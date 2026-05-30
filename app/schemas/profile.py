# app/schemas/profile.py
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import Field, SQLModel


class ProfileCreate(SQLModel):
    name: str = Field(..., min_length=1, description="Nombre del narrador")
    language: str = Field(default="Spanish", description="Idioma: Auto, Chinese, English, Spanish...")
    ref_text: str = Field(..., description="Transcripción del audio de referencia")
    
class ProfileResponse(BaseModel):
    id: int
    name: str
    language: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True