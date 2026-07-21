import threading
import queue
import speech_recognition as sr
from typing import List, Optional, Callable, Dict
from difflib import SequenceMatcher

class AudioListener:
    """Listens continuously using single-engine Google Speech-To-Text (STT) Keyword Recognition."""

    def __init__(self, config_manager, notifier, log_callback: Optional[Callable[[str], None]] = None, status_callback: Optional[Callable[[str], None]] = None):
        self.config = config_manager
        self.notifier = notifier
        self.log_callback = log_callback
        self.status_callback = status_callback
        
        self.recognizer = sr.Recognizer()
        # Tune recognition sensitivity & thresholds for complete phrase capture
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.1
        self.recognizer.non_speaking_duration = 0.5
        self.recognizer.dynamic_energy_threshold = False

        self.is_listening = False
        self.audio_queue: queue.Queue = queue.Queue()
        self._stop_bg_listener: Optional[Callable] = None
        self._worker_thread: Optional[threading.Thread] = None
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
        """Checks if any configured keyword is found in the transcribed text (exact substring or fuzzy match)."""
        text_lower = text.lower().strip()

        for kw in self.config.keywords:
            kw_clean = kw.lower().strip()
            if not kw_clean:
                continue

            # 1. Exact Substring Match
            if kw_clean in text_lower:
                return kw

            # 2. Fuzzy Ratio Match for slight phonetic variations / suffixes
            kw_len = len(kw_clean)
            for i in range(0, max(1, len(text_lower) - kw_len + 2)):
                sub = text_lower[i:i + kw_len + 2]
                ratio = SequenceMatcher(None, kw_clean, sub).ratio()
                if ratio >= 0.70:
                    return kw
        return None

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
        """Callback invoked immediately when background recorder captures a phrase."""
        if not self._stop_event.is_set():
            self.audio_queue.put(audio)

    def _process_queue_loop(self) -> None:
        """Worker thread processing captured audio chunks using Single-Engine Google Speech-To-Text."""
        while not self._stop_event.is_set():
            try:
                audio = self.audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self.update_status("🟢 กำลังฟังเสียงอย่างต่อเนื่อง (⚡ กำลังวิเคราะห์สัญญาณเสียง...)")

            try:
                # Primary & Only Engine: Google Speech Recognition
                text_transcript = self.recognizer.recognize_google(audio, language=self.config.language)
                self.log(f"🗣️ ได้ยิน: '{text_transcript}'")

                matched_kw = self.match_keyword(text_transcript)
                if matched_kw:
                    self.notifier.trigger_alert(matched_kw, text_transcript)
            except sr.UnknownValueError:
                # Speech was faint or unintelligible
                pass
            except sr.RequestError as e:
                self.log(f"⚠️ ไม่สามารถเชื่อมต่อระบบ Google STT: {e}")
            except Exception as e:
                if not self._stop_event.is_set():
                    self.log(f"⚠️ เกิดข้อผิดพลาดในการประมวลผลเสียง: {e}")

            self.audio_queue.task_done()
            if self.is_listening and self.audio_queue.empty():
                self.update_status("🟢 กำลังฟังเสียงภาษาไทยอย่างต่อเนื่อง (ไมโครโฟนเปิดอยู่ตลอดเวลา)...")

    def start_listening(self) -> bool:
        """Starts continuous non-blocking background listening."""
        if self.is_listening:
            return False

        mic_index = self.config.mic_index
        mic_name = f"Device #{mic_index}" if mic_index is not None else "Default Microphone"

        self.log(f"🎙️ กำลังเปิดใช้งานไมโครโฟน ({mic_name})...")
        self.update_status("กำลังปรับตั้งค่าเสียงรบกวนรอบข้าง...")

        try:
            mic = sr.Microphone(device_index=mic_index)
            with mic as source:
                target_threshold = max(30, self.config.energy_threshold)
                self.recognizer.energy_threshold = target_threshold
                self.recognizer.dynamic_energy_threshold = False
                self.log(f"🎚️ ปรับระดับความไวรับเสียงคงที่ Energy Threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            self.log(f"❌ ไม่สามารถเปิดไมโครโฟนได้: {e}")
            self.update_status("เกิดข้อผิดพลาดในการเปิดไมโครโฟน")
            return False

        self._stop_event.clear()
        self.is_listening = True

        # Clear existing queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start continuous background audio recorder with 10s phrase limit
        self._stop_bg_listener = self.recognizer.listen_in_background(
            mic, 
            self._audio_callback, 
            phrase_time_limit=10.0
        )

        # Start async worker thread for speech recognition
        self._worker_thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self._worker_thread.start()

        self.log("🟢 เริ่มต้นการฟังเสียงภาษาไทยอย่างต่อเนื่อง (Google Speech-To-Text)...")
        self.update_status("🟢 กำลังฟังเสียงภาษาไทยอย่างต่อเนื่อง...")
        return True

    def stop_listening(self) -> bool:
        """Stops continuous background listening."""
        if not self.is_listening:
            return False

        self.update_status("กำลังหยุดการฟังเสียง...")
        self._stop_event.set()

        if self._stop_bg_listener:
            try:
                self._stop_bg_listener(wait_for_stop=False)
            except Exception:
                pass
            self._stop_bg_listener = None

        self.is_listening = False
        self.log("🔴 หยุดทำงานการฟังเสียงเรียบร้อยแล้ว")
        self.update_status("🔴 หยุดการทำงาน")
        return True
