"""Main listen loop: mic → STT → fuzzy name match → alert."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import AppConfig, load_config
from .listener import MicListener, list_microphones
from .matcher import NameMatcher
from .notifier import Notifier
from .recognizer import SpeechRecognizer

log = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def print_mics() -> None:
    mics = list_microphones()
    if not mics:
        print("ไม่พบไมโครโฟน")
        return
    print("รายการไมโครโฟน:")
    for m in mics:
        print(f"  [{m['index']}] {m['name']}  ({m['hostapi']}, ch={m['channels']})")


def run(config_path: Path | str | None = None, verbose: bool = False) -> None:
    setup_logging(verbose)
    cfg: AppConfig = load_config(config_path)

    targets = cfg.all_targets
    if not targets:
        raise SystemExit("กรุณาใส่ชื่อใน config.yaml → names")

    log.info("กำลังฟังชื่อ: %s", ", ".join(targets))
    log.info(
        "sensitivity=%s | language=%s | model=%s | cooldown=%ss",
        cfg.sensitivity,
        cfg.language,
        cfg.whisper_model,
        cfg.cooldown_seconds,
    )

    matcher = NameMatcher(targets, sensitivity=cfg.sensitivity)
    notifier = Notifier(cfg.alert)
    recognizer = SpeechRecognizer(
        model_size=cfg.whisper_model,
        language=cfg.language,
    )
    # preload model so first speech is not delayed
    recognizer.load()

    listener = MicListener(
        device=cfg.microphone_index,
        chunk_seconds=cfg.chunk_seconds,
        energy_threshold=cfg.energy_threshold,
    )

    last_alert = 0.0
    log.info("เริ่มฟัง... (กด Ctrl+C เพื่อหยุด)")

    try:
        for audio, energy in listener.stream_chunks():
            # ข้ามช่วงเงียบมาก ๆ เพื่อประหยัด CPU
            if energy < cfg.energy_threshold:
                continue

            try:
                text = recognizer.transcribe(audio)
            except Exception as e:
                log.warning("STT error: %s", e)
                continue

            if not text:
                continue

            result = matcher.score_text(text)
            log.info(
                "ได้ยิน: %r | score=%.1f | target=%s | %s%s",
                text,
                result.score,
                result.best_target or "-",
                result.reason,
                " ★ MATCH" if result.matched else "",
            )

            if not result.matched:
                continue

            now = time.monotonic()
            if now - last_alert < cfg.cooldown_seconds:
                log.debug("cooldown — ข้ามการแจ้งเตือน")
                continue

            last_alert = now
            notifier.notify(
                matched_text=text,
                score=result.score,
                target=result.best_target,
            )
    except KeyboardInterrupt:
        log.info("หยุดฟังแล้ว")
