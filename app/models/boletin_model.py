# app/models/boletin_model.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone
from app.models.generated_audio_model import GeneratedAudio


class Boletin(SQLModel, table=True):
    __tablename__ = "boletin"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: str = Field(
        regex=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="Hora de inicio en formato HH:MM"
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    
    active: bool = Field(default=True)
    
    # Relación muchos a muchos
    audios: List["GeneratedAudio"] = Relationship(
        back_populates="boletines",
        link_model="BoletinAudioLink"
    )
    
    @property
    def end_time(self) -> str:
        hours, minutes = map(int, self.start_time.split(':'))
        total_minutes = hours * 60 + minutes + 30
        new_hours = (total_minutes // 60) % 24
        new_minutes = total_minutes % 60
        return f"{new_hours:02d}:{new_minutes:02d}"