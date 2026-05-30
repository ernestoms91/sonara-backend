# app/repositories/profile_repository.py
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlmodel import paginate 
from sqlmodel import Session, select
from typing import List, Optional
from app.models.profile_model import Profile
from app.core.logging import get_logger
from app.schemas.profile import ProfileCreate

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
    def create(self, profile_data: ProfileCreate, voice_clone_prompt: bytes) -> Profile:
        """Guardar un perfil en la base de datos"""
        profile = Profile(
            name=profile_data.name,
            language=profile_data.language,
            ref_text=profile_data.ref_text,
            model_type=profile_data.model_type,
            folder_id=profile_data.folder_id
            
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    

    def update_active_status(self, profile: Profile, active: bool) -> Profile:
        """Actualizar el estado activo/inactivo del perfil"""
        profile.active = active
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, profile: Profile) -> Profile:
        """Actualizar cualquier campo del perfil"""
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_profiles_paginated(self, page: int = 1, size: int = 50, active_only: bool = False) -> dict:
        """
        Obtiene todos los perfiles paginados.
        """
        statement = select(Profile)
        
        if active_only:
            statement = statement.where(Profile.active == True)
        
        statement = statement.order_by(Profile.name.asc())
        
        params = Params(page=page, size=size)
        result = paginate(self.db, statement, params)
        
        # Convertir los items a diccionario (igual que en audios)
        items = [item.model_dump() for item in result.items]        
        
        return {
            "items": items,
            "total": result.total,
            "page": result.page,
            "size": result.size,
            "pages": result.pages
        }