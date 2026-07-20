# -*- coding: utf-8 -*-
import json
import os
from typing import List, Optional, Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "keywords": ["\u0e2a\u0e21\u0e0a\u0e32\u0e22", "\u0e21\u0e35\u0e04\u0e19\u0e40\u0e23\u0e35\u0e22\u0e01", "\u0e0a\u0e48\u0e27\u0e22\u0e14\u0e49\u0e27\u0e22"],
    "enable_notification": True,
    "enable_tts": True,
    "tts_phrase": "\u0e21\u0e35\u0e04\u0e19\u0e40\u0e23\u0e35\u0e22\u0e01\u0e0a\u0e37\u0e48\u0e2d\u0e04\u0e38\u0e13\u0e04\u0e48\u0e30",
    "mic_index": None,
    "cooldown_seconds": 5.0,
    "energy_threshold": 150,
    "language": "th-TH"
}

class ConfigManager:
    """Manages application settings stored in a local JSON file."""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from JSON file or returns defaults if missing/corrupt."""
        if not os.path.exists(self.config_file):
            config = DEFAULT_CONFIG.copy()
            self.save_config(config)
            return config
        
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(loaded)
                return config
        except Exception as e:
            print(f"Error loading config file '{self.config_file}': {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Saves current or provided configuration to JSON file."""
        if config is not None:
            self.config = config
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config file '{self.config_file}': {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()

    @property
    def keywords(self) -> List[str]:
        return self.config.get("keywords", DEFAULT_CONFIG["keywords"])

    @keywords.setter
    def keywords(self, val: List[str]) -> None:
        self.config["keywords"] = val
        self.save_config()

    @property
    def enable_notification(self) -> bool:
        return self.config.get("enable_notification", True)

    @enable_notification.setter
    def enable_notification(self, val: bool) -> None:
        self.config["enable_notification"] = val
        self.save_config()

    @property
    def enable_tts(self) -> bool:
        return self.config.get("enable_tts", True)

    @enable_tts.setter
    def enable_tts(self, val: bool) -> None:
        self.config["enable_tts"] = val
        self.save_config()

    @property
    def tts_phrase(self) -> str:
        return self.config.get("tts_phrase", "\u0e21\u0e35\u0e04\u0e19\u0e40\u0e23\u0e35\u0e22\u0e01\u0e0a\u0e37\u0e48\u0e2d\u0e04\u0e38\u0e13\u0e04\u0e48\u0e32")

    @tts_phrase.setter
    def tts_phrase(self, val: str) -> None:
        self.config["tts_phrase"] = val
        self.save_config()

    @property
    def mic_index(self) -> Optional[int]:
        return self.config.get("mic_index", None)

    @mic_index.setter
    def mic_index(self, val: Optional[int]) -> None:
        self.config["mic_index"] = val
        self.save_config()

    @property
    def cooldown_seconds(self) -> float:
        return float(self.config.get("cooldown_seconds", 5.0))

    @cooldown_seconds.setter
    def cooldown_seconds(self, val: float) -> None:
        self.config["cooldown_seconds"] = float(val)
        self.save_config()

    @property
    def language(self) -> str:
        return self.config.get("language", "th-TH")

    @language.setter
    def language(self, val: str) -> None:
        self.config["language"] = val
        self.save_config()

    @property
    def energy_threshold(self) -> int:
        return int(self.config.get("energy_threshold", 300))

    @energy_threshold.setter
    def energy_threshold(self, val: int) -> None:
        self.config["energy_threshold"] = int(val)
        self.save_config()

