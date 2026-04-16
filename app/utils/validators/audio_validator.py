# app/utils/validators/audio_validator.py
from pathlib import Path

class AudioValidator:
    MAX_SIZE = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/flac", "audio/mp4", "audio/ogg"}
    
    @classmethod
    def validate(cls, audio_bytes: bytes, filename: str, content_type: str):
        if not audio_bytes:
            raise ValueError("El archivo de audio está vacío")
        
        if len(audio_bytes) > cls.MAX_SIZE:
            raise ValueError(f"El audio excede {cls.MAX_SIZE // (1024*1024)}MB")
        
        ext = Path(filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(f"Formato no soportado. Use: {', '.join(cls.ALLOWED_EXTENSIONS)}")
        
        if content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Tipo MIME no soportado: {content_type}")
