# app/repositories/boletin_audio_link_repository.py
from sqlmodel import Session
from app.models.boletin_audio_link import BoletinAudioLink
from app.core.logging import get_logger

logger = get_logger(__name__)

class BoletinAudioLinkRepository:
    """Repositorio para la tabla intermedia BoletinAudioLink"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, boletin_id: int, audio_id: int, position: int) -> BoletinAudioLink:
        """Crear un nuevo link entre boletín y audio"""
        logger.debug(f"Creando link: boletin_id={boletin_id}, audio_id={audio_id}, position={position}")
        link = BoletinAudioLink(
            boletin_id=boletin_id,
            audio_id=audio_id,
            position=position
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        logger.debug(f"Link creado: {link}")
        return link