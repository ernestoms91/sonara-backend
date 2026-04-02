# app/services/profile_service.py
from sqlmodel import Session
from app.repositories.profile_repository import ProfileRepository
from app.models.profile_model import Profile


class ProfileService:
    def __init__(self, db: Session):
        self.repo = ProfileRepository(db)
    
    def create_profile(self, name: str, profile_id: str, active: bool = False) -> Profile:
        """Crear un nuevo perfil con validaciones de negocio"""
        # Validaciones
        if self.repo.exists_by_name(name):
            raise ValueError(f"Ya existe un perfil con el nombre: {name}")
        
        if self.repo.exists_by_profile_id(profile_id):
            raise ValueError(f"Ya existe un perfil con profile_id: {profile_id}")
        
        # Crear el perfil
        profile = Profile(
            name=name,
            profile_id=profile_id,
            active=active
        )
        
        return self.repo.create(profile)
    
    def update_profile(self, profile_id: int, **kwargs) -> Profile:
        """Actualizar un perfil con validaciones"""
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Perfil no encontrado: {profile_id}")
        
        # Validar si el nuevo nombre ya existe (si se está cambiando)
        new_name = kwargs.get("name")
        if new_name and new_name != profile.name:
            if self.repo.exists_by_name(new_name):
                raise ValueError(f"Ya existe un perfil con el nombre: {new_name}")
            profile.name = new_name
        
        # Validar si el nuevo profile_id ya existe
        new_profile_id = kwargs.get("profile_id")
        if new_profile_id and new_profile_id != profile.profile_id:
            if self.repo.exists_by_profile_id(new_profile_id):
                raise ValueError(f"Ya existe un perfil con profile_id: {new_profile_id}")
            profile.profile_id = new_profile_id
        
        # Actualizar otros campos
        if "active" in kwargs:
            profile.active = kwargs["active"]
        
        return self.repo.update(profile)
    
    def delete_profile(self, profile_id: int) -> None:
        """Eliminar un perfil"""
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Perfil no encontrado: {profile_id}")
        
        # Aquí puedes agregar validaciones adicionales
        # Por ejemplo: verificar si el perfil tiene dependencias
        
        self.repo.delete(profile)
    
    def get_profile(self, profile_id: int) -> Profile:
        """Obtener un perfil"""
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Perfil no encontrado: {profile_id}")
        return profile
    
    def list_profiles(self, active_only: bool = False, skip: int = 0, limit: int = 100):
        """Listar perfiles"""
        if active_only:
            return self.repo.list_active(skip=skip, limit=limit)
        return self.repo.list_all(skip=skip, limit=limit)