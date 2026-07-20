"""Microphone capture in overlapping chunks."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1


def list_microphones() -> list[dict[str, Any]]:
    import sounddevice as sd

    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    result: list[dict[str, Any]] = []
    for i, d in enumerate(devices):
        if int(d.get("max_input_channels", 0)) <= 0:
            continue
        api = hostapis[int(d["hostapi"])]["name"] if d.get("hostapi") is not None else "?"
        result.append(
            {
                "index": i,
                "name": d.get("name", f"device-{i}"),
                "hostapi": api,
                "channels": int(d.get("max_input_channels", 0)),
                "default_samplerate": d.get("default_samplerate"),
            }
        )
    return result


def rms_energy(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))


class MicListener:
    """Capture continuous mic audio as float32 mono chunks at 16 kHz."""

    def __init__(
        self,
        device: int | None = None,
        chunk_seconds: float = 2.5,
        energy_threshold: float = 0.012,
    ) -> None:
        self.device = device
        self.chunk_seconds = max(1.0, float(chunk_seconds))
        self.energy_threshold = float(energy_threshold)
        self.sample_rate = SAMPLE_RATE

    def stream_chunks(self) -> Iterator[tuple[np.ndarray, float]]:
        """
        Yields (audio_f32, energy).
        Overlaps ~40% so short names at chunk boundaries still get heard.
        """
        import sounddevice as sd

        chunk_samples = int(self.sample_rate * self.chunk_seconds)
        hop = max(int(chunk_samples * 0.6), self.sample_rate)  # 40% overlap
        buffer = np.zeros(0, dtype=np.float32)

        log.info(
            "เปิดไมโครโฟน (device=%s, chunk=%.1fs, energy>=%.4f)",
            self.device if self.device is not None else "default",
            self.chunk_seconds,
            self.energy_threshold,
        )

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            dtype="float32",
            device=self.device,
            blocksize=int(self.sample_rate * 0.1),
        ) as stream:
            while True:
                frames, _overflowed = stream.read(int(self.sample_rate * 0.2))
                mono = frames.reshape(-1).astype(np.float32, copy=False)
                buffer = np.concatenate([buffer, mono])

                while len(buffer) >= chunk_samples:
                    chunk = buffer[:chunk_samples]
                    buffer = buffer[hop:]
                    energy = rms_energy(chunk)
                    if energy < self.energy_threshold:
                        yield chunk, energy  # still yield; caller may skip STT
                        continue
                    yield chunk, energy
