import librosa
import numpy as np
from pathlib import Path

def generate_peaks_from_array(
    audio_array: np.ndarray,
    sample_rate: int,
    pixels_per_second: int = 20
) -> list[float]:
    """
    Genera peaks desde un array de audio (mono).
    Si el audio está en estéreo, lo convertimos a mono.
    """
    # Convertir a mono si es estéreo
    if len(audio_array.shape) > 1:
        audio_array = np.mean(audio_array, axis=1)

    duration = len(audio_array) / sample_rate

    # Samples por "pixel" (por cada segundo dividido en partes)
    samples_per_pixel = sample_rate / pixels_per_second

    # Número de pixels
    num_pixels = int(np.ceil(duration * pixels_per_second))

    # Recortar audio a la longitud exacta
    total_samples_needed = num_pixels * int(samples_per_pixel)
    audio_array = audio_array[:total_samples_needed]

    # Reorganizar en chunks
    if audio_array.shape[0] < total_samples_needed:
        # Si no alcanza, relleno con ceros
        audio_array = np.pad(audio_array, (0, total_samples_needed - audio_array.shape[0]))

    y = audio_array.reshape(num_pixels, -1)

    # Calcular el pico absoluto por chunk
    peaks = np.max(np.abs(y), axis=1).tolist()

    return peaks