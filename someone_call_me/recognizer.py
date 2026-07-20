"""Speech-to-text via faster-whisper (offline)."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# language codes for Whisper
_LANG_MAP = {
    "th": "th",
    "thai": "th",
    "en": "en",
    "english": "en",
    "auto": None,
}


class SpeechRecognizer:
    def __init__(self, model_size: str = "base", language: str = "th") -> None:
        self.model_size = model_size
        self.language = _LANG_MAP.get(language.lower(), language if language != "auto" else None)
        self._model: Any = None

    def load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        log.info("กำลังโหลด Whisper model '%s' (ครั้งแรกอาจช้า)...", self.model_size)
        # CPU int8 ทำงานได้ดีบนเครื่องทั่วไป
        self._model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type="int8",
        )
        log.info("โหลดโมเดลเสร็จแล้ว")

    def transcribe(self, audio_f32: np.ndarray, sample_rate: int = 16000) -> str:
        """
        audio_f32: mono float32 in range [-1, 1]
        """
        self.load()
        assert self._model is not None

        if audio_f32 is None or len(audio_f32) == 0:
            return ""

        # ensure float32 mono
        audio = np.asarray(audio_f32, dtype=np.float32).reshape(-1)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 1e-6:
            return ""

        # soft normalize ช่วยเสียงเบา/ไกล
        if peak < 0.35:
            gain = min(0.9 / peak, 12.0)
            audio = np.clip(audio * gain, -1.0, 1.0)

        segments, _info = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
            condition_on_previous_text=False,
            # เปิด temperature fallback เมื่อเสียงไม่ชัด
            temperature=[0.0, 0.2, 0.4],
            no_speech_threshold=0.45,
            compression_ratio_threshold=2.4,
        )

        parts: list[str] = []
        for seg in segments:
            t = (seg.text or "").strip()
            if t:
                parts.append(t)
        return " ".join(parts).strip()
