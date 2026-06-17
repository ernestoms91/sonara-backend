# app/services/audio_service.py
import json
import io
import uuid
import pyrubberband as pyrb
from fastapi import Request
import soundfile as sf
import time
import re
import numpy as np
from pathlib import Path
from sqlmodel import Session
from app.core.config import settings
from app.core.logging import get_logger
from app.helpers.generate_peaks import generate_peaks_from_array
from app.models.generated_audio_model import GeneratedAudio
from app.repositories.generated_audio_repository import GeneratedAudioRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.tts_service import TTSService

logger = get_logger(__name__)


class AudioService:
    def __init__(self, db: Session, tts_service: TTSService):
        self.db = db
        self.tts_service = tts_service
        self.profile_repo = ProfileRepository(db)
        self.audio_repo = GeneratedAudioRepository(db)
        self.audios_base_dir = Path(settings.OUTPUT_DIR) / "generated"
        self.waveforms_base_dir = Path(settings.OUTPUT_DIR) / "waveforms"

    # ─── Helpers privados ────────────────────────────────────────────────────
    
    def _normalize_text_with_marker(self, text: str) -> str:
        """
        Asegura que el texto tenga un marcador [P1] al inicio.
        SOLO PARA UNA VOZ. Los duetos ya tienen su estructura [P1], [P2], etc.
        """
        if not text:
            return "[P1] Texto vacío"
        
        text = text.strip()
        
        # Si ya tiene [P1] al inicio, devolver tal cual
        if re.match(r'^\[P1\]', text, re.IGNORECASE):
            return text
        
        # Si tiene algún marcador [Pn] pero no [P1] al inicio
        if re.search(r'\[P\d+\]', text):
            # Reemplazar el primer marcador por [P1]
            return re.sub(r'\[P\d+\]', '[P1]', text, count=1)
        
        # No tiene marcadores, agregar [P1] al inicio
        return f"[P1] {text}"

    def _clean_text_for_tts(self, text: str) -> str:
        """
        Limpia el texto para TTS eliminando marcadores pero manteniendo estructura.
        """
        if not text:
            return ""
        
        # Eliminar marcadores [Pn] pero conservar el texto
        cleaned = re.sub(r'\[P\d+\]\s*', '', text)
        
        # Normalizar múltiples saltos de línea
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Limpiar líneas vacías
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n\n'.join(line for line in lines if line)
        
        return cleaned

    def _extract_first_sentence(self, text: str) -> str:
        if not text:
            return "Audio sin título"
        
        # Siempre limpiar marcadores, incluso si no los tiene
        clean = re.sub(r'\[P\d+\]\s*', '', text).strip()
        
        if not clean:
            return "Audio sin título"
        
        match = re.search(r"(.+?[\.\!\?])(?:\s|$)", clean)
        if match:
            first_sentence = match.group(1).strip()
            if len(first_sentence) > 60:
                first_sentence = first_sentence[:57] + "..."
            return first_sentence
        
        first_line = clean.splitlines()[0].strip() if clean.splitlines() else clean
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."
        return first_line if first_line else "Audio sin título"

    def _extract_paragraphs_from_markers(self, text: str) -> list[str]:
        markers = re.findall(r'\[P(\d+)\]', text, re.IGNORECASE)
        if not markers:
            raise ValueError("No se encontraron marcadores [Pn] en el texto")

        total = max(int(m) for m in markers)
        paragraphs = []

        for i in range(1, total + 1):
            pattern = (
                rf'\[P{i}\](.*?)(?=\[P{i+1}\])'
                if i < total
                else rf'\[P{i}\](.*?)$'
            )
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if not match:
                raise ValueError(f"No se encontró el marcador [P{i}]")
            paragraph = match.group(1).strip()
            if not paragraph:
                raise ValueError(f"El marcador [P{i}] está vacío")
            paragraphs.append(paragraph)

        logger.info(f"Párrafos extraídos: {len(paragraphs)}")
        for idx, p in enumerate(paragraphs, 1):
            logger.debug(f"P{idx}: {p[:50]}{'...' if len(p) > 50 else ''}")

        return paragraphs

    def _normalize_volume(self, audio_array: np.ndarray) -> np.ndarray:
        """Normaliza el volumen al 95%."""
        max_abs = np.max(np.abs(audio_array))
        if max_abs > 0:
            audio_array = audio_array / max_abs * 0.95
        return audio_array

    def _apply_time_stretch(
        self,
        audio_array: np.ndarray,
        sample_rate: int,
        target_duration: float,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Aplica time-stretch al audio para alcanzar target_duration usando rubberband.
        
        Args:
            audio_array: Audio original
            sample_rate: Tasa de muestreo
            target_duration: Duración deseada en segundos
            normalize: Si debe normalizar el volumen (default True)
        """
        current_duration = len(audio_array) / sample_rate
        rate = current_duration / target_duration
        
        logger.info(f"Time-stretch: {current_duration:.2f}s → {target_duration:.2f}s (rate={rate:.3f})")
        
        audio_stretched = pyrb.time_stretch(
            audio_array.astype(np.float32),
            sample_rate,
            rate
        )
        
        # Ajustar a la longitud exacta
        target_samples = int(round(target_duration * sample_rate))
        if len(audio_stretched) > target_samples:
            audio_stretched = audio_stretched[:target_samples]
        elif len(audio_stretched) < target_samples:
            audio_stretched = np.pad(audio_stretched, (0, target_samples - len(audio_stretched)))
        
        # Normalizar si es necesario
        if normalize:
            audio_stretched = self._normalize_volume(audio_stretched)
        
        logger.info(f"Duración final: {len(audio_stretched) / sample_rate:.2f}s")
        return audio_stretched.astype(np.float32)

    def _save_audio_file(self, audio_array: np.ndarray, sample_rate: int, audio_uuid: str) -> str:
        """Guarda el archivo WAV y retorna el filename."""
        self.audios_base_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{audio_uuid}.wav"
        sf.write(self.audios_base_dir / filename, audio_array, sample_rate)
        logger.info(f"Audio guardado en: {self.audios_base_dir / filename}")
        return filename

    def _save_waveform(self, audio_array: np.ndarray, sample_rate: int, audio_uuid: str) -> dict:
        """Genera y guarda el waveform JSON. Retorna el dict."""
        peaks = generate_peaks_from_array(audio_array, sample_rate, pixels_per_second=settings.PIXELS_PER_SECOND)
        waveform_data = {
            "sample_rate": sample_rate,
            "bits": 8,
            "duration": float(len(audio_array) / sample_rate),
            "channels": 1 if audio_array.ndim == 1 else 2,
            "pixels_per_second": 20,
            "data_overview_length": len(peaks),
            "data": peaks,
        }
        waveform_path = self.waveforms_base_dir / f"{audio_uuid}.json"
        with open(waveform_path, "w", encoding="utf-8") as f:
            json.dump(waveform_data, f, ensure_ascii=False)
        logger.info(f"Waveform guardado en: {waveform_path}")
        return waveform_data

    def _to_bytes(self, audio_array: np.ndarray, sample_rate: int) -> bytes:
        """Convierte audio array a bytes WAV."""
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, sample_rate, format='wav')
        return buffer.getvalue()

    # ─── Métodos públicos ─────────────────────────────────────────────────────

    def generate_and_save(self, profile_id: int, text: str, created_by: str) -> dict:
        profile = self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"Perfil {profile_id} no encontrado")
        if not profile.active:
            raise ValueError(f"Perfil {profile_id} no está activo")

        prompt_path = Path(settings.OUTPUT_DIR) / "profiles" / profile.folder_id / f"{profile.name.lower()}.pt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt no encontrado: {prompt_path}")

        prompt = self.tts_service.load_prompt(str(prompt_path))
        
        # Normalizar texto: asegurar que tenga [P1] si no lo tiene
        text_normalizado = self._normalize_text_with_marker(text)
        
        # Limpiar texto para TTS (remover marcadores para la síntesis)
        text_clean = self._clean_text_for_tts(text_normalizado)
        logger.info(f"Texto para TTS: {text_clean[:100]}...")
        
        audio_array, sample_rate = self.tts_service.synthesize(prompt, text_clean, language=profile.language)

        duration = len(audio_array) / sample_rate

        audio_uuid = str(uuid.uuid4())
        filename = self._save_audio_file(audio_array, sample_rate, audio_uuid)
        waveform_data = self._save_waveform(audio_array, sample_rate, audio_uuid)

        # Extraer título del texto limpio
        title = self._extract_first_sentence(text_clean)
        logger.info(f"Título extraído: {title}")

        saved_audio = self.audio_repo.create(GeneratedAudio(
            audio_id=audio_uuid,
            profile_id=profile_id,
            text=text_normalizado,
            duration=duration,
            title=title,
            waveform=audio_uuid,
            created_by=created_by,
            character_count=len(text_clean)
        ))

        result = {
            "id": saved_audio.id,
            "audio_id": saved_audio.audio_id,
            "audio_bytes": self._to_bytes(audio_array, sample_rate),
            "filename": filename,
            "duration": duration,
            "character_count": len(text_clean),
            "created_at": saved_audio.created_at,
            "waveform": waveform_data
        }

        # Limpiar memoria
        self.tts_service.empty_cache()
        del audio_array

        return result

    def generate_duet_and_save(
        self,
        profile_a_id: int,
        profile_b_id: int,
        text_with_markers: str,
        created_by: str
    ) -> dict:
        paragraphs = self._extract_paragraphs_from_markers(text_with_markers)

        profile_a = self.profile_repo.get_by_id(profile_a_id)
        if not profile_a or not profile_a.active:
            raise ValueError(f"Perfil A {profile_a_id} no encontrado o no activo")

        profile_b = self.profile_repo.get_by_id(profile_b_id)
        if not profile_b or not profile_b.active:
            raise ValueError(f"Perfil B {profile_b_id} no encontrado o no activo")

        language = profile_a.language
        if profile_a.language != profile_b.language:
            logger.warning(f"Idiomas diferentes: A={profile_a.language}, B={profile_b.language}. Usando idioma de A.")

        prompt_a_path = Path(settings.OUTPUT_DIR) / "profiles" / profile_a.folder_id / f"{profile_a.name.lower()}.pt"
        prompt_b_path = Path(settings.OUTPUT_DIR) / "profiles" / profile_b.folder_id / f"{profile_b.name.lower()}.pt"

        if not prompt_a_path.exists():
            raise FileNotFoundError(f"Prompt no encontrado: {prompt_a_path}")
        if not prompt_b_path.exists():
            raise FileNotFoundError(f"Prompt no encontrado: {prompt_b_path}")

        prompt_a = self.tts_service.load_prompt(str(prompt_a_path))
        prompt_b = self.tts_service.load_prompt(str(prompt_b_path))

        duet_paragraphs = [
            {"speaker": "A" if (i % 2 == 0) else "B", "text": p}
            for i, p in enumerate(paragraphs)
        ]

        audio_array, sample_rate = self.tts_service.synthesize_duet(
            prompt_a=prompt_a,
            prompt_b=prompt_b,
            paragraphs=duet_paragraphs,
            language=language
        )

        duration = len(audio_array) / sample_rate
        character_count = sum(len(p) for p in paragraphs)

        combined_text = ""
        for i, p in enumerate(paragraphs):
            combined_text += f"[P{i+1}] {p}\n\n"

        audio_uuid = str(uuid.uuid4())
        filename = self._save_audio_file(audio_array, sample_rate, audio_uuid)
        waveform_data = self._save_waveform(audio_array, sample_rate, audio_uuid)

        saved_audio = self.audio_repo.create(GeneratedAudio(
            audio_id=audio_uuid,
            profile_id=profile_a_id,
            secondary_profile_id=profile_b_id,
            text=combined_text,
            duration=duration,
            title= self._extract_first_sentence(paragraphs[0]),
            waveform=audio_uuid,
            created_by=created_by,
            character_count=character_count
        ))

        result = {
            "id": saved_audio.id,
            "audio_id": saved_audio.audio_id,
            "audio_bytes": self._to_bytes(audio_array, sample_rate),
            "filename": filename,
            "duration": duration,
            "character_count": character_count,
            "created_at": saved_audio.created_at,
            "waveform": waveform_data,
            "profile_a": profile_a.name,
            "profile_b": profile_b.name
        }

        # Limpiar memoria
        self.tts_service.empty_cache()
        del audio_array

        return result
    
    def get_audios_paginated(
        self,
        page: int = 1,
        size: int = 50,
        actives: bool = True,
        request: Request = None
    ) -> dict:
        if size > 100:
            logger.warning(f"Tamaño de página {size} excede el límite, limitando a 100")
            size = 100
        if page < 1:
            logger.warning(f"Página {page} inválida, usando página 1")
            page = 1

        logger.info(f"Obteniendo audios paginados - Página: {page}, Tamaño: {size}")
        result = self.audio_repo.get_audios_paginated(page=page, size=size, actives=actives)

        if request and result.get("items"):
            base_url = str(request.base_url).rstrip('/')
            for item in result["items"]:
                audio_id = item.get("audio_id")
                if audio_id:
                    item["waveform_url"] = f"{base_url}/waveforms/{audio_id}.json"
                    item["audio_url"] = f"{base_url}/audios/{audio_id}.wav"

        return result

    def soft_delete_audio(self, audio_id: str) -> dict:
        audio = self.audio_repo.get_by_id(audio_id)
        if not audio:
            raise ValueError(f"Audio {audio_id} no encontrado o se encuentra desactivado")
        self.audio_repo.soft_delete(audio_id)
        logger.info(f"Audio {audio_id} desactivado (soft delete)")
        return {
            "audio_id": audio_id,
            "message": "Audio desactivado correctamente",
            "profile_id": audio["profile_id"],
            "profile_name": audio["profile_name"]
        }

    def activate_audio(self, audio_id: str) -> dict:
        audio = self.audio_repo.get_by_id(audio_id, active=0)
        if not audio:
            raise ValueError(f"Audio {audio_id} no encontrado")
        self.audio_repo.activate(audio_id)
        logger.info(f"Audio {audio_id} activado")
        return {
            "audio_id": audio_id,
            "message": "Audio activado",
            "profile_id": audio["profile_id"],
            "profile_name": audio["profile_name"]
        }


    def generate_boletin_audios(
        self,
        boletin_data: dict,
        profile_a_id: int,
        profile_b_id: int,
        created_by: str
    ) -> dict:
        """
        Genera audios para un boletín completo (TODO O NADA).
        Si algún minuto falla, se eliminan todos los audios generados.
        """
        start_time = time.time()
        
        minutos = boletin_data.get("minutos", {})
        sigla = boletin_data.get("sigla", "")
        fecha = boletin_data.get("fecha", "")
        hora = boletin_data.get("hora", "")
        
        cantidad_minutos = len(minutos)
        
        if cantidad_minutos != 30:
            raise ValueError(f"Se requieren exactamente 30 minutos. Recibidos: {cantidad_minutos}")
        
        logger.info(f"INICIANDO BOLETIN: {sigla} - {fecha} - {cantidad_minutos} minutos")
        
        resultados = []
        audios_generados = []
        
        # Variable para recordar la última voz usada en párrafo único
        ultima_voz_unica = None  # "A" o "B"
        
        try:
            for i, (num_minuto, texto) in enumerate(minutos.items()):
                minuto_start = time.time()
                
                # Detectar cuántos párrafos tiene este minuto
                num_parrafos = len(re.findall(r'\[P\d+\]', texto))
                es_parrafo_unico = num_parrafos == 1
                
                if es_parrafo_unico:
                    # Alternar voz para párrafos únicos
                    if ultima_voz_unica is None:
                        voz_a_usar = "A"
                    else:
                        voz_a_usar = "B" if ultima_voz_unica == "A" else "A"
                    
                    ultima_voz_unica = voz_a_usar
                    profile_id = profile_a_id if voz_a_usar == "A" else profile_b_id
                    
                    logger.info(f"PROCESANDO MINUTO {i+1}/{cantidad_minutos} | Tipo: Unico | Voz: {voz_a_usar}")
                    
                    result = self.generate_and_save(
                        profile_id=profile_id,
                        text=texto,
                        created_by=created_by
                    )
                    result["speaker"] = f"{voz_a_usar} (unico)"
                    result["tipo"] = "unico"
                else:
                    logger.info(f"PROCESANDO MINUTO {i+1}/{cantidad_minutos} | Tipo: Dueto | Voz: A/B")
                    
                    result = self.generate_duet_and_save(
                        profile_a_id=profile_a_id,
                        profile_b_id=profile_b_id,
                        text_with_markers=texto,
                        created_by=created_by
                    )
                    result["speaker"] = "dueto A/B"
                    result["tipo"] = "dueto"
                
                resultados.append({
                    "minuto": i + 1,
                    "audio_id": result["audio_id"],
                    "duration": result["duration"],
                    "filename": result["filename"],
                    "created_at": result["created_at"],
                    "character_count": result["character_count"],
                    "tiempo_segundos": round(time.time() - minuto_start, 2),
                    "speaker": result["speaker"],
                    "tipo": result["tipo"]
                })
                
                audios_generados.append(result["audio_id"])
                
                # Limpiar memoria después de cada minuto
                self.tts_service.empty_cache()
                
                logger.info(f"Minuto {i + 1} completado en {time.time() - minuto_start:.2f}s | Caracteres: {result['character_count']}")
                
                # LOG DE PROGRESO CADA 5 MINUTOS
                if (i + 1) % 5 == 0:
                    porcentaje = ((i + 1) / cantidad_minutos) * 100
                    logger.info(f"PROGRESO: {i+1}/{cantidad_minutos} minutos ({porcentaje:.0f}%)")
            
            # CALCULAR ESTADÍSTICAS
            total_duration = time.time() - start_time
            total_minutes = total_duration / 60
            
            duetos = sum(1 for r in resultados if r["tipo"] == "dueto")
            unicos = sum(1 for r in resultados if r["tipo"] == "unico")
            voz_a_unicos = sum(1 for r in resultados if r.get("speaker") == "A (unico)")
            voz_b_unicos = sum(1 for r in resultados if r.get("speaker") == "B (unico)")
            
            logger.info(f"BOLETIN COMPLETADO: {cantidad_minutos} minutos | Duetos: {duetos} | Unicos: {unicos} (A:{voz_a_unicos}, B:{voz_b_unicos}) | Tiempo total: {total_minutes:.2f} min")
            
            return {
                "total_minutos": cantidad_minutos,
                "generados": len(resultados),
                "errores": 0,
                "tiempo_total_segundos": round(total_duration, 2),
                "tiempo_total_minutos": round(total_minutes, 2),
                "tiempo_promedio_por_minuto_segundos": round(total_duration / len(resultados), 2),
                "tiempo_promedio_por_minuto_minutos": round(total_minutes / len(resultados), 2),
                "estadisticas": {
                    "duetos": duetos,
                    "unicos": unicos,
                    "voz_a_unicos": voz_a_unicos,
                    "voz_b_unicos": voz_b_unicos
                },
                "audios": resultados
            }
            
        except Exception as e:
            minuto_fallido = i + 1 if 'i' in locals() else '?'
            
            logger.error(f"BOLETIN CANCELADO: Error en minuto {minuto_fallido} - {str(e)}")
            logger.info(f"Limpiando {len(audios_generados)} audios generados...")
            
            for audio_id in audios_generados:
                try:
                    self.audio_repo.soft_delete(audio_id)
                    
                    audio_path = self.audios_base_dir / f"{audio_id}.wav"
                    if audio_path.exists():
                        audio_path.unlink()
                    
                    waveform_path = self.waveforms_base_dir / f"{audio_id}.json"
                    if waveform_path.exists():
                        waveform_path.unlink()
                        
                except Exception as cleanup_error:
                    logger.error(f"No se pudo eliminar {audio_id}: {cleanup_error}")
            
            logger.info(f"Limpieza completada: {len(audios_generados)} audios eliminados")
            raise ValueError(f"Boletín fallido. Se eliminaron {len(audios_generados)} audios. Error original: {str(e)}")