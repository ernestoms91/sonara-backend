# models/profile.py
import uuid
from sqlmodel import SQLModel, Field


class Profile(SQLModel, table=True):
    __tablename__ = "profile"
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=50)
    active: bool = Field(default=False)
    profile_id: str = Field(min_length=1, max_length=50)
    

class ProfileCreate(SQLModel):
    name: str = Field(..., min_length=1, description="Nombre del narrador")
    language: str = Field(default="Spanish", description="Idioma: Auto, Chinese, English, Spanish...")
    ref_text: str= Field(..., description="Transcripción del audio de referencia")
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID único del perfil")