"""User alerts: beep, Windows toast, and TTS."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AlertConfig

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, alert: AlertConfig) -> None:
        self.alert = alert
        self._lock = threading.Lock()

    def notify(self, matched_text: str, score: float, target: str) -> None:
        """Fire alerts without blocking the listener long."""
        msg = self.alert.message.format(
            matched=matched_text or target,
            score=f"{score:.0f}",
            target=target,
        )
        title = self.alert.title

        def _run() -> None:
            with self._lock:
                log.info("ALERT: %s | %s (score=%.1f)", title, msg, score)
                if self.alert.toast:
                    self._toast(title, msg)
                if self.alert.sound:
                    self._beep(self.alert.beep_count)
                if self.alert.speak:
                    self._speak(self.alert.speak_text)

        threading.Thread(target=_run, name="alert", daemon=True).start()

    def _toast(self, title: str, message: str) -> None:
        try:
            from winotify import Notification, audio

            toast = Notification(
                app_id="Someone Call Me",
                title=title,
                msg=message,
                duration="short",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except Exception as e:
            log.warning("toast ล้มเหลว: %s", e)
            try:
                # fallback: PowerShell balloon-ish via .NET is heavy; just print
                print(f"\n*** {title} — {message} ***\n")
            except Exception:
                pass

    def _beep(self, count: int) -> None:
        try:
            import winsound

            for i in range(max(1, count)):
                # frequency, duration_ms — เสียงสูงชัด
                winsound.Beep(1200 + (i % 3) * 200, 220)
                time.sleep(0.08)
        except Exception as e:
            log.warning("beep ล้มเหลว: %s", e)
            try:
                print("\a" * max(1, count), end="", flush=True)
            except Exception:
                pass

    def _speak(self, text: str) -> None:
        if not text:
            return
        try:
            import subprocess

            # Windows built-in SAPI via PowerShell — no extra deps
            safe = text.replace("'", "''")
            ps = (
                "Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = 1; $s.Speak('{safe}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            log.warning("TTS ล้มเหลว: %s", e)
