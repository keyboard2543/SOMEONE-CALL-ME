"""Load and validate configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class AlertConfig:
    sound: bool = True
    beep_count: int = 4
    toast: bool = True
    title: str = "มีคนเรียกคุณ!"
    message: str = "ได้ยินชื่อคล้าย ๆ ว่า: {matched}"
    speak: bool = True
    speak_text: str = "มีคนเรียกคุณครับ"


@dataclass
class AppConfig:
    names: list[str] = field(default_factory=lambda: ["สมชาย"])
    aliases: list[str] = field(default_factory=list)
    sensitivity: float = 68.0
    cooldown_seconds: float = 8.0
    language: str = "th"
    whisper_model: str = "base"
    microphone_index: int | None = None
    chunk_seconds: float = 2.5
    energy_threshold: float = 0.012
    alert: AlertConfig = field(default_factory=AlertConfig)

    @property
    def all_targets(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for n in self.names + self.aliases:
            key = n.strip()
            if key and key.lower() not in seen:
                seen.add(key.lower())
                out.append(key)
        return out


def _alert_from_dict(data: dict[str, Any] | None) -> AlertConfig:
    if not data:
        return AlertConfig()
    return AlertConfig(
        sound=bool(data.get("sound", True)),
        beep_count=int(data.get("beep_count", 4)),
        toast=bool(data.get("toast", True)),
        title=str(data.get("title", "มีคนเรียกคุณ!")),
        message=str(data.get("message", "ได้ยินชื่อคล้าย ๆ ว่า: {matched}")),
        speak=bool(data.get("speak", True)),
        speak_text=str(data.get("speak_text", "มีคนเรียกคุณครับ")),
    )


def load_config(path: Path | str | None = None) -> AppConfig:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ config: {cfg_path}")

    with cfg_path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    names = raw.get("names") or ["สมชาย"]
    if isinstance(names, str):
        names = [names]

    aliases = raw.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]

    mic = raw.get("microphone_index", None)
    if mic is not None:
        mic = int(mic)

    return AppConfig(
        names=[str(n).strip() for n in names if str(n).strip()],
        aliases=[str(a).strip() for a in aliases if str(a).strip()],
        sensitivity=float(raw.get("sensitivity", 68)),
        cooldown_seconds=float(raw.get("cooldown_seconds", 8)),
        language=str(raw.get("language", "th")).lower(),
        whisper_model=str(raw.get("whisper_model", "base")),
        microphone_index=mic,
        chunk_seconds=float(raw.get("chunk_seconds", 2.5)),
        energy_threshold=float(raw.get("energy_threshold", 0.012)),
        alert=_alert_from_dict(raw.get("alert")),
    )
