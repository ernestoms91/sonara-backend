# app/services/tts_service.py
import io
import time
import torch
import soundfile as sf
from pathlib import Path
from app.core.config import settings
from app.core.logging import get_logger
from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem

logger = get_logger(__name__)


class TTSService:
    def __init__(self, model):
        self.model = model

    def generate_and_save_prompt(
        self,
        audio_path: str,
        ref_text: str,
        prompt_path: Path
    ) -> None:
        """
        Genera el prompt y lo guarda en disco.
        """
        logger.info(f"Generando prompt para audio: {audio_path}")

        voice_prompt = self.model.create_voice_clone_prompt(
            ref_audio=audio_path,
            ref_text=ref_text.strip()
        )

        torch.save(voice_prompt, prompt_path)
        logger.info(f"Prompt guardado: {prompt_path}")

    def load_prompt(self, prompt_path: str) -> VoiceClonePromptItem:
        """Carga un prompt desde un archivo .pt"""
        torch.serialization.add_safe_globals([VoiceClonePromptItem])
        return torch.load(prompt_path, map_location=settings.DEVICE, weights_only=False)

    def synthesize(self, prompt: VoiceClonePromptItem, text: str, language: str = "Auto") -> tuple:
        logger.info(f"Sintetizando: '{text}'")

        device = settings.DEVICE.lower()

        t2 = time.time()
        if device == "cuda":
            with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.float16):
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                    max_new_tokens=min(len(text) * 2, 2048),
                )
        else:
            with torch.no_grad():
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                    max_new_tokens=min(len(text) * 2, 2048),
                )
        logger.info(f"Generación modelo: {time.time() - t2:.2f}s")

        audio = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        logger.info(f"Sintetización completada - sample_rate: {sample_rate}")
        return audio, sample_rate