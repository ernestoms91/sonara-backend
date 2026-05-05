# app/repositories/boletin_repository.py
from datetime import datetime
from time import timezone
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from app.models.boletin_model import Boletin
from app.models.boletin_audio_link import BoletinAudioLink
from app.models.generated_audio_model import GeneratedAudio
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
    
    def get_audio_ids_by_boletin_id(self, boletin_id: int) -> List[str]:
        """
        Retorna la lista de audio_ids en orden del 0 al 29 según la posición
        """
        logger.debug(f"Obteniendo audio_ids del boletín {boletin_id}")
        
        # Query para obtener los enlaces ordenados por posición
        query = select(BoletinAudioLink).where(
            BoletinAudioLink.boletin_id == boletin_id
        ).order_by(BoletinAudioLink.position)
        
        links = self.db.exec(query).all()
        
        # Extraer los audio_id de cada GeneratedAudio relacionado
        audio_ids = [link.audio.audio_id for link in links]
        
        logger.debug(f"Audio_ids encontrados: {len(audio_ids)}")
        return audio_ids
    
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
    
    def update_boletin_audios(self, boletin_id: int, audio_ids: List[str]) -> None:
        """
        Actualiza la relación boletín-audios con la nueva lista.
        Asigna la posición según el índice en la lista.
        """
        logger.info(f"Actualizando audios del boletín {boletin_id}")
        
        # 1. Obtener el boletín
        boletin = self.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")
        
        # 2. Eliminar relaciones existentes
        existing_links = self.db.exec(
            select(BoletinAudioLink).where(BoletinAudioLink.boletin_id == boletin_id)
        ).all()
        
        for link in existing_links:
            self.db.delete(link)
        
        # 3. Crear nuevas relaciones con posiciones
        for position, audio_id in enumerate(audio_ids):
            # Obtener el audio por su audio_id (string) no por id numérico
            audio = self.db.exec(
                select(GeneratedAudio).where(GeneratedAudio.audio_id == audio_id)
            ).first()
            
            if not audio:
                raise ValueError(f"Audio con audio_id {audio_id} no encontrado")
            
            # Crear el enlace con la posición
            link = BoletinAudioLink(
                boletin_id=boletin_id,
                audio_id=audio.id,  # Usar el id numérico del audio
                position=position
            )
            self.db.add(link)
        
        # 4. El updated_at se actualizará automáticamente por el onupdate del modelo
        # Pero hay que hacer un touch al boletín para que se actualice
        boletin.updated_at = datetime.now(timezone.utc)  # Si quieres forzarlo
        self.db.add(boletin)
        
        # 5. Commit de todos los cambios
        self.db.commit()
        
        logger.info(f"Boletín {boletin_id} actualizado con {len(audio_ids)} audios")
    
    def soft_delete(self, boletin_id: int) -> None:
        """Soft delete: desactiva el boletín"""
        logger.info(f"Desactivando boletín {boletin_id}")
        
        boletin = self.db.get(Boletin, boletin_id)
        boletin.active = False
        self.db.add(boletin)
        self.db.commit()
        
        logger.info(f"Boletín {boletin_id} desactivado")

    def activate(self, boletin_id: int) -> None:
        """Activa un boletín"""
        logger.info(f"Activando boletín {boletin_id}")
        
        boletin = self.db.get(Boletin, boletin_id)
        boletin.active = True
        self.db.add(boletin)
        self.db.commit()
        
        logger.info(f"Boletín {boletin_id} activado")