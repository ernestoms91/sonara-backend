# models/profile.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class Profile(SQLModel, table=True):
    __tablename__ = "profile"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=50)
    active: bool = Field(default=False)
    hours_ready : bool = Field(default=False)
    minutes_ready : bool = Field(default=False)
    connectors_ready  : bool = Field(default=False)
    language: str = Field(default="Spanish")
    ref_text: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))