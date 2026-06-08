# app/services/tts_service.py
import re
import time
import torch
import numpy as np
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
        logger.info(f"Generando prompt para audio: {audio_path}")
        voice_prompt = self.model.create_voice_clone_prompt(
            ref_audio=audio_path,
            ref_text=ref_text.strip()
        )
        torch.save(voice_prompt, prompt_path)
        logger.info(f"Prompt guardado: {prompt_path}")

    def load_prompt(self, prompt_path: str) -> VoiceClonePromptItem:
        torch.serialization.add_safe_globals([VoiceClonePromptItem])
        return torch.load(prompt_path, map_location=settings.DEVICE, weights_only=False)

    def _split_sentences(self, text: str) -> list[str]:
        """Divide el texto en oraciones por . ! ?"""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        # filtrar vacíos y oraciones muy cortas
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    def synthesize(self, prompt: VoiceClonePromptItem, text: str, language: str = "Auto") -> tuple:
        sentences = self._split_sentences(text)

        # Si es una sola oración, generación directa
        if len(sentences) <= 1:
            return self._synthesize_single(prompt, text, language)

        logger.info(f"Sintetizando {len(sentences)} oraciones en batch")
        return self._synthesize_batch(prompt, sentences, language)

    def _synthesize_single(self, prompt: VoiceClonePromptItem, text: str, language: str) -> tuple:
        logger.info(f"Sintetizando (single): '{text[:80]}...' " if len(text) > 80 else f"Sintetizando: '{text}'")
        device = settings.DEVICE.lower()
        t2 = time.time()

        if device == "cuda":
            with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.float16):
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                    max_new_tokens=min(len(text) * 2, 1000),
                )
        else:
            with torch.no_grad():
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                    max_new_tokens=min(len(text) * 2, 1000),
                )

        logger.info(f"Generación modelo: {time.time() - t2:.2f}s")
        audio = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        logger.info(f"Sintetización completada - sample_rate: {sample_rate}")
        return audio, sample_rate

    def _synthesize_batch(self, prompt: VoiceClonePromptItem, sentences: list[str], language: str) -> tuple:
        logger.info(f"Sintetizando batch de {len(sentences)} oraciones")
        device = settings.DEVICE.lower()
        t2 = time.time()
        torch.cuda.empty_cache()
        
        if device == "cuda":
            with torch.no_grad(), torch.amp.autocast("cuda", dtype=torch.float16):
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=sentences,
                    language=[language] * len(sentences),
                    voice_clone_prompt=prompt,
                    max_new_tokens=500,
                )
        else:
            with torch.no_grad():
                wavs, sample_rate = self.model.generate_voice_clone(
                    text=sentences,
                    language=[language] * len(sentences),
                    voice_clone_prompt=prompt,
                    max_new_tokens=500,
                )

        logger.info(f"Generación batch modelo: {time.time() - t2:.2f}s")

        # Convertir cada wav a numpy
        chunks = []
        silence = np.zeros(int(sample_rate * 0.25))  # 250ms de silencio entre oraciones

        for i, wav in enumerate(wavs):
            if isinstance(wav, torch.Tensor):
                wav = wav.cpu().numpy()
            chunks.append(wav)
            if i < len(wavs) - 1:
                chunks.append(silence)

        audio = np.concatenate(chunks)
        logger.info(f"Sintetización batch completada - sample_rate: {sample_rate}")
        return audio, sample_rate