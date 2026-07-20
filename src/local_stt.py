import io
import time
import tempfile
import soundfile as sf
import numpy as np
from typing import Optional, Callable

class LocalSpeechEngine:
    """100% Offline On-Device Speech Recognition using Faster-Whisper."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback
        self.model = None
        self._is_loading = False

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[LocalSTT] {message}")

    def load_model(self, model_name: str = "tiny") -> bool:
        """Loads the Faster-Whisper local model asynchronously into memory."""
        if self.model is not None:
            return True

        if self._is_loading:
            return False

        self._is_loading = True
        try:
            from faster_whisper import WhisperModel
            self.log(f"🧠 กำลังโหลดระบบแปลภาษาในเครื่อง 100% Offline (Faster-Whisper {model_name})...")
            # Load model on CPU with int8 quantization for ultra-fast performance
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
            self.log("✅ โหลดระบบประมวลผลแปลภาษาในเครื่อง (100% Offline Local STT) สำเร็จ!")
            self._is_loading = False
            return True
        except Exception as e:
            self.log(f"⚠️ ไม่สามารถโหลด Local Whisper: {e}")
            self._is_loading = False
            return False

    def transcribe_audio_data(self, audio_data) -> Optional[str]:
        """Transcribes sr.AudioData using the local on-device Whisper model."""
        if self.model is None:
            # Try to load if not already loaded
            if not self.load_model():
                return None

        try:
            # Get raw WAV bytes from AudioData
            raw_wav = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            fp = io.BytesIO(raw_wav)
            y, sr_val = sf.read(fp)

            if len(y) == 0:
                return None

            if y.ndim > 1:
                y = np.mean(y, axis=1)

            y = y.astype(np.float32)

            segments, _ = self.model.transcribe(
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
