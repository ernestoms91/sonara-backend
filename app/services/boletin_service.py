# app/services/boletin_service.py
from networkx import enumerate_all_cliques
from sqlmodel import Session
from app.repositories.boletin_repository import BoletinRepository
from app.models.boletin_model import Boletin
from typing import List, Optional
from app.core.logging import get_logger
from app.repositories.generated_audio_repository import GeneratedAudioRepository
from app.core.config import settings

logger = get_logger(__name__)

class BoletinService:
    """Servicio para la gestión de Boletines"""
    
    def __init__(self, db: Session):
        self.db = db
        self.boletin_repo = BoletinRepository(db)
        self.audio_repo = GeneratedAudioRepository(db)
    
    def create(
            self, 
            start_time: str, 
            audio_ids: List[str],  # Lista de 30 IDs de audios
        ) -> Boletin:
            """
            Crear un nuevo boletín con una lista de audios asociados.
            
            Args:
                start_time: Horario de inicio del boletín (ej: "06:00")
                audio_ids: Lista de 30 IDs de audios (debe tener exactamente 30)
                
            Returns:
                Boletin: El boletín creado con sus audios asociados
            """
            # 1. Validar cantidad de audios
            if len(audio_ids) != 30:
                raise ValueError(
                    f"Se requieren exactamente 30 audios para un boletín completo. "
                    f"Recibidos: {len(audio_ids)}"
                )
            
            # 2. Validar que todos los audios existen en la BD
            
            for audio_id in audio_ids:
                audio = self.audio_repo.get_by_audio_id(audio_id, active=True)
                if not audio or audio["active"] == False:
                    raise ValueError(f"Audio con ID {audio_id} no encontrado o inactivo")
                
            # 3. Crear cada audio del boletin con la hora exacta
            hour = int(start_time.split(":")[0])
            for index, audio_id in enumerate(audio_ids):
                audio_obj = self.audio_repo.get_by_audio_id_with_relationship(audio_id)
                folder_id = audio_obj.owner_profile.folder_id
                hours_path = f"{settings.OUTPUT_DIR}/{folder_id}/hours/{hour}.mp3"
                mins_path = f"{settings.OUTPUT_DIR}/{folder_id}/mins/{index}.mp3"
                logger.info(f"{hours_path}")
                logger.info(f"{mins_path}")
            
            pass