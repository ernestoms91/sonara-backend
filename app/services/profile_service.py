# app/services/profile_service.py
from typing import Dict, List, Tuple
import uuid
import io
import tempfile
import shutil
from fastapi import HTTPException, status
from fastapi_pagination import Params, paginate
import soundfile as sf
from pathlib import Path
from sqlmodel import Session, select
from app.core.logging import get_logger
from app.helpers.audio_templates import REQUIRED_AUDIO_FILES
from app.models.profile_model import Profile
from app.repositories.profile_repository import ProfileRepository
from app.services.tts_service import TTSService
from app.utils.validators.audio_validator import AudioValidator
from app.core.config import settings

logger = get_logger(__name__)


class ProfileService:
    def __init__(self, db: Session, tts_service: TTSService):
        self.repo = ProfileRepository(db)
        self.db = db
        self.tts_service = tts_service
        self.profiles_base_dir = Path(settings.OUTPUT_DIR) / "profiles"

    def create_profile(
        self,
        name: str,
        ref_text: str,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        language: str = "Spanish"
    ) -> Profile:
        """
        Crea perfil de forma ATÓMICA con folder_id UUID
        """
        AudioValidator.validate(audio_bytes, filename, content_type)

        ext = Path(filename).suffix.lower()
        temp_path = None
        profile_folder = None

        # Generar folder_id antes de crear la carpeta
        folder_id = str(uuid.uuid4())

        try:
            # 1. Crear carpeta con folder_id + nombre
            safe_name = "".join(c for c in name.strip()
                                if c.isalnum() or c in " ._-")
            folder_name = f"{folder_id}"
            profile_folder = self.profiles_base_dir / folder_name
            profile_folder.mkdir(parents=True, exist_ok=True)

            audio_path = profile_folder / f"{name.strip().capitalize()}{ext}"
            prompt_path = profile_folder / f"{name.lower()}.pt"

            # 2. Guardar audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            shutil.copy2(temp_path, audio_path)
            logger.info(f"Audio guardado: {audio_path}")

            # 3. Generar prompt
            self.tts_service.generate_and_save_prompt(
                audio_path=str(audio_path),
                ref_text=ref_text,
                prompt_path=prompt_path
            )

            # 4. Guardar en BD (el id auto-incremento lo pone la BD)
            profile = Profile(
                folder_id=folder_id,
                name=name.strip(),
                language=language,
                ref_text=ref_text.strip(),
                model_type=settings.MODEL_NAME,
                active=False,
                hours_ready=False,
                minutes_ready=False,
                connectors_ready=False
            )

            profile = self.repo.create(profile, None)
            logger.info(
                f"Perfil '{name}' creado con ID: {profile.id}, folder_id: {folder_id}")

            return profile

        except Exception as e:
            logger.error(f"Error creando perfil: {e}")
            if profile_folder and profile_folder.exists():
                shutil.rmtree(profile_folder)
            raise

        finally:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)

    def deactivate_profile(self, profile_id: int) -> Profile:
        """
        Desactivar un perfil existente (solo cambia flag active=False)
        """
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        # Si ya está inactivo
        if not profile.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Profile '{profile.name}' is already deactivated"
            )

        # Actualizar estado
        profile = self.repo.update_active_status(profile, active=False)

        logger.info(
            f"Profile '{profile.name}' (ID={profile_id}) desactivado exitosamente")
        return profile

    def validate_profile_files(self, profile: Profile) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Valida que existan todos los archivos requeridos para un perfil.

        Args:
            profile: Objeto Profile (contiene folder_id)

        Returns:
            (is_valid, missing_files_dict)
        """
        # Construir ruta: OUTPUT_DIR/profiles/{folder_id}/
        profile_dir = self.profiles_base_dir / profile.folder_id
        missing_files = {}

        for category, files in REQUIRED_AUDIO_FILES.items():
            category_dir = profile_dir / category
            missing_in_category = []

            for filename in files:
                file_path = category_dir / filename
                if not file_path.exists():
                    missing_in_category.append(filename)

            if missing_in_category:
                missing_files[category] = missing_in_category

        is_valid = len(missing_files) == 0
        return is_valid, missing_files

    def activate_profile_with_validation(self, profile_id: int) -> Profile:
        """
        Activa un perfil SOLO si todos los archivos requeridos existen.
        """
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )

        if profile.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Profile '{profile.name}' is already active"
            )

        # Validar archivos usando folder_id
        is_valid, missing_files = self.validate_profile_files(profile)

        if not is_valid:
            # Convertir missing_files a string legible
            missing_summary = []
            for category, files in missing_files.items():
                missing_summary.append(f"{category}: {', '.join(files[:5])}" +
                                       (f" and {len(files)-5} more" if len(files) > 5 else ""))

            detail_message = f"Missing required audio files. {'; '.join(missing_summary)}"

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail_message  # Esto es un string
            )

        # Actualizar todos los flags
        profile.active = True
        profile.hours_ready = True
        profile.minutes_ready = True
        profile.connectors_ready = True

        profile = self.repo.update(profile)

        logger.info(
            f"Profile '{profile.name}' (ID={profile_id}, folder_id={profile.folder_id}) "
            f"activado con todos los archivos validados"
        )

        return profile


    def get_profiles_paginated(
        self,
        page: int = 1,
        size: int = 50,
        active_only: bool = False
    ) -> dict:
        """
        Obtiene todos los perfiles paginados.

        Args:
            page: Número de página (default: 1)
            size: Items por página (default: 50, max: 100)
            active_only: Filtrar solo activos (default: False)

        Returns:
            Dict con items, total, page, size, pages
        """
        # Reglas de negocio: límite máximo de 100 items por página
        if size > 100:
            logger.warning(
                f"Tamaño de página {size} excede el límite, limitando a 100")
            size = 100

        # Validar que page sea al menos 1
        if page < 1:
            logger.warning(f"Página {page} inválida, usando página 1")
            page = 1

        logger.info(
            f"Obteniendo perfiles paginados - Página: {page}, Tamaño: {size}, Activos solo: {active_only}")

        result = self.repo.get_profiles_paginated(
            page=page, size=size, active_only=active_only)

        logger.info(
            f"Perfiles obtenidos - Total: {result['total']}, Páginas: {result['pages']}")
        return result


    def delete_profile(self, profile_id: int, force: bool = False) -> dict:
        """
        Elimina un perfil de forma ATÓMICA:
        1. Valida que exista
        2. Valida que no esté activo (o force=True)
        3. Elimina la carpeta física
        4. Elimina el registro de la BD
        
        Args:
            profile_id: ID del perfil a eliminar
            force: Si True, elimina aunque esté activo
            
        Returns:
            dict: Información del perfil eliminado
            
        Raises:
            HTTPException: Si el perfil no existe o está activo (sin force)
        """
        # 1. Obtener el perfil
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        # 2. Validar que no esté activo (a menos que force=True)
        if profile.active and not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete active profile '{profile.name}'. Deactivate it first or use force=true"
            )
        
        # Guardar información para el response
        profile_info = {
            "id": profile.id,
            "name": profile.name,
            "folder_id": profile.folder_id,
            "active": profile.active
        }
        
        # 3. Eliminar carpeta física
        profile_folder = self.profiles_base_dir / profile.folder_id
        folder_deleted = False
        folder_size = 0
        
        if profile_folder.exists():
            try:
                # Calcular tamaño antes de eliminar
                folder_size = sum(f.stat().st_size for f in profile_folder.rglob('*') if f.is_file())
                shutil.rmtree(profile_folder)
                folder_deleted = True
                logger.info(f"Carpeta eliminada: {profile_folder} (tamaño: {folder_size} bytes)")
            except Exception as e:
                logger.error(f"Error eliminando carpeta {profile_folder}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error deleting profile folder: {str(e)}"
                )
        else:
            logger.warning(f"La carpeta del perfil no existe: {profile_folder}")
        
        # 4. Eliminar de la BD
        deleted = self.repo.delete(profile_id)
        if not deleted:
            # Si falla la eliminación en BD pero ya eliminamos la carpeta,
            # intentamos restaurar la carpeta? Mejor loguear y continuar
            logger.error(f"Perfil eliminado de BD pero no se pudo eliminar: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting profile from database"
            )
        
        logger.info(
            f"Perfil '{profile.name}' (ID={profile_id}) eliminado exitosamente. "
            f"Carpeta eliminada: {folder_deleted}, Tamaño: {folder_size} bytes"
        )
        
        return {
            "profile": profile_info,
            "folder_deleted": folder_deleted,
            "folder_size_bytes": folder_size
        }