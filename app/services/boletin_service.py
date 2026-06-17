# app/services/boletin_service.py
from datetime import datetime
from pathlib import Path
import re
from xml.etree.ElementTree import tostring
from networkx import enumerate_all_cliques
from sqlmodel import Session
from app.helpers.audio_helpers import AudioMerger
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

    def _extract_title(self, text: str) -> str:
        if not text:
            return "Boletín"

        clean = text.strip()
        match = re.search(r"(.+?[\.\!\?])(?:\s|$)", clean)
        if match:
            return match.group(1).strip()

        return clean.splitlines()[0].strip()[:200]

    def create(
        self,
        start_time: datetime,
        audio_ids: List[str],
        created_by: str
    ) -> Boletin:
        """
        Crear un nuevo boletín con una lista de audios asociados.

        Args:
            start_time: Fecha y hora de inicio (datetime, minutos deben ser 00 o 30)
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

        # 2. Validar que todos los audios existen y tienen duración suficiente
        for audio_id in audio_ids:
            audio = self.audio_repo.get_by_audio_id(audio_id, active=True)
            if not audio or audio["active"] == False:
                raise ValueError(
                    f"Audio con ID {audio_id} no encontrado o inactivo")

            # Validar duración mínima
            duracion_audio = audio.get("duration", 0)
            if duracion_audio < 40:
                raise ValueError(
                    f"Audio {audio.get('id')} tiene duración insuficiente: {duracion_audio:.2f}s. "
                    f"Mínimo requerido: 40s para poder ajustarlo a 60s sin distorsión"
                )

        # 3. Crear el boletín en la BD
        boletin = self.boletin_repo.create(
            start_time=start_time, created_by=created_by)

        # 4. Extraer fecha y hora del datetime
        bol_date = start_time.strftime("%Y-%m-%d")  # Formato: YYYY-MM-DD
        hour = start_time.hour                       # Hora en 24h (0-23)
        minute = start_time.minute                   # Minuto (0 o 30)

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

        # Nombre de carpeta con formato "HH:MM AM/PM"
        folder_name = f"{hour_display}:{minute:02d} {am_pm}"

        # 5. Crear directorio base si no existe
        base_boletin_dir = Path(settings.OUTPUT_DIR) / \
            "boletines" / bol_date / folder_name
        temp_dir = base_boletin_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 6. Procesar cada audio del boletín
        for index, audio_id in enumerate(audio_ids):
            audio_obj = self.audio_repo.get_by_audio_id_with_relationship(
                audio_id)
            folder_id = audio_obj.owner_profile.folder_id

            # Rutas de archivos fuente
            conector_rreloj = Path(settings.OUTPUT_DIR) / \
                f"profiles/{folder_id}/Connectors/rreloj.mp3"

            # Determinar el archivo de hora correcto (manejar AM/PM)
            if hour == 0:
                # 12:00 AM en punto usa "12 AM", 12:01-12:59 usa "12"
                if minute == 0 and index == 0:
                    hour_filename = "12 AM"
                    usar_minutos = False
                else:
                    hour_filename = "12"
                    usar_minutos = True
            elif hour == 12:
                # 12:00 PM en punto usa "12 PM", 12:01-12:59 usa "12"
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

            hours_path = Path(settings.OUTPUT_DIR) / \
                f"profiles/{folder_id}/Hours/{hour_filename}.mp3"
            audio_path = Path(settings.OUTPUT_DIR) / \
                f"generated/{audio_id}.wav"

            # Calcular minuto real para el nombre del archivo
            minuto_real = minute + index

            # Determinar AM/PM para el nombre del archivo
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

            # Nombre del archivo: "06:00 AM.mp3", "06:01 AM.mp3", ...
            output_filename = f"{archivo_hour}:{minuto_real:02d} {archivo_am_pm}.mp3"
            output_path = temp_dir / output_filename
            final_audio_output_path = base_boletin_dir / output_filename

            # Verificar que todos los archivos existen
            missing_files = []
            for file_path in [conector_rreloj, hours_path, audio_path]:
                if not Path(file_path).exists():
                    missing_files.append(str(file_path))

            if usar_minutos:
                # Para cualquier otra hora, incluir minutos
                mins_path = Path(settings.OUTPUT_DIR) / \
                    f"profiles/{folder_id}/Minutes/{minute + index}.mp3"
                if not mins_path.exists():
                    missing_files.append(str(mins_path))
                    logger.warning(
                        f"Faltan archivos para minuto {index}: {missing_files}")
                    continue

                logger.info(
                    f"Minuto {index}: usando hours + minutes ({hour_filename} + {minute + index})")

                # Merge de hours + mins
                time_path = AudioMerger.merge_audio_files(
                    audio_paths=[str(hours_path), str(mins_path)],
                    output_path=str(output_path),
                    output_format="mp3",
                    crossfade_ms=50,
                    silence_thresh=-50,
                )
            else:
                # 12:00 AM o 12:00 PM en punto - solo el archivo de hora
                time_path = hours_path
                logger.info(
                    f"12:00 {'AM' if hour == 0 else 'PM'} en punto (minuto {index}): usando solo archivo de hora")

            if missing_files:
                logger.warning(
                    f"Faltan archivos para minuto {index}: {missing_files}")
                continue

            duration_time_path = AudioMerger.get_duration_seconds(time_path)
            duration_conector_rreloj = AudioMerger.get_duration(
                str(conector_rreloj))
            remaining_seconds = 60.0 - duration_time_path - duration_conector_rreloj

            title = self._extract_title(audio_obj.text)

            # Ajustar duración del audio
            output_audios_path = temp_dir / f"{audio_id}.mp3"
            info_path = AudioMerger.adjust_duration(
                input_path=str(audio_path),
                output_path=str(output_audios_path),
                target_seconds=remaining_seconds,
                output_format="mp3",
                tags={"title": title},
            )

            # Concatenar todos los audios
            final_audio = AudioMerger.concatenate_audio_files(
                audio_paths=[str(time_path), str(
                    info_path), str(conector_rreloj)],
                output_path=str(final_audio_output_path),
                output_format="mp3",
                crossfade_ms=0,
                tags={"title": title},
            )

            duracion_final = AudioMerger.get_duration_seconds(final_audio)
            logger.info(
                f"Archivo de audio {index}: {output_filename} - {duracion_final:.2f}s")

        return boletin

    def update(
        self,
        boletin_id: int,
        new_audio_ids: List[str],
    ) -> Boletin:
        """
        Actualiza un boletín existente con nuevos audios.
        Solo procesa los minutos donde el audio_id cambió.

        Args:
            boletin_id: ID del boletín a actualizar
            new_audio_ids: Lista de 30 nuevos IDs de audios

        Returns:
            Boletin: El boletín actualizado
        """
        # 1. Obtener boletín existente
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        # 2. Validar que el boletín esté activo
        if not boletin.active:
            raise ValueError(f"Boletín {boletin_id} no está activo")

        # 3. Validar cantidad de audios
        if len(new_audio_ids) != 30:
            raise ValueError(
                f"Se requieren exactamente 30 audios para un boletín completo. "
                f"Recibidos: {len(new_audio_ids)}"
            )

        # 4. Obtener los IDs actuales del boletín (en orden)
        current_audio_ids = self.boletin_repo.get_audio_ids_by_boletin_id(
            boletin_id)

        # 5. Validar que todos los nuevos audios existen en la BD
        for audio_id in new_audio_ids:
            audio = self.audio_repo.get_by_audio_id(audio_id, active=True)
            if not audio or audio["active"] == False:
                raise ValueError(
                    f"Audio con ID {audio_id} no encontrado o inactivo")

        # 6. Preparar datos del boletín
        bol_date = boletin.bol_date
        start_time = boletin.start_time
        hour = int(start_time.split(":")[0])
        hour_str = start_time.replace(":", "-")

        # 7. Procesar cada minuto
        for index, new_audio_id in enumerate(new_audio_ids):
            # Verificar si el audio cambió
            if current_audio_ids[index] == new_audio_id:
                logger.info(
                    f"Minuto {index}: sin cambios, manteniendo audio existente")
                continue

            logger.info(
                f"Minuto {index}: actualizando de {current_audio_ids[index] if index < len(current_audio_ids) else 'None'} a {new_audio_id}")

            # Obtener el nuevo audio con su relación
            audio_obj = self.audio_repo.get_by_audio_id_with_relationship(
                new_audio_id)
            folder_id = audio_obj.owner_profile.folder_id

            # Construir rutas de archivos fuente
            conector1 = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/conec/Rreloj.m4a"
            hours_path = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/hours/{hour}.m4a"
            mins_path = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/min/{index}.m4a"
            conector2 = f"{settings.OUTPUT_DIR}/profiles/{folder_id}/conec/Minutos.m4a"
            audio_path = f"{settings.OUTPUT_DIR}/generated/{new_audio_id}.wav"

            # Rutas de salida
            output_filename = f"{index:02d}.mp3"
            output_path = f"{settings.OUTPUT_DIR}/boletines/{bol_date}/{hour_str}/temp/{output_filename}"
            final_audio_output_path = f"{settings.OUTPUT_DIR}/boletines/{bol_date}/{hour_str}/{output_filename}"

            # Verificar que todos los archivos existen
            missing_files = []
            for file_path in [conector1, hours_path, mins_path, conector2, audio_path]:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            if missing_files:
                logger.warning(
                    f"Faltan archivos para minuto {index}: {missing_files}")
                continue

            # Crear directorio temporal si no existe
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Unir los conectores y la hora/minuto
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
                logger.warning(
                    f"El bloque de tiempo para minuto {index} dura {duration_time_path:.2f}s y no deja espacio para el audio adicional."
                )

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

        # 8. Actualizar la relación en BD con la nueva lista de audios
        self.boletin_repo.update_boletin_audios(boletin_id, new_audio_ids)

        logger.info(f"Boletín {boletin_id} actualizado correctamente")

        # 9. Retornar el boletín actualizado
        return self.boletin_repo.get_by_id(boletin_id)

    # app/services/boletin_service.py

    def soft_delete(self, boletin_id: int) -> dict:
        """
        Soft delete: desactiva un boletín (cambia active a False)
        """
        # 1. Verificar que el boletín existe
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        # 2. Verificar que esté activo
        if not boletin.active:
            raise ValueError(f"Boletín {boletin_id} ya está desactivado")

        # 3. Ejecutar soft delete
        self.boletin_repo.soft_delete(boletin_id)

        logger.info(f"Boletín {boletin_id} desactivado")

        return {
            "boletin_id": boletin_id,
            "start_time": boletin.start_time,
            "message": "Boletín desactivado correctamente"
        }

    def activate_boletin(self, boletin_id: int) -> dict:
        """
        Activa un boletín (cambia active a True)
        """
        # 1. Verificar que el boletín existe
        boletin = self.boletin_repo.get_by_id(boletin_id)
        if not boletin:
            raise ValueError(f"Boletín {boletin_id} no encontrado")

        # 2. Verificar que esté inactivo
        if boletin.active:
            raise ValueError(f"Boletín {boletin_id} ya está activo")

        # 3. Activar
        self.boletin_repo.activate(boletin_id)

        logger.info(f"Boletín {boletin_id} activado")

        return {
            "boletin_id": boletin_id,
            "start_time": boletin.start_time,
            "message": "Boletín activado correctamente"
        }
