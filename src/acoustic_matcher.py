# -*- coding: utf-8 -*-
import io
import time
import threading
import numpy as np
import soundfile as sf
import librosa
from gtts import gTTS
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from typing import List, Dict, Optional, Tuple, Any

class AcousticMatcher:
    """Matches live microphone audio against TTS-generated keyword acoustic templates using MFCC and DTW."""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.templates: Dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[AcousticMatcher] {message}")

    def update_keywords(self, keywords: List[str]) -> None:
        """Asynchronously updates cached acoustic templates for the given keywords."""
        def worker():
            with self._lock:
                new_templates = {}
                for kw in keywords:
                    kw_clean = kw.strip()
                    if not kw_clean:
                        continue
                    if kw_clean in self.templates:
                        new_templates[kw_clean] = self.templates[kw_clean]
                    else:
                        mfcc = self._generate_tts_mfcc(kw_clean)
                        if mfcc is not None:
                            new_templates[kw_clean] = mfcc
                            self.log(f"🔊 สร้าง Acoustic Template สำหรับคำว่า '{kw_clean}' สำเร็จ")
                self.templates = new_templates

        threading.Thread(target=worker, daemon=True).start()

    def _generate_tts_mfcc(self, keyword: str) -> Optional[np.ndarray]:
        """Synthesizes TTS reference audio for a keyword and extracts normalized MFCC features."""
        try:
            tts = gTTS(text=keyword, lang="th")
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)

            y, sr_val = sf.read(fp)
            if len(y) == 0:
                return None

            # Convert to mono if stereo
            if y.ndim > 1:
                y = np.mean(y, axis=1)

            # Resample to 16kHz if needed
            if sr_val != 16000:
                y = librosa.resample(y, orig_sr=sr_val, target_sr=16000)
                sr_val = 16000

            # Extract 13 MFCC features
            mfcc = librosa.feature.mfcc(y=y, sr=sr_val, n_mfcc=13)
            # Z-score normalization
            mfcc = (mfcc - np.mean(mfcc)) / (np.std(mfcc) + 1e-8)
            return mfcc
        except Exception as e:
            self.log(f"⚠️ ไม่สามารถสร้าง Template เสียงสำหรับ '{keyword}': {e}")
            return None

    def match_audio(self, raw_wav_bytes: bytes, sample_rate: int = 16000, threshold: float = 78.0) -> Optional[Tuple[str, float]]:
        """Compares raw WAV audio bytes against cached TTS templates using Sliding Window DTW."""
        if not self.templates:
            return None

        try:
            # Load WAV bytes into numpy array
            fp = io.BytesIO(raw_wav_bytes)
            y, sr_val = sf.read(fp)

            if len(y) == 0:
                return None

            if y.ndim > 1:
                y = np.mean(y, axis=1)

            # SPEECH ENERGY GATE: Ignore quiet room static below human speech level
            rms = float(np.sqrt(np.mean(y ** 2)))
            if rms < 0.015:
                return None

            if sr_val != 16000:
                y = librosa.resample(y, orig_sr=sr_val, target_sr=16000)
                sr_val = 16000

            # Extract MFCC for microphone audio
            mfcc_mic = librosa.feature.mfcc(y=y, sr=sr_val, n_mfcc=13)
            mfcc_mic = (mfcc_mic - np.mean(mfcc_mic)) / (np.std(mfcc_mic) + 1e-8)
            mic_len = mfcc_mic.shape[1]

            best_match: Optional[str] = None
            highest_score: float = 0.0

            with self._lock:
                for kw, mfcc_ref in self.templates.items():
                    ref_len = mfcc_ref.shape[1]
                    if mic_len < ref_len * 0.6:
                        continue

                    # Sliding window step size
                    step = max(1, ref_len // 4)
                    min_dist = float("inf")

                    for i in range(0, max(1, mic_len - ref_len + 1), step):
                        sub_mic = mfcc_mic[:, i:i + ref_len]
                        dist, _ = fastdtw(mfcc_ref.T, sub_mic.T, dist=euclidean)
                        norm_dist = dist / ref_len
                        if norm_dist < min_dist:
                            min_dist = norm_dist

                    # Calculate Similarity Score (%) tuned for human-like perception
                    score = max(0.0, 100.0 - (min_dist * 28.0))
                    if score > highest_score:
                        highest_score = score
                        best_match = kw

            if best_match and highest_score >= threshold:
                return (best_match, round(highest_score, 1))

        except Exception as e:
            # Fail silently on audio format mismatch
            pass

        return None
