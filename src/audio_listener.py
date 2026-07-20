import threading
import time
import speech_recognition as sr
from typing import List, Optional, Callable, Dict

class AudioListener:
    """Listens continuously to microphone input and matches target Thai keywords."""

    def __init__(self, config_manager, notifier, log_callback: Optional[Callable[[str], None]] = None, status_callback: Optional[Callable[[str], None]] = None):
        self.config = config_manager
        self.notifier = notifier
        self.log_callback = log_callback
        self.status_callback = status_callback
        
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[Listener] {message}")

    def update_status(self, status: str) -> None:
        if self.status_callback:
            self.status_callback(status)

    @staticmethod
    def get_microphone_list() -> List[Dict[str, int]]:
        """Returns a list of dicts with microphone names and device indices."""
        mics = []
        try:
            mic_names = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(mic_names):
                mics.append({"index": idx, "name": f"[{idx}] {name}"})
        except Exception as e:
            print(f"Error listing microphones: {e}")
        return mics

    def match_keyword(self, text: str) -> Optional[str]:
        """Checks if any configured keyword is found in the text."""
        text_lower = text.lower().strip()
        for kw in self.config.keywords:
            kw_clean = kw.lower().strip()
            if kw_clean and kw_clean in text_lower:
                return kw
        return None

    def _listen_loop(self) -> None:
        mic_index = self.config.mic_index
        mic_name = f"Device #{mic_index}" if mic_index is not None else "Default Microphone"

        self.log(f"🎙️ กำลังเปิดใช้งานไมโครโฟน ({mic_name})...")
        self.update_status("กำลังปรับตั้งค่าเสียงรบกวนรอบข้าง...")

        try:
            mic = sr.Microphone(device_index=mic_index)
            with mic as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                # Ensure minimum energy threshold
                if self.recognizer.energy_threshold < 100:
                    self.recognizer.energy_threshold = 300
        except Exception as e:
            self.log(f"❌ ไม่สามารถเปิดไมโครโฟนได้: {e}")
            self.update_status("เกิดข้อผิดพลาดในการเปิดไมโครโฟน")
            self.is_listening = False
            return

        self.log("🟢 เริ่มต้นการฟังเสียงภาษาไทย (th-TH)...")
        self.update_status("🟢 กำลังฟังเสียงภาษาไทย...")

        while not self._stop_event.is_set():
            try:
                with mic as source:
                    # Listen for audio phrase (timeout=3s, limit=6s per phrase)
                    audio = self.recognizer.listen(source, timeout=2.0, phrase_time_limit=5.0)

                if self._stop_event.is_set():
                    break

                self.update_status("🟡 กำลังประมวลผลคำพูด...")
                try:
                    # Recognize Thai speech
                    text = self.recognizer.recognize_google(audio, language=self.config.language)
                    self.log(f"🗣️ ได้ยิน: '{text}'")

                    # Check for keyword match
                    matched_kw = self.match_keyword(text)
                    if matched_kw:
                        self.notifier.trigger_alert(matched_kw, text)
                        
                except sr.UnknownValueError:
                    # Speech was unintelligible (normal in silence)
                    pass
                except sr.RequestError as e:
                    self.log(f"⚠️ ไม่สามารถเชื่อมต่อระบบแปลงเสียง Google: {e}")
                    time.sleep(1.0)

                self.update_status("🟢 กำลังฟังเสียงภาษาไทย...")

            except sr.WaitTimeoutError:
                # Timeout waiting for speech, continue loop
                pass
            except Exception as e:
                if not self._stop_event.is_set():
                    self.log(f"⚠️ เกิดข้อผิดพลาดในระบบฟังเสียง: {e}")
                    time.sleep(0.5)

        self.log("🔴 หยุดทำงานการฟังเสียงเรียบร้อยแล้ว")
        self.update_status("🔴 หยุดการทำงาน")
        self.is_listening = False

    def start_listening(self) -> bool:
        """Starts background listening thread."""
        if self.is_listening:
            return False

        self._stop_event.clear()
        self.is_listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        return True

    def stop_listening(self) -> bool:
        """Stops background listening thread."""
        if not self.is_listening:
            return False

        self.update_status("กำลังหยุดการฟังเสียง...")
        self._stop_event.set()
        self.is_listening = False
        return True
