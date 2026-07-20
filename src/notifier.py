import os
import time
import tempfile
import threading
from typing import Optional, Callable
from winotify import Notification
from gtts import gTTS
import pygame

class Notifier:
    """Handles Windows notifications and Thai Text-To-Speech audio alerts."""

    def __init__(self, config_manager, log_callback: Optional[Callable[[str], None]] = None):
        self.config = config_manager
        self.log_callback = log_callback
        self.last_trigger_time: float = 0.0
        self._mixer_initialized = False
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[Notifier] {message}")

    def _init_mixer(self) -> bool:
        if not self._mixer_initialized:
            try:
                pygame.mixer.init()
                self._mixer_initialized = True
            except Exception as e:
                self.log(f"⚠️ ไม่สามารถเริ่มระบบเล่นเสียงได้: {e}")
                return False
        return True

    def speak_thai(self, text: str) -> None:
        """Generates and plays Thai TTS speech asynchronously."""
        def run_tts():
            with self._lock:
                if not self._init_mixer():
                    return
                
                temp_path = None
                try:
                    # Generate TTS mp3 using gTTS
                    tts = gTTS(text=text, lang="th")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                        temp_path = temp_file.name
                    
                    tts.save(temp_path)

                    # Play sound via pygame
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    pygame.mixer.music.unload()
                except Exception as e:
                    self.log(f"⚠️ เกิดข้อผิดพลาดในการเล่นเสียงพูด: {e}")
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

        threading.Thread(target=run_tts, daemon=True).start()

    def show_windows_toast(self, matched_keyword: str, full_transcript: str) -> None:
        """Displays a Windows 10/11 Toast Notification."""
        try:
            toast = Notification(
                app_id="Someone Call Me",
                title=f"🔔 ตรวจพบคำว่า '{matched_keyword}'!",
                msg=f"ได้ยินคำว่า: {full_transcript}",
                duration="short"
            )
            toast.show()
        except Exception as e:
            self.log(f"⚠️ ไม่สามารถแสดง Windows Notification ได้: {e}")

    def trigger_alert(self, matched_keyword: str, full_transcript: str, force: bool = False) -> bool:
        """Triggers alerts if cooldown period has passed."""
        current_time = time.time()
        cooldown = self.config.cooldown_seconds

        if not force and (current_time - self.last_trigger_time < cooldown):
            remaining = round(cooldown - (current_time - self.last_trigger_time), 1)
            self.log(f"⏳ อยู่ในช่วง Cooldown (เหลือ {remaining} วินาที) ข้ามการแจ้งเตือน...")
            return False

        self.last_trigger_time = current_time
        timestamp_str = time.strftime("%H:%M:%S")

        self.log(f"🎯 [{timestamp_str}] ตรวจจับคำว่า '{matched_keyword}' ในประโยค: '{full_transcript}'")

        # Windows Notification
        if self.config.enable_notification:
            self.show_windows_toast(matched_keyword, full_transcript)
            self.log("🔔 ส่งการแจ้งเตือน Windows Toast แล้ว")

        # Thai Speech
        if self.config.enable_tts:
            phrase = self.config.tts_phrase or "มีคนเรียกชื่อคุณค่ะ"
            self.speak_thai(phrase)
            self.log(f"🔊 กำลังเล่นเสียงพูดภาษาไทย: '{phrase}'")

        return True
