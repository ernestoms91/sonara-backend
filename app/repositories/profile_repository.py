# app/repositories/profile_repository.py
from sqlmodel import Session, select
from typing import List, Optional
from app.models.profile_model import Profile
from app.core.logging import get_logger

logger = get_logger(__name__)

class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # LIST PROFILES
    # ============================================
    def list_all(self, skip: int = 0, limit: int = 100) -> List[Profile]:
        """Listar todos los perfiles con paginación"""
        query = select(Profile).order_by(Profile.name.asc()).offset(skip).limit(limit)
        return self.db.exec(query).all()
    
    def list_active(self, skip: int = 0, limit: int = 100) -> List[Profile]:
        """Listar solo perfiles activos"""
        query = select(Profile).where(Profile.active == True).order_by(Profile.name.asc()).offset(skip).limit(limit)
        return self.db.exec(query).all()
    
    # ============================================
    # GET SINGLE PROFILE
    # ============================================
    def get_by_id(self, profile_id: int) -> Optional[Profile]:
        """Obtener perfil por ID"""
        return self.db.get(Profile, profile_id)
    
    def get_by_profile_id(self, profile_id: str) -> Optional[Profile]:
        """Obtener perfil por profile_id (string)"""
        query = select(Profile).where(Profile.profile_id == profile_id)
        return self.db.exec(query).first()
    
    def get_by_name(self, name: str) -> Optional[Profile]:
        """Obtener perfil por nombre exacto"""
        query = select(Profile).where(Profile.name == name)
        return self.db.exec(query).first()
    
    # ============================================
    # CREATE PROFILE
    # ============================================
    def create(self, profile: Profile) -> Profile:
        """Guardar un perfil en la base de datos"""
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Perfil creado: ID={profile.id}, name={profile.name}")
        return profile
    
    # ============================================
    # UPDATE PROFILE
    # ============================================
    def update(self, profile: Profile) -> Profile:
        """Actualizar un perfil existente"""
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Perfil actualizado: ID={profile.id}")
        return profile
    
    # ============================================
    # DELETE PROFILE
    # ============================================
    def delete(self, profile: Profile) -> None:
        """Eliminar un perfil"""
        self.db.delete(profile)
        self.db.commit()
        
        logger.info(f"Perfil eliminado: ID={profile.id}")
    
    def delete_by_id(self, profile_id: int) -> None:
        """Eliminar un perfil por ID"""
        profile = self.get_by_id(profile_id)
        if profile:
            self.delete(profile)
    
    # ============================================
    # COUNT METHODS
    # ============================================
    def count_all(self) -> int:
        """Contar total de perfiles"""
        query = select(Profile)
        return len(self.db.exec(query).all())
    
    def count_active(self) -> int:
        """Contar perfiles activos"""
        query = select(Profile).where(Profile.active == True)
        return len(self.db.exec(query).all())
    
    # ============================================
    # EXISTS METHODS
    # ============================================
    def exists_by_name(self, name: str) -> bool:
        """Verificar si existe un perfil con ese nombre"""
        return self.get_by_name(name) is not None
    
    def exists_by_profile_id(self, profile_id: str) -> bool:
        """Verificar si existe un perfil con ese profile_id"""
        return self.get_by_profile_id(profile_id) is not None