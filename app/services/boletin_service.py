# app/services/boletin_service.py
from datetime import datetime
from pathlib import Path
import re
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload, aliased
from typing import List, Optional, Dict, Any
from app.helpers.audio_helpers import AudioMerger
from app.repositories.boletin_repository import BoletinRepository
from app.models.boletin_model import Boletin
from app.core.logging import get_logger
from app.repositories.generated_audio_repository import GeneratedAudioRepository
from app.core.config import settings
from app.models.profile_model import Profile

logger = get_logger(__name__)


class BoletinService:
    """Servicio para la gestión de Boletines"""

    def __init__(self, db: Session):
        self.db = db
        self.boletin_repo = BoletinRepository(db)
        self.audio_repo = GeneratedAudioRepository(db)

    def _extract_title(self, text: str) -> str:
        """Extrae el título de un texto (método auxiliar - sin try/except)"""
        if not text:
            return "Boletín"

        clean = text.strip()
        match = re.search(r"(.+?[\.\!\?])(?:\s|$)", clean)
        if match:
            return match.group(1).strip()

        return clean.splitlines()[0].strip()[:200]

    # ==========================================
    # 📖 MÉTODOS DE SOLO LECTURA - SIN try/except
    # ==========================================

    def get_all(
        self,
        page: int = 1,
        size: int = 50,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Obtiene todos los boletines paginados con sus audio_ids en orden.
        """
        logger.info(f"Obteniendo boletines: page={page}, size={size}, active_only={active_only}")
        
        return self.boletin_repo.get_all_paginated(
            page=page,
            size=size,
            active_only=active_only
        )

    def get_by_id(self, boletin_id: int) -> Dict[str, Any]:
        """
        Obtener un boletín por su ID con toda la información completa de los audios
        """
        logger.info(f"Obteniendo boletín con ID: {boletin_id}")
        
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")
        
        audio_ids = self.boletin_repo.get_audio_ids_by_boletin_id(boletin_id)
        
        return {
            "id": boletin.id,
            "start_time": boletin.start_time,
            "created_by": boletin.created_by,
            "created_at": boletin.created_at,
            "updated_at": boletin.updated_at,
            "active": boletin.active,
            "audio_count": len(boletin.audios),
            "audio_ids": audio_ids,
            "audios": [
                {
                    "id": audio.id,
                    "audio_id": audio.audio_id,
                    "title": audio.title,
                    "text": audio.text,
                    "duration": audio.duration,
                    "character_count": audio.character_count,
                    "created_at": audio.created_at,
                    "profile_id": audio.profile_id,
                    "secondary_profile_id": audio.secondary_profile_id,
                    "waveform": audio.waveform,
                    "active": audio.active
                }
                for audio in boletin.audios
            ]
        }

    # ==========================================
    # ✏️ MÉTODOS QUE MODIFICAN DATOS - CON try/except
    # ==========================================

    def create(
        self,
        start_time: datetime,
        audio_ids: List[str],
        created_by: str
    ) -> Boletin:
        """
        Crear un nuevo boletín con una lista de audios asociados.
        UNIDAD DE TRABAJO COMPLETA - CON try/except y commit/rollback.
        """
        # 1. Validaciones (pueden lanzar excepciones)
        if len(audio_ids) != 30:
            raise ValueError(
                f"Se requieren exactamente 30 audios para un boletín completo. "
                f"Recibidos: {len(audio_ids)}"
            )

        for audio_id in audio_ids:
            audio = self.audio_repo.get_by_audio_id(audio_id, active=True)
            if not audio or audio["active"] == False:
                raise ValueError(
                    f"Audio con ID {audio_id} no encontrado o inactivo")

            duracion_audio = audio.get("duration", 0)
            if duracion_audio < 40:
                raise ValueError(
                    f"Audio {audio.get('id')} tiene duración insuficiente: {duracion_audio:.2f}s. "
                    f"Mínimo requerido: 40s para poder ajustarlo a 60s sin distorsión"
                )

        try:
            # 2. Crear el boletín
            boletin = self.boletin_repo.create(
                start_time=start_time, created_by=created_by)

            # 3. Procesar archivos de audio
            self._process_audio_files(start_time, audio_ids, boletin)

            # 4. Guardar relaciones
            self.boletin_repo.update_boletin_audios(boletin.id, audio_ids)

            # 5. COMMIT - Todo funciona
            self.db.commit()
            logger.info(f"Boletín {boletin.id} creado exitosamente con {len(audio_ids)} audios")

            # 6. Retornar el boletín con los audios cargados
            return self.boletin_repo.get_by_id(boletin.id)

        except Exception as e:
            # 7. ROLLBACK - Algo falló
            self.db.rollback()
            logger.error(f"Error creando boletín: {str(e)}")
            raise

    def update(
        self,
        boletin_id: int,
        new_audio_ids: List[str],
    ) -> Boletin:
        """
        Actualiza un boletín existente con nuevos audios.
        UNIDAD DE TRABAJO COMPLETA - CON try/except y commit/rollback.
        """
        # 1. Validaciones (fuera de la transacción)
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        if not boletin.active:
            raise ValueError(f"Boletín {boletin_id} no está activo")

        if len(new_audio_ids) != 30:
            raise ValueError(
                f"Se requieren exactamente 30 audios para un boletín completo. "
                f"Recibidos: {len(new_audio_ids)}"
            )

        current_audio_ids = self.boletin_repo.get_audio_ids_by_boletin_id(boletin_id)

        for audio_id in new_audio_ids:
            audio = self.audio_repo.get_by_audio_id(audio_id, active=True)
            if not audio or audio["active"] == False:
                raise ValueError(f"Audio con ID {audio_id} no encontrado o inactivo")

        try:
            # 2. Procesar actualización de archivos
            self._process_update_audio_files(boletin, new_audio_ids, current_audio_ids)

            # 3. Actualizar relación en BD
            self.boletin_repo.update_boletin_audios(boletin_id, new_audio_ids)

            # 4. COMMIT - Todo funciona
            self.db.commit()
            logger.info(f"Boletín {boletin_id} actualizado correctamente")

            # 5. Retornar el boletín actualizado
            return self.boletin_repo.get_by_id(boletin_id)

        except Exception as e:
            # 6. ROLLBACK - Algo falló
            self.db.rollback()
            logger.error(f"Error actualizando boletín: {str(e)}")
            raise

    def soft_delete(self, boletin_id: int) -> dict:
        """
        Soft delete: desactiva un boletín.
        UNIDAD DE TRABAJO COMPLETA - CON try/except y commit/rollback.
        """
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        if not boletin.active:
            raise ValueError(f"Boletín {boletin_id} ya está desactivado")

        try:
            self.boletin_repo.soft_delete(boletin_id)
            self.db.commit()
            logger.info(f"Boletín {boletin_id} desactivado")

            return {
                "boletin_id": boletin_id,
                "start_time": boletin.start_time,
                "message": "Boletín desactivado correctamente"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error desactivando boletín: {str(e)}")
            raise

    def activate_boletin(self, boletin_id: int) -> dict:
        """
        Activa un boletín.
        UNIDAD DE TRABAJO COMPLETA - CON try/except y commit/rollback.
        """
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        if boletin.active:
            raise ValueError(f"Boletín {boletin_id} ya está activo")

        try:
            self.boletin_repo.activate(boletin_id)
            self.db.commit()
            logger.info(f"Boletín {boletin_id} activado")

            return {
                "boletin_id": boletin_id,
                "start_time": boletin.start_time,
                "message": "Boletín activado correctamente"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error activando boletín: {str(e)}")
            raise

    # ==========================================
    # 🔧 MÉTODOS PRIVADOS - SIN try/except
    # ==========================================

    def _process_audio_files(self, start_time: datetime, audio_ids: List[str], boletin: Boletin):
        """
        Procesa y genera los archivos de audio.
        SIN try/except - las excepciones suben al método padre.
        """
        # Extraer fecha y hora
        bol_date = start_time.strftime("%Y-%m-%d")
        hour = start_time.hour
        minute = start_time.minute

        # Determinar AM/PM para la carpeta
        if hour == 0:
            am_pm = "AM"
            hour_display = "12"
        elif hour == 12:
            am_pm = "PM"
            hour_display = "12"
        elif hour > 12:
            am_pm = "PM"
            hour_display = f"{hour - 12}"
        else:
            am_pm = "AM"
            hour_display = f"{hour}"

        folder_name = f"{hour_display}:{minute:02d} {am_pm}"

        # Crear directorio base si no existe
        base_boletin_dir = Path(settings.OUTPUT_DIR) / "boletines" / bol_date / folder_name
        temp_dir = base_boletin_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Procesar cada audio del boletín
        for index, audio_id in enumerate(audio_ids):
            audio_obj = self.audio_repo.get_by_audio_id_with_relationship(audio_id)
            folder_id = audio_obj.owner_profile.folder_id

            conector_rreloj = Path(settings.OUTPUT_DIR) / f"profiles/{folder_id}/Connectors/rreloj.mp3"

            # Determinar el archivo de hora correcto
            if hour == 0:
                if minute == 0 and index == 0:
                    hour_filename = "12 AM"
                    usar_minutos = False
                else:
                    hour_filename = "12"
                    usar_minutos = True
            elif hour == 12:
                if minute == 0 and index == 0:
                    hour_filename = "12 PM"
                    usar_minutos = False
                else:
                    hour_filename = "12"
                    usar_minutos = True
            elif hour > 12:
                hour_filename = f"{hour - 12}"
                usar_minutos = True
            else:
                hour_filename = f"{hour}"
                usar_minutos = True

            hours_path = Path(settings.OUTPUT_DIR) / f"profiles/{folder_id}/Hours/{hour_filename}.mp3"
            audio_path = Path(settings.OUTPUT_DIR) / f"generated/{audio_id}.wav"

            minuto_real = minute + index

            if hour == 0:
                archivo_am_pm = "AM"
                archivo_hour = "12"
            elif hour == 12:
                archivo_am_pm = "PM"
                archivo_hour = "12"
            elif hour > 12:
                archivo_am_pm = "PM"
                archivo_hour = f"{hour - 12}"
            else:
                archivo_am_pm = "AM"
                archivo_hour = f"{hour}"

            output_filename = f"{archivo_hour}:{minuto_real:02d} {archivo_am_pm}.mp3"
            output_path = temp_dir / output_filename
            final_audio_output_path = base_boletin_dir / output_filename

            missing_files = []
            for file_path in [conector_rreloj, hours_path, audio_path]:
                if not Path(file_path).exists():
                    missing_files.append(str(file_path))

            if usar_minutos:
                mins_path = Path(settings.OUTPUT_DIR) / f"profiles/{folder_id}/Minutes/{minute + index}.mp3"
                if not mins_path.exists():
                    missing_files.append(str(mins_path))
                    logger.warning(f"Faltan archivos para minuto {index}: {missing_files}")
                    raise FileNotFoundError(f"Archivos faltantes para el minuto {index}: {missing_files}")

                logger.info(f"Minuto {index}: usando hours + minutes ({hour_filename} + {minute + index})")
                time_path = AudioMerger.merge_audio_files(
                    audio_paths=[str(hours_path), str(mins_path)],
                    output_path=str(output_path),
                    output_format="mp3",
                    crossfade_ms=50,
                    silence_thresh=-50,
                )
            else:
                time_path = hours_path
                logger.info(f"12:00 {'AM' if hour == 0 else 'PM'} en punto (minuto {index}): usando solo archivo de hora")

            if missing_files:
                logger.warning(f"Faltan archivos para minuto {index}: {missing_files}")
                raise FileNotFoundError(f"Archivos faltantes para el minuto {index}: {missing_files}")

            duration_time_path = AudioMerger.get_duration_seconds(time_path)
            duration_conector_rreloj = AudioMerger.get_duration(str(conector_rreloj))
            remaining_seconds = 60.0 - duration_time_path - duration_conector_rreloj

            title = self._extract_title(audio_obj.text)

            output_audios_path = temp_dir / f"{audio_id}.mp3"
            info_path = AudioMerger.adjust_duration(
                input_path=str(audio_path),
                output_path=str(output_audios_path),
                target_seconds=remaining_seconds,
                output_format="mp3",
                tags={"title": title},
            )

            final_audio = AudioMerger.concatenate_audio_files(
                audio_paths=[str(time_path), str(info_path), str(conector_rreloj)],
                output_path=str(final_audio_output_path),
                output_format="mp3",
                crossfade_ms=0,
                tags={"title": title},
            )

            duracion_final = AudioMerger.get_duration_seconds(final_audio)
            logger.info(f"Archivo de audio {index}: {output_filename} - {duracion_final:.2f}s")

    def _process_update_audio_files(
        self,
        boletin: Boletin,
        new_audio_ids: List[str],
        current_audio_ids: List[str]
    ):
        """
        Procesa la actualización de archivos de audio.
        SIN try/except - las excepciones suben al método padre.
        """
        bol_date = boletin.bol_date
        start_time = boletin.start_time
        hour = int(start_time.split(":")[0])
        hour_str = start_time.replace(":", "-")

        for index, new_audio_id in enumerate(new_audio_ids):
            if current_audio_ids[index] == new_audio_id:
                logger.info(f"Minuto {index}: sin cambios, manteniendo audio existente")
                continue

            logger.info(f"Minuto {index}: actualizando de {current_audio_ids[index] if index < len(current_audio_ids) else 'None'} a {new_audio_id}")

            audio_obj = self.audio_repo.get_by_audio_id_with_relationship(new_audio_id)
            folder_id = audio_obj.owner_profile.folder_id

            conector1 = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/conec/Rreloj.m4a"
            hours_path = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/hours/{hour}.m4a"
            mins_path = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/min/{index}.m4a"
            conector2 = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/conec/Minutos.m4a"
            audio_path = f"{settings.OUTPUT_DIR}/generated/{new_audio_id}.wav"

            output_filename = f"{index:02d}.mp3"
            output_path = f"{settings.OUTPUT_DIR}/boletines/{bol_date}/{hour_str}/temp/{output_filename}"
            final_audio_output_path = f"{settings.OUTPUT_DIR}/boletines/{bol_date}/{hour_str}/{output_filename}"

            missing_files = []
            for file_path in [conector1, hours_path, mins_path, conector2, audio_path]:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            if missing_files:
                logger.warning(f"Faltan archivos para minuto {index}: {missing_files}")
                raise FileNotFoundError(f"Archivos faltantes para el minuto {index}: {missing_files}")

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            time_path = AudioMerger.merge_audio_files(
                audio_paths=[conector1, hours_path, mins_path, conector2],
                output_path=output_path,
                output_format="mp3",
                crossfade_ms=0,
            )

            duration_time_path = AudioMerger.get_duration_seconds(time_path)
            remaining_seconds = 60.0 - duration_time_path

            title = self._extract_title(audio_obj.text)

            if remaining_seconds <= 0.0:
                logger.warning(f"El bloque de tiempo para minuto {index} dura {duration_time_path:.2f}s y no deja espacio para el audio adicional.")

                if duration_time_path > 60.0:
                    time_path = AudioMerger.adjust_duration(
                        input_path=time_path,
                        output_path=output_path,
                        target_seconds=60.0,
                        output_format="mp3",
                        tags={"title": title},
                    )

                final_audio = AudioMerger.merge_audio_files(
                    audio_paths=[time_path],
                    output_path=final_audio_output_path,
                    output_format="mp3",
                    tags={"title": title},
                )
                final_audio = AudioMerger.enforce_duration(
                    audio_path=final_audio,
                    output_path=final_audio_output_path,
                    target_seconds=60.0,
                    output_format="mp3",
                    tags={"title": title},
                )
            else:
                output_audios_path = f"{settings.OUTPUT_DIR}/boletines/{bol_date}/{hour_str}/temp/{new_audio_id}.mp3"
                info_path = AudioMerger.adjust_duration(
                    input_path=audio_path,
                    output_path=output_audios_path,
                    target_seconds=remaining_seconds,
                    output_format="mp3",
                    tags={"title": title},
                )

                final_audio = AudioMerger.concatenate_audio_files(
                    audio_paths=[time_path, info_path],
                    output_path=final_audio_output_path,
                    output_format="mp3",
                    crossfade_ms=0,
                    tags={"title": title},
                )
                final_audio = AudioMerger.enforce_duration(
                    audio_path=final_audio,
                    output_path=final_audio_output_path,
                    target_seconds=60.0,
                    output_format="mp3",
                    tags={"title": title},
                )

            duracion_final = AudioMerger.get_duration_seconds(final_audio)
            logger.info(f"Minuto {index} actualizado: {duracion_final:.2f}s")