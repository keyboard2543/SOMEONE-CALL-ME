import os
import io
import tempfile
import numpy as np
import soundfile as sf
from typing import Optional, Callable

class LocalSpeechEngine:
    """100% Offline On-Device Speech Recognition Engine for Thai Language.
    Supports PyThaiASR (AIResearch Wav2Vec2 Thai Speech Model) and Faster-Whisper.
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback
        self.whisper_model = None
        self.use_pythaiasr = False
        self._init_engine()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[LocalSTT] {message}")

    def _init_engine(self) -> None:
        """Initializes PyThaiASR or Faster-Whisper for 100% offline local processing."""
        try:
            import pythaiasr
            self.use_pythaiasr = True
            self.log("🇹🇭 โหลดโมเดล PyThaiASR (AIResearch Wav2Vec2 Thai Speech Engine) สำเร็จ! (100% Offline)")
        except Exception:
            try:
                from faster_whisper import WhisperModel
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                self.log("🧠 โหลดโมเดล Faster-Whisper (100% Offline Local Engine) สำเร็จ!")
            except Exception as e:
                self.log(f"⚠️ ไม่สามารถโหลด Local STT Engine: {e}")

    def transcribe_audio_data(self, audio_data) -> Optional[str]:
        """Transcribes sr.AudioData using PyThaiASR or Faster-Whisper 100% locally."""
        try:
            raw_wav = audio_data.get_wav_data(convert_rate=16000, convert_width=2)

            # 1. PyThaiASR Specialized Thai Speech Model
            if self.use_pythaiasr:
                try:
                    import pythaiasr
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        tmp_file.write(raw_wav)
                    
                    try:
                        text = pythaiasr.asr(tmp_path)
                        if text:
                            return text.strip()
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                except Exception:
                    pass

            # 2. Faster-Whisper Local Model
            if self.whisper_model is not None:
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

        except Exception:
            pass

        return None
