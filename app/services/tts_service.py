# app/services/tts_service.py
from ast import Pass
from datetime import datetime
import tempfile
import pickle
import shutil
from pathlib import Path
from typing import Optional
from sqlmodel import Session
from app.core.logging import get_logger
from app.models.profile_model import Profile
from app.repositories.profile_repository import ProfileRepository
from app.utils.validators.audio_validator import AudioValidator
from app.core.config import settings
import torch
from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem
import io
import uuid
import soundfile as sf

logger = get_logger(__name__)

class TTSService:
    def __init__(self, db: Session, model):
        self.repo = ProfileRepository(db)
        self.model = model
        self.db = db
        
        # Carpeta base para perfiles
        self.profiles_base_dir = Path(settings.OUTPUT_DIR) / "profiles"
    
    def create_profile(
        self,
        name: str,
        ref_text: str,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        language: str = "Spanish"
    ):
        AudioValidator.validate(audio_bytes, filename, content_type)
        
        ext = Path(filename).suffix.lower()
        temp_path = None
        
        # Crear carpeta con el nombre del perfil
        safe_name = "".join(c for c in name.strip() if c.isalnum() or c in " ._-")
        profile_folder = self.profiles_base_dir / safe_name
        profile_folder.mkdir(parents=True, exist_ok=True)
        
        # Rutas permanentes
        audio_path = profile_folder / f"audio{ext}"
        prompt_path = profile_folder / f"{name.lower()}.pt"
        
        
        try:
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name
            
            # Copiar audio a la carpeta del perfil (PERMANENTE)
            shutil.copy2(temp_path, audio_path)
            logger.info(f"Audio guardado: {audio_path}")
            
            # Generar prompt usando la ruta permanente
            voice_prompt = self.model.create_voice_clone_prompt(
                ref_audio=str(audio_path),
                ref_text=ref_text.strip()
            )
            
            # Guardar el prompt
            torch.save(voice_prompt, prompt_path)
            logger.info(f"Prompt guardado: {prompt_path}")
            
            # Guardar en BD (solo las rutas, no el blob)
            profile_data = Profile(
                name=name.strip(),
                language=language,
                ref_text=ref_text.strip(),
                folder_path=str(profile_folder),
                audio_path=str(audio_path),
                prompt_path=str(prompt_path)
            )
            
            profile = self.repo.create(profile_data, None)  # No guardar blob en BD
            
            logger.info(f"Perfil '{name}' creado en: {profile_folder}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creando perfil: {e}")
            # Limpiar carpeta si algo falló
            if profile_folder.exists():
                shutil.rmtree(profile_folder)
            raise
            
        finally:
            # Limpiar archivo temporal
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)
                
                
    def synthesize_with_profile(
            self,
            profile_id: int,   
            text: str,
            language: str = "Spanish",
            save_audio: bool = True 
        ) -> bytes:
            
            
            # 1. Obtener el perfil desde la BD
            profile = self.repo.get_by_id(profile_id)
            if not profile:
                raise ValueError(f"Perfil {profile_id} no encontrado")
            
            logger.info(f"Perfil encontrado: {profile.name}")
            
            # 2. Cargar el prompt (.pt)
            pt_path = Path(settings.OUTPUT_DIR) / "profiles" /profile.name / f"{profile.name.lower()}.pt"
    
            if not pt_path.exists():
                raise FileNotFoundError(f"Prompt no encontrado: {pt_path}")
    
            logger.info(f"Prompt cargado desde: {pt_path}")
            
            # 3. Cargar con torch.load (como en el proyecto que funciona)
            torch.serialization.add_safe_globals([VoiceClonePromptItem])
            
            voice_clone_prompt = torch.load(
                pt_path,
                map_location=settings.DEVICE,
                weights_only=False,
            )
            
            logger.info(f"Prompt cargado: {pt_path}")
            
            # 4. Generar audio
            if torch.cuda.is_available():
                autocast_device = "cuda"
                dtype = torch.float16
            else:
                autocast_device = "cpu"
                dtype = torch.float32  # CPU no soporta float16
            
            
            with torch.no_grad(), torch.amp.autocast(autocast_device, dtype=dtype):
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=text,
                    voice_clone_prompt=voice_clone_prompt,
                    max_new_tokens=min(len(text) * 2, 2048),
                    use_cache=True,
                    do_sample=True,
                    temperature=0.8,
                    top_p=0.9,
                    repetition_penalty=1.15,
                )
            
             # 5. Convertir a numpy
            audio = wavs[0] if isinstance(wavs, list) else wavs
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
    
            # 6. GUARDAR EL AUDIO EN settings.OUTPUT_DIR
            if save_audio:
                # Crear directorio si no existe
                output_dir = Path(settings.OUTPUT_DIR) / "generated_audio"
                output_dir.mkdir(parents=True, exist_ok=True)
        
            # Generar nombre único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{profile.name}_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
            filepath = output_dir / filename
        
            # Guardar archivo WAV
            sf.write(filepath, audio, sample_rate)
            logger.info(f"Audio guardado en: {filepath}")
            logger.info(f"Ruta completa: {filepath.absolute()}")
        
            # 7. Convertir a bytes para devolver (opcional)
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format='wav')
            buffer.seek(0)
            
            return buffer.read()