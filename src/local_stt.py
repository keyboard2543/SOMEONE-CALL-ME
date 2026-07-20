import io
import os
import warnings
import numpy as np
import soundfile as sf
import librosa
from typing import Optional, Callable

# Suppress library deprecation warnings for clean console output
warnings.filterwarnings("ignore")

class LocalSpeechEngine:
    """100% Offline On-Device Speech Recognition Engine using PyThaiASR (Wav2Vec2 Thai Model)."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback
        self.use_pythaiasr = False
        self.whisper_model = None
        self._init_engine()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[LocalSTT] {message}")

    def _init_engine(self) -> None:
        """Initializes PyThaiASR AIResearch Wav2Vec2 model for 100% offline Thai processing."""
        try:
            import pythaiasr
            self.use_pythaiasr = True
            self.log("🇹🇭 โหลดโมเดล PyThaiASR (AIResearch Wav2Vec2 Thai Speech Engine) สำเร็จ! (100% Offline)")
        except Exception as e:
            self.log(f"⚠️ ไม่สามารถโหลด PyThaiASR: {e}")
            try:
                from faster_whisper import WhisperModel
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                self.log("🧠 โหลดโมเดล Faster-Whisper (100% Offline Local Engine) สำเร็จ!")
            except Exception:
                pass

    def transcribe_audio_data(self, audio_data) -> Optional[str]:
        """Transcribes sr.AudioData 100% locally using PyThaiASR (Numpy 16kHz + RMS VAD Gate)."""
        try:
            raw_wav = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
            fp = io.BytesIO(raw_wav)
            y, sr_val = sf.read(fp)

            if len(y) == 0:
                return None

            if y.ndim > 1:
                y = np.mean(y, axis=1)

            # SPEECH VAD GATE: Ignore quiet room static to prevent PyThaiASR CTC text garbling
            rms = float(np.sqrt(np.mean(y ** 2)))
            if rms < 0.015:
                return None

            # Resample to 16kHz if needed for Wav2Vec2 PyThaiASR
            if sr_val != 16000:
                y = librosa.resample(y, orig_sr=sr_val, target_sr=16000)
                sr_val = 16000

            y_numpy = y.astype(np.float32)

            # 1. PyThaiASR Specialized Thai Speech Model (Direct Numpy Array Mode)
            if self.use_pythaiasr:
                try:
                    import pythaiasr
                    text = pythaiasr.asr(y_numpy, sampling_rate=16000)
                    if text:
                        text_clean = text.strip()
                        # Filter out CTC noise artifact characters (e.g. 'ทคค', 'มตค')
                        if len(text_clean) > 1 and not all(c in "ทคจนม " for c in text_clean):
                            return text_clean
                except Exception:
                    pass

            # 2. Faster-Whisper Local Model Backup
            if self.whisper_model is not None:
                segments, _ = self.whisper_model.transcribe(
                    y_numpy,
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
