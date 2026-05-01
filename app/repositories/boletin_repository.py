# app/repositories/boletin_repository.py
from sqlmodel import Session
from typing import Optional
from app.models.boletin_model import Boletin
from app.core.logging import get_logger

logger = get_logger(__name__)

class BoletinRepository:
    """Repositorio para operaciones CRUD de Boletines"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, boletin_id: int) -> Optional[Boletin]:
        """Obtener boletín por ID con sus audios incluidos y ordenados"""
        logger.debug(f"Buscando boletín con ID: {boletin_id}")
        
        # Query con selectinload para traer los audios
        query = select(Boletin).where(
            Boletin.id == boletin_id
        ).options(
            selectinload(Boletin.audios)
        )
        
        boletin = self.db.exec(query).first()
        
        if boletin:
            # Ordenar los audios por la posición en la tabla intermedia
            boletin.audios.sort(
                key=lambda audio: self.db.exec(
                    select(BoletinAudioLink.position).where(
                        BoletinAudioLink.boletin_id == boletin_id,
                        BoletinAudioLink.audio_id == audio.id
                    )
                ).first() or 0
            )
            logger.debug(f"Boletín encontrado con {len(boletin.audios)} audios")
        
        return boletin
    
    def create(self, start_time: str, active: bool = True) -> Boletin:
        """Crear un nuevo boletín"""
        logger.info(f"Creando boletín con start_time: {start_time}, active: {active}")
        boletin = Boletin(
            start_time=start_time,
            active=active
        )
        self.db.add(boletin)
        self.db.commit()
        self.db.refresh(boletin)
        logger.info(f"Boletín creado con ID: {boletin.id}")
        return boletin