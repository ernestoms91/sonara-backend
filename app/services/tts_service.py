# app/services/tts_service.py
import re
import time
import torch
import numpy as np
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
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    def _empty_cache(self):
        """Libera memoria GPU si está disponible"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def synthesize(self, prompt: VoiceClonePromptItem, text: str, language: str = "Auto") -> tuple:
        """Sintetiza un texto completo con una sola voz"""
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return self._synthesize_single(prompt, text, language)

        logger.info(f"Sintetizando {len(sentences)} oraciones en batch")
        return self._synthesize_batch(prompt, sentences, language)

    def _synthesize_single(self, prompt: VoiceClonePromptItem, text: str, language: str) -> tuple:
        """Sintetiza una sola oración"""
        logger.info(f"Sintetizando (single): '{text[:80]}...'" if len(text) > 80 else f"Sintetizando: '{text}'")
        device = settings.DEVICE.lower()

        self._empty_cache()
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

        self._empty_cache()
        logger.info(f"Generación modelo: {time.time() - t2:.2f}s")

        audio = wavs[0] if isinstance(wavs, list) else wavs
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        logger.info(f"Sintetización completada - sample_rate: {sample_rate}")
        return audio, sample_rate

    def _synthesize_batch(
        self,
        prompt: VoiceClonePromptItem,
        sentences: list[str],
        language: str,
        return_raw: bool = False
    ) -> tuple:
        """
        Sintetiza múltiples oraciones en batch.

        Args:
            prompt: Prompt de voz clonada
            sentences: Lista de oraciones
            language: Idioma
            return_raw: Si True devuelve lista de audios sin concatenar

        Returns:
            Si return_raw=False: (audio_concatenado, sample_rate)
            Si return_raw=True: (lista_de_audios, sample_rate)
        """
        logger.info(f"Sintetizando batch de {len(sentences)} oraciones")
        device = settings.DEVICE.lower()

        self._empty_cache()
        t2 = time.time()

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

        self._empty_cache()
        logger.info(f"Generación batch modelo: {time.time() - t2:.2f}s")

        audios = []
        for wav in wavs:
            if isinstance(wav, torch.Tensor):
                audios.append(wav.cpu().numpy())
            else:
                audios.append(wav)

        if return_raw:
            logger.info(f"Devolviendo {len(audios)} audios individuales")
            return audios, sample_rate

        silence = np.zeros(int(sample_rate * 0.25))
        chunks = []
        for i, audio in enumerate(audios):
            chunks.append(audio)
            if i < len(audios) - 1:
                chunks.append(silence)

        audio = np.concatenate(chunks)
        logger.info(f"Sintetización batch completada - sample_rate: {sample_rate}")
        return audio, sample_rate

    def synthesize_duet(
        self,
        prompt_a: VoiceClonePromptItem,
        prompt_b: VoiceClonePromptItem,
        paragraphs: list[dict],
        language: str = "Auto"
    ) -> tuple:
        """
        Genera audio con dos voces alternadas por párrafo.

        Args:
            prompt_a: Prompt del locutor A
            prompt_b: Prompt del locutor B
            paragraphs: Lista de dicts con formato:
                       [{"speaker": "A", "text": "texto p1"},
                        {"speaker": "B", "text": "texto p2"}, ...]
            language: Idioma para la generación

        Returns:
            (audio_concatenado, sample_rate)
        """
        logger.info(f"Iniciando síntesis duet con {len(paragraphs)} párrafos")

        # Dividir cada párrafo en oraciones
        paragraphs_data = []
        for i, p in enumerate(paragraphs):
            sentences = self._split_sentences(p["text"])
            paragraphs_data.append({
                "speaker": p["speaker"],
                "sentences": sentences,
                "num_sentences": len(sentences),
                "original_index": i
            })
            logger.debug(f"Párrafo {i+1} (locutor {p['speaker']}): {len(sentences)} oraciones")

        # Separar oraciones por locutor
        sentences_a, sentences_b = [], []
        structure_a, structure_b = [], []

        for p_data in paragraphs_data:
            if p_data["speaker"] == "A":
                structure_a.append(p_data["num_sentences"])
                sentences_a.extend(p_data["sentences"])
            else:
                structure_b.append(p_data["num_sentences"])
                sentences_b.extend(p_data["sentences"])

        # Generar batch A
        sample_rate = None
        audios_a, audios_b = [], []

        if sentences_a:
            logger.info(f"Generando {len(sentences_a)} oraciones para locutor A")
            audios_a, sample_rate = self._synthesize_batch(
                prompt_a, sentences_a, language, return_raw=True
            )

        self._empty_cache()

        if sentences_b:
            logger.info(f"Generando {len(sentences_b)} oraciones para locutor B")
            audios_b, sample_rate = self._synthesize_batch(
                prompt_b, sentences_b, language, return_raw=True
            )

        self._empty_cache()

        # Reconstruir estructura por párrafo
        wavs_by_paragraph_a = []
        idx = 0
        for num in structure_a:
            wavs_by_paragraph_a.append(audios_a[idx:idx + num])
            idx += num

        wavs_by_paragraph_b = []
        idx = 0
        for num in structure_b:
            wavs_by_paragraph_b.append(audios_b[idx:idx + num])
            idx += num

        # Intercalar en orden original
        final_chunks = []
        idx_a = 0
        idx_b = 0
        silence_short = np.zeros(int(sample_rate * 0.25))  # entre oraciones
        silence_long = np.zeros(int(sample_rate * 0.5))    # entre locutores

        for p_idx, p_data in enumerate(paragraphs_data):
            if p_data["speaker"] == "A":
                for audio_chunk in wavs_by_paragraph_a[idx_a]:
                    final_chunks.append(audio_chunk)
                    final_chunks.append(silence_short)
                idx_a += 1
            else:
                for audio_chunk in wavs_by_paragraph_b[idx_b]:
                    final_chunks.append(audio_chunk)
                    final_chunks.append(silence_short)
                idx_b += 1

            # Silencio largo entre cambios de locutor
            if p_idx < len(paragraphs_data) - 1:
                next_speaker = paragraphs_data[p_idx + 1]["speaker"]
                if next_speaker != p_data["speaker"]:
                    final_chunks.append(silence_long)

        # Quitar último silencio corto si quedó al final
        if final_chunks and len(final_chunks[-1]) == len(silence_short):
            final_chunks.pop()

        logger.info(f"Concatenando {len(final_chunks)} segmentos de audio")
        audio_final = np.concatenate(final_chunks)
        duration = len(audio_final) / sample_rate

        logger.info(f"Síntesis duet completada - duración: {duration:.2f}s, sample_rate: {sample_rate}")
        return audio_final, sample_rate