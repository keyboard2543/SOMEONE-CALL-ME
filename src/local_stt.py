import io
import os
import warnings
import numpy as np
import soundfile as sf
from typing import Optional, Callable

# Suppress library deprecation warnings for clean console output
warnings.filterwarnings("ignore")

class LocalSpeechEngine:
    """100% Offline On-Device Speech Recognition Engine using Faster-Whisper."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback
        self.whisper_model = None
        self._init_engine()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[LocalSTT] {message}")

    def _init_engine(self) -> None:
        """Initializes Faster-Whisper for 100% offline local processing on CPU."""
        try:
            from faster_whisper import WhisperModel
            self.log("🧠 กำลังโหลดโมเดลแปลภาษาในเครื่อง (Faster-Whisper 100% Offline)...")
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            self.log("✅ โหลดระบบประมวลผลแปลภาษาในเครื่อง (100% Offline Local STT) สำเร็จ!")
        except Exception as e:
            self.log(f"⚠️ ไม่สามารถโหลด Local STT Engine: {e}")

    def transcribe_audio_data(self, audio_data) -> Optional[str]:
        """Transcribes sr.AudioData 100% locally using Faster-Whisper on CPU."""
        if self.whisper_model is None:
            return None

        try:
            raw_wav = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            fp = io.BytesIO(raw_wav)
            y, sr_val = sf.read(fp)

            if len(y) == 0:
                return None

            if y.ndim > 1:
                y = np.mean(y, axis=1)

            y = y.astype(np.float32)

            segments, _ = self.whisper_model.transcribe(
                y,
                language="th",
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=True
            )

            text_segments = [seg.text for seg in segments]
            full_text = " ".join(text_segments).strip()
            return full_text if full_text else None
        except Exception as e:
            return None
