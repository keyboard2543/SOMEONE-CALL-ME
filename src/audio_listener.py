import threading
import time
import queue
import speech_recognition as sr
from typing import List, Optional, Callable, Dict
from src.acoustic_matcher import AcousticMatcher

class AudioListener:
    """Listens continuously using a Dual Engine (Acoustic Waveform Pattern + STT Dictation)."""

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

        # Acoustic Waveform Feature Matcher (TTS Reference + MFCC + DTW)
        self.acoustic_matcher = AcousticMatcher(log_callback=self.log)

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
        """Checks if any configured keyword is found in the text."""
        text_lower = text.lower().strip()
        for kw in self.config.keywords:
            kw_clean = kw.lower().strip()
            if kw_clean and kw_clean in text_lower:
                return kw
        return None

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
        """Callback invoked immediately when background recorder captures a phrase."""
        if not self._stop_event.is_set():
            self.audio_queue.put(audio)

    def _process_queue_loop(self) -> None:
        """Worker thread processing captured audio chunks using Dual Engine."""
        while not self._stop_event.is_set():
            try:
                audio = self.audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self.update_status("🟡 กำลังประมวลผลรูปแบบเสียง...")

            # --- Engine 1: Acoustic Waveform MFCC+DTW Matcher ---
            matched_by_acoustic = False
            try:
                raw_wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
                ac_result = self.acoustic_matcher.match_audio(raw_wav, threshold=65.0)
                if ac_result:
                    matched_kw, score = ac_result
                    self.log(f"🎵 [Acoustic Waveform Match] พบรูปคลื่นเสียงคล้ายคำว่า '{matched_kw}' (ความเหมือน {score}%)")
                    self.notifier.trigger_alert(matched_kw, f"รูปคลื่นเสียงคล้ายคำว่า '{matched_kw}' ({score}%)")
                    matched_by_acoustic = True
            except Exception as e:
                pass

            # --- Engine 2: Google Speech-To-Text Dictation Matcher ---
            if not matched_by_acoustic:
                try:
                    text = self.recognizer.recognize_google(audio, language=self.config.language)
                    self.log(f"🗣️ ได้ยิน: '{text}'")

                    matched_kw = self.match_keyword(text)
                    if matched_kw:
                        self.notifier.trigger_alert(matched_kw, text)
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    self.log(f"⚠️ ไม่สามารถเชื่อมต่อระบบแปลงเสียง Google: {e}")
                except Exception as e:
                    if not self._stop_event.is_set():
                        self.log(f"⚠️ เกิดข้อผิดพลาดในการประมวลผลเสียง: {e}")

            self.audio_queue.task_done()
            if self.is_listening and self.audio_queue.empty():
                self.update_status("🟢 กำลังฟังเสียงภาษาไทยอย่างต่อเนื่อง...")

    def start_listening(self) -> bool:
        """Starts continuous non-blocking background listening."""
        if self.is_listening:
            return False

        mic_index = self.config.mic_index
        mic_name = f"Device #{mic_index}" if mic_index is not None else "Default Microphone"

        self.log(f"🎙️ กำลังเปิดใช้งานไมโครโฟน ({mic_name})...")
        self.update_status("กำลังปรับตั้งค่าเสียงรบกวนรอบข้าง...")

        # Generate / update acoustic TTS templates for keywords
        self.acoustic_matcher.update_keywords(self.config.keywords)

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

        self.log("🟢 เริ่มต้นการฟังเสียงภาษาไทยอย่างต่อเนื่อง (Continuous Listening)...")
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
