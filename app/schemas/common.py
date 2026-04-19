# schemas/common.py
from typing import Generic, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")

class CommonResponse(BaseModel, Generic[T]):
    """Define la estructura de TODAS las respuestas de la API"""
    ok: bool
    message: str
    data: T | None = None
    timestamp: datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def success(cls, message: str, data: T | None = None):
        return cls(ok=True, message=message, data=data)
    
    @classmethod
    def fail(cls, message: str, data: T | None = None):
        return cls(ok=False, message=message, data=data)