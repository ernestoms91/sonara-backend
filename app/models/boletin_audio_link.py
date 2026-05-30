# app/models/boletin_audio_link.py
from sqlmodel import SQLModel, Field


class BoletinAudioLink(SQLModel, table=True):
    __tablename__ = "boletin_audio_link"
    
    boletin_id: int = Field(foreign_key="boletin.id", primary_key=True)
    audio_id: int = Field(foreign_key="generated_audio.id", primary_key=True)
    position: int = Field(default=0, description="Orden dentro del boletín")