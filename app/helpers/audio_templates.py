# app/helpers/audio_templates.py
from typing import List, Dict

REQUIRED_HOURS: List[str] = [
    "1.mp3", "2.mp3", "3.mp3", "4.mp3", "5.mp3", "6.mp3",
    "7.mp3", "8.mp3", "9.mp3", "10.mp3", "11.mp3", "12.mp3",
    "12 AM.mp3", "12 PM.mp3"
]

REQUIRED_MINUTES: List[str] = [f"{i}.mp3" for i in range(60)]  # 0.mp3 a 59.mp3

REQUIRED_CONNECTORS: List[str] = [
    "mañana.mp3", "noche.mp3", "rreloj.mp3", "tarde.mp3"
]

# Diccionario completo para validación
REQUIRED_AUDIO_FILES: Dict[str, List[str]] = {
    "Hours": REQUIRED_HOURS,
    "Minutes": REQUIRED_MINUTES,
    "Connectors": REQUIRED_CONNECTORS
}