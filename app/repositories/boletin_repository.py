# app/repositories/boletin_repository.py
from datetime import datetime, timezone
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
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
        """
        Obtener boletín por ID con sus audios incluidos y ordenados
        """
        logger.debug(f"Buscando boletín con ID: {boletin_id}")
        
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
        
        statement = select(GeneratedAudio.audio_id).join(
            BoletinAudioLink,
            GeneratedAudio.id == BoletinAudioLink.audio_id
        ).where(
            BoletinAudioLink.boletin_id == boletin_id
        ).order_by(BoletinAudioLink.position)
        
        audio_ids = self.db.exec(statement).all()
        
        logger.debug(f"Audio_ids encontrados: {len(audio_ids)}")
        return audio_ids
    
    def get_all_paginated(
        self,
        page: int = 1,
        size: int = 50,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Obtiene todos los boletines paginados con sus audio_ids en orden
        
        Args:
            page: Número de página (empieza en 1)
            size: Cantidad de items por página (máx 100)
            active_only: Si solo se retornan boletines activos
        
        Returns:
            Dict con items, total, page, size, pages
        """
        logger.debug(f"Obteniendo boletines paginados: page={page}, size={size}, active_only={active_only}")
        
        # ✅ Validar y normalizar parámetros
        page = max(1, page)  # page mínimo 1
        size = max(1, min(size, 100))  # size entre 1 y 100
        
        # Construir query base
        query = select(Boletin)
        
        if active_only:
            query = query.where(Boletin.active == True)
        
        # Ordenar por fecha de creación descendente
        query = query.order_by(Boletin.created_at.desc())
        
        # Calcular offset
        offset = (page - 1) * size
        
        # Ejecutar query con paginación
        boletines = self.db.exec(query.offset(offset).limit(size)).all()
        
        # Obtener total de registros
        count_query = select(func.count()).select_from(Boletin)
        if active_only:
            count_query = count_query.where(Boletin.active == True)
        total = self.db.exec(count_query).first() or 0
        
        # Procesar cada boletín para obtener sus audio_ids
        items = []
        for boletin in boletines:
            audio_ids = self.get_audio_ids_by_boletin_id(boletin.id)
            
            items.append({
                "id": boletin.id,
                "start_time": boletin.start_time,
                "created_by": boletin.created_by,
                "created_at": boletin.created_at,
                "updated_at": boletin.updated_at,
                "active": boletin.active,
                "audio_count": len(audio_ids),
                "audio_ids": audio_ids
            })
        
        # ✅ Calcular páginas de forma segura
        pages = (total + size - 1) // size if total > 0 else 0
        
        logger.debug(f"Boletines encontrados: {len(items)} de {total} totales, páginas: {pages}")
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    
    def create(self, start_time: str, created_by: str, active: bool = True) -> Boletin:
        """
        Crear un nuevo boletín (SIN commit - lo maneja el servicio)
        """
        logger.info(f"Creando boletín con start_time: {start_time}, active: {active}")
        boletin = Boletin(
            start_time=start_time,
            active=active,
            created_by=created_by
        )
        self.db.add(boletin)
        self.db.flush()  # Obtener ID sin commit
        self.db.refresh(boletin)
        logger.info(f"Boletín creado con ID: {boletin.id}")
        return boletin
    
    def update_boletin_audios(self, boletin_id: int, audio_ids: List[str]) -> None:
        """
        Actualiza la relación boletín-audios con la nueva lista.
        Asigna la posición según el índice en la lista.
        (SIN commit - lo maneja el servicio)
        """
        logger.info(f"Actualizando audios del boletín {boletin_id}")
        
        # 1. Eliminar relaciones existentes
        existing_links = self.db.exec(
            select(BoletinAudioLink).where(BoletinAudioLink.boletin_id == boletin_id)
        ).all()
        
        for link in existing_links:
            self.db.delete(link)
        
        # 2. Crear nuevas relaciones con posiciones
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
        
        # 3. Actualizar timestamp
        boletin = self.get_by_id(boletin_id)
        if boletin:
            boletin.updated_at = datetime.now(timezone.utc)
            self.db.add(boletin)
        
        logger.info(f"Boletín {boletin_id} actualizado con {len(audio_ids)} audios")
    
    def soft_delete(self, boletin_id: int) -> None:
        """
        Soft delete: desactiva el boletín
        (SIN commit - lo maneja el servicio)
        """
        logger.info(f"Desactivando boletín {boletin_id}")
        
        boletin = self.db.get(Boletin, boletin_id)
        if boletin:
            boletin.active = False
            self.db.add(boletin)
            logger.info(f"Boletín {boletin_id} desactivado")
        else:
            logger.warning(f"Boletín {boletin_id} no encontrado")

    def activate(self, boletin_id: int) -> None:
        """
        Activa un boletín
        (SIN commit - lo maneja el servicio)
        """
        logger.info(f"Activando boletín {boletin_id}")
        
        boletin = self.db.get(Boletin, boletin_id)
        if boletin:
            boletin.active = True
            self.db.add(boletin)
            logger.info(f"Boletín {boletin_id} activado")
        else:
            logger.warning(f"Boletín {boletin_id} no encontrado")