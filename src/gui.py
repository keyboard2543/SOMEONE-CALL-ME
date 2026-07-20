import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import datetime
from typing import List, Dict

class AppGUI:
    """Main Tkinter GUI interface for Someone Call Me."""

    def __init__(self, root: tk.Tk, config_manager, notifier, audio_listener):
        self.root = root
        self.config = config_manager
        self.notifier = notifier
        self.audio_listener = audio_listener

        # Attach callbacks to notifier and listener
        self.notifier.log_callback = self.log_message
        self.audio_listener.log_callback = self.log_message
        self.audio_listener.status_callback = self.update_status

        self.root.title("Someone Call Me - ระบบตรวจจับคำพูดและแจ้งเตือน")
        self.root.geometry("820x680")
        self.root.minsize(750, 600)

        # Style configuration
        self.setup_styles()

        # Build UI layout
        self.create_widgets()

        # Load configuration into UI fields
        self.load_settings_to_ui()

        # Initial log entry
        self.log_message("👋 ยินดีต้อนรับสู่โปรแกรม Someone Call Me (ระบบตรวจจับคำพูดและแจ้งเตือน)")
        self.log_message("💡 คำแนะนำ: เพิ่มคำสำคัญที่คุณต้องการให้ดักฟัง เช่น ชื่อของคุณ แล้วกด 'เริ่มฟังเสียง'")

    def setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        # Color Palette
        bg_dark = "#1e1e2e"
        card_bg = "#2b2b3b"
        input_bg = "#191923"
        fg_text = "#f8f8f2"
        accent_green = "#50fa7b"

        self.root.configure(bg=bg_dark)

        # Global OptionDB for Combobox Popdown Listbox & Text Widgets
        self.root.option_add("*TCombobox*Listbox.background", input_bg)
        self.root.option_add("*TCombobox*Listbox.foreground", fg_text)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#6272a4")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        style.configure(".", background=bg_dark, foreground=fg_text, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=card_bg, relief="flat")
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#bd93f9", background=bg_dark)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#6272a4", background=bg_dark)
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"), foreground=accent_green, background=card_bg)

        # Checkbutton Styling
        style.configure("TCheckbutton", background=card_bg, foreground=fg_text)
        style.map("TCheckbutton", background=[("active", card_bg)], foreground=[("active", "#ffffff")])

        # Entry Styling (Input Boxes)
        style.configure(
            "TEntry",
            fieldbackground=input_bg,
            foreground="#ffffff",
            insertcolor="#ffffff",
            bordercolor="#6272a4",
            lightcolor="#6272a4",
            darkcolor="#6272a4"
        )

        # Combobox Styling (Dropdown Menu)
        style.configure(
            "TCombobox",
            fieldbackground=input_bg,
            foreground="#ffffff",
            background=card_bg,
            arrowcolor="#ffffff",
            bordercolor="#6272a4"
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", input_bg), ("focus", input_bg)],
            foreground=[("readonly", "#ffffff"), ("focus", "#ffffff")],
            selectbackground=[("readonly", "#6272a4")],
            selectforeground=[("readonly", "#ffffff")]
        )

        # Spinbox Styling
        style.configure(
            "TSpinbox",
            fieldbackground=input_bg,
            foreground="#ffffff",
            arrowcolor="#ffffff",
            bordercolor="#6272a4"
        )
        style.map(
            "TSpinbox",
            fieldbackground=[("readonly", input_bg), ("focus", input_bg)],
            foreground=[("readonly", "#ffffff"), ("focus", "#ffffff")]
        )
        
        # Buttons Styling
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Start.TButton", background="#50fa7b", foreground="#1e1e2e")
        style.map("Start.TButton", background=[("active", "#40c964")])
        
        style.configure("Stop.TButton", background="#ff5555", foreground="#ffffff")
        style.map("Stop.TButton", background=[("active", "#ff3333")])

        style.configure("Test.TButton", background="#8be9fd", foreground="#1e1e2e")
        style.map("Test.TButton", background=[("active", "#64d3ec")])

    def create_widgets(self) -> None:
        # Main Container
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header Title
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="🎙️ Someone Call Me", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(header_frame, text="ระบบดักฟังคำพูดภาษาไทย แจ้งเตือน Windows และส่งเสียงพูดเมื่อมีคนเรียก", style="SubHeader.TLabel").pack(anchor=tk.W)

        # Top Section: Status & Controls
        status_card = ttk.Frame(main_container, style="Card.TFrame", padding=12)
        status_card.pack(fill=tk.X, pady=(0, 12))

        status_left = ttk.Frame(status_card, style="Card.TFrame")
        status_left.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        ttk.Label(status_left, text="สถานะระบบ:", font=("Segoe UI", 10, "bold"), background="#2b2b3b").pack(anchor=tk.W)
        self.lbl_status = ttk.Label(status_left, text="🔴 หยุดการทำงาน", style="Status.TLabel")
        self.lbl_status.pack(anchor=tk.W, pady=(2, 0))

        status_right = ttk.Frame(status_card, style="Card.TFrame")
        status_right.pack(side=tk.RIGHT)

        self.btn_start = ttk.Button(status_right, text="▶️ เริ่มฟังเสียง", style="Start.TButton", command=self.on_start_click)
        self.btn_start.pack(side=tk.LEFT, padx=4)

        self.btn_stop = ttk.Button(status_right, text="⏹️ หยุดฟังเสียง", style="Stop.TButton", command=self.on_stop_click, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        self.btn_test = ttk.Button(status_right, text="🧪 ทดสอบแจ้งเตือน", style="Test.TButton", command=self.on_test_click)
        self.btn_test.pack(side=tk.LEFT, padx=4)

        # Middle Section: Paned window (Keywords on Left, Settings on Right)
        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 12))

        # --- Left Panel: Keywords ---
        kw_card = ttk.Frame(middle_frame, style="Card.TFrame", padding=10)
        kw_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        ttk.Label(kw_card, text="🏷️ คำสำคัญที่ดักฟัง (Keywords)", font=("Segoe UI", 11, "bold"), background="#2b2b3b").pack(anchor=tk.W, pady=(0, 6))

        # Listbox for Keywords
        list_frame = ttk.Frame(kw_card, style="Card.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.kw_listbox = tk.Listbox(
            list_frame, 
            height=6, 
            bg="#191923", 
            fg="#f8f8f2", 
            selectbackground="#6272a4", 
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            relief="flat",
            bd=1
        )
        self.kw_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.kw_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.kw_listbox.config(yscrollcommand=scrollbar.set)

        # Entry & Add/Remove buttons
        add_frame = ttk.Frame(kw_card, style="Card.TFrame")
        add_frame.pack(fill=tk.X)

        self.entry_kw = tk.Entry(
            add_frame,
            font=("Segoe UI", 10),
            bg="#191923",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#6272a4",
            selectforeground="#ffffff",
            bd=1,
            relief="solid"
        )
        self.entry_kw.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.entry_kw.bind("<Return>", lambda e: self.on_add_keyword())

        btn_add = ttk.Button(add_frame, text="➕ เพิ่ม", command=self.on_add_keyword)
        btn_add.pack(side=tk.LEFT, padx=(0, 4))

        btn_del = ttk.Button(add_frame, text="❌ ลบที่เลือก", command=self.on_remove_keyword)
        btn_del.pack(side=tk.LEFT)

        # --- Right Panel: Settings ---
        settings_card = ttk.Frame(middle_frame, style="Card.TFrame", padding=10)
        settings_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        ttk.Label(settings_card, text="⚙️ การตั้งค่าระบบแจ้งเตือน", font=("Segoe UI", 11, "bold"), background="#2b2b3b").pack(anchor=tk.W, pady=(0, 6))

        # Checkboxes
        self.var_notif = tk.BooleanVar(value=True)
        chk_notif = ttk.Checkbutton(settings_card, text="🔔 เปิดการแจ้งเตือน Windows Toast", variable=self.var_notif, command=self.save_ui_settings)
        chk_notif.pack(anchor=tk.W, pady=2)

        self.var_tts = tk.BooleanVar(value=True)
        chk_tts = ttk.Checkbutton(settings_card, text="🔊 เปิดเสียงพูดภาษาไทย (Thai TTS)", variable=self.var_tts, command=self.save_ui_settings)
        chk_tts.pack(anchor=tk.W, pady=2)

        # TTS Phrase input
        ttk.Label(settings_card, text="ข้อความเสียงพูดภาษาไทย:", background="#2b2b3b").pack(anchor=tk.W, pady=(4, 1))
        self.entry_tts = tk.Entry(
            settings_card,
            font=("Segoe UI", 10),
            bg="#191923",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#6272a4",
            selectforeground="#ffffff",
            bd=1,
            relief="solid"
        )
        self.entry_tts.pack(fill=tk.X, pady=(0, 6))
        self.entry_tts.bind("<FocusOut>", lambda e: self.save_ui_settings())
        self.entry_tts.bind("<Return>", lambda e: self.save_ui_settings())

        # Microphone dropdown
        ttk.Label(settings_card, text="เลือกไมโครโฟน (Microphone):", background="#2b2b3b").pack(anchor=tk.W, pady=(4, 1))
        self.cbo_mic = ttk.Combobox(settings_card, state="readonly", font=("Segoe UI", 9))
        self.cbo_mic.pack(fill=tk.X, pady=(0, 6))
        self.cbo_mic.bind("<<ComboboxSelected>>", lambda e: self.save_ui_settings())

        # Sensitivity Scale (ความไวรับเสียง)
        sens_frame = ttk.Frame(settings_card, style="Card.TFrame")
        sens_frame.pack(fill=tk.X, pady=(4, 4))
        ttk.Label(sens_frame, text="🎚️ ความไวรับเสียง (Sensitivity Threshold):", background="#2b2b3b").pack(anchor=tk.W)

        sens_inner = ttk.Frame(sens_frame, style="Card.TFrame")
        sens_inner.pack(fill=tk.X, pady=(2, 0))

        self.sld_sens = tk.Scale(
            sens_inner,
            from_=50,
            to=600,
            orient=tk.HORIZONTAL,
            bg="#2b2b3b",
            fg="#ffffff",
            troughcolor="#191923",
            activebackground="#50fa7b",
            highlightthickness=0,
            bd=0,
            showvalue=False,
            command=self.on_sens_change
        )
        self.sld_sens.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.lbl_sens_val = ttk.Label(sens_inner, text="150 (ไวสูง-เสียงไกล)", font=("Segoe UI", 9, "bold"), foreground="#50fa7b", background="#2b2b3b")
        self.lbl_sens_val.pack(side=tk.RIGHT)

        # Cooldown entry
        cooldown_frame = ttk.Frame(settings_card, style="Card.TFrame")
        cooldown_frame.pack(fill=tk.X, pady=(2, 0))
        ttk.Label(cooldown_frame, text="ระยะเวลา Cooldown (วินาที):", background="#2b2b3b").pack(side=tk.LEFT)
        self.spn_cooldown = tk.Spinbox(
            cooldown_frame,
            from_=1.0,
            to=60.0,
            increment=1.0,
            width=5,
            font=("Segoe UI", 9),
            bg="#191923",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#6272a4",
            selectforeground="#ffffff",
            bd=1,
            relief="solid"
        )
        self.spn_cooldown.pack(side=tk.LEFT, padx=6)
        self.spn_cooldown.bind("<FocusOut>", lambda e: self.save_ui_settings())

        # Bottom Section: Log Box
        log_card = ttk.Frame(main_container, style="Card.TFrame", padding=10)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_header = ttk.Frame(log_card, style="Card.TFrame")
        log_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(log_header, text="📋 ประวัติและบันทึกการทำงาน (Live Log)", font=("Segoe UI", 10, "bold"), background="#2b2b3b").pack(side=tk.LEFT)
        
        btn_clear_log = ttk.Button(log_header, text="🧹 ล้างบันทึก", command=self.clear_log)
        btn_clear_log.pack(side=tk.RIGHT)

        self.txt_log = scrolledtext.ScrolledText(
            log_card,
            height=10,
            bg="#14141d",
            fg="#f8f8f2",
            font=("Consolas", 9),
            relief="flat",
            bd=1
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def load_settings_to_ui(self) -> None:
        # Load keywords into listbox
        self.kw_listbox.delete(0, tk.END)
        for kw in self.config.keywords:
            self.kw_listbox.insert(tk.END, kw)

        # Load settings checkboxes and entries
        self.var_notif.set(self.config.enable_notification)
        self.var_tts.set(self.config.enable_tts)
        
        self.entry_tts.delete(0, tk.END)
        self.entry_tts.insert(0, self.config.tts_phrase)

        self.spn_cooldown.delete(0, tk.END)
        self.spn_cooldown.insert(0, str(self.config.cooldown_seconds))

        current_sens = self.config.energy_threshold
        self.sld_sens.set(current_sens)
        self.on_sens_change(str(current_sens))

        # Populate microphone combobox
        mics = self.audio_listener.get_microphone_list()
        mic_values = [" [Default] ไมโครโฟนเริ่มต้นของระบบ"]
        self.mic_map = {0: None}

        selected_index = 0
        for i, m in enumerate(mics, start=1):
            mic_values.append(m["name"])
            self.mic_map[i] = m["index"]
            if self.config.mic_index == m["index"]:
                selected_index = i

        self.cbo_mic["values"] = mic_values
        self.cbo_mic.current(selected_index)

    def on_sens_change(self, val_str: str) -> None:
        try:
            val = int(float(val_str))
            self.config.energy_threshold = val
            if val <= 100:
                desc = f"{val} (ไวสูงสุด-ดักฟังเสียงไกล)"
            elif val <= 200:
                desc = f"{val} (ไวสูง-เสียงไกล/แผ่วเบา)"
            elif val <= 350:
                desc = f"{val} (ปานกลาง-เสียงทั่วไป)"
            else:
                desc = f"{val} (ไวต่ำ-ต้องพูดใกล้ๆ)"
            self.lbl_sens_val.config(text=desc)
        except ValueError:
            pass

    def save_ui_settings(self) -> None:
        # Save keywords
        keywords = list(self.kw_listbox.get(0, tk.END))
        self.config.keywords = keywords
        self.config.enable_notification = self.var_notif.get()
        self.config.enable_tts = self.var_tts.get()
        self.config.tts_phrase = self.entry_tts.get().strip() or "มีคนเรียกชื่อคุณค่ะ"

        try:
            cooldown_val = float(self.spn_cooldown.get())
            self.config.cooldown_seconds = max(1.0, cooldown_val)
        except ValueError:
            pass

        selected_cbo_idx = self.cbo_mic.current()
        self.config.mic_index = self.mic_map.get(selected_cbo_idx, None)

    def on_add_keyword(self) -> None:
        new_kw = self.entry_kw.get().strip()
        if not new_kw:
            return
        
        existing = list(self.kw_listbox.get(0, tk.END))
        if new_kw in existing:
            messagebox.showinfo("แจ้งเตือน", f"คำว่า '{new_kw}' มีอยู่ในรายการแล้ว")
            return

        self.kw_listbox.insert(tk.END, new_kw)
        self.entry_kw.delete(0, tk.END)
        self.save_ui_settings()
        self.log_message(f"➕ เพิ่มคำสำคัญใหม่: '{new_kw}'")

    def on_remove_keyword(self) -> None:
        selected_idx = self.kw_listbox.curselection()
        if not selected_idx:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกคำสำคัญที่ต้องการลบในรายการ")
            return

        idx = selected_idx[0]
        removed_kw = self.kw_listbox.get(idx)
        self.kw_listbox.delete(idx)
        self.save_ui_settings()
        self.log_message(f"❌ ลบคำสำคัญ: '{removed_kw}'")

    def on_start_click(self) -> None:
        self.save_ui_settings()
        if not self.config.keywords:
            messagebox.showwarning("คำเตือน", "กรุณาเพิ่มคำสำคัญอย่างน้อย 1 คำก่อนเริ่มใช้งาน")
            return

        success = self.audio_listener.start_listening()
        if success:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)

    def on_stop_click(self) -> None:
        self.audio_listener.stop_listening()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def on_test_click(self) -> None:
        self.save_ui_settings()
        kw = self.config.keywords[0] if self.config.keywords else "ทดสอบระบบ"
        self.log_message("🧪 กำลังทดสอบระบบแจ้งเตือนและเสียงพูดภาษาไทย...")
        self.notifier.trigger_alert(kw, f"ทดสอบการได้ยินคำว่า '{kw}'", force=True)

    def update_status(self, status_text: str) -> None:
        self.root.after(0, lambda: self._apply_status_update(status_text))

    def _apply_status_update(self, status_text: str) -> None:
        self.lbl_status.config(text=status_text)
        if "🟢" in status_text:
            self.lbl_status.config(foreground="#50fa7b")
        elif "🟡" in status_text:
            self.lbl_status.config(foreground="#f1fa8c")
        else:
            self.lbl_status.config(foreground="#ff5555")

    def log_message(self, message: str) -> None:
        self.root.after(0, lambda: self._apply_log(message))

    def _apply_log(self, message: str) -> None:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now_str}] {message}\n"
        self.txt_log.insert(tk.END, formatted)
        self.txt_log.see(tk.END)

    def clear_log(self) -> None:
        self.txt_log.delete("1.0", tk.END)
        self.log_message("🧹 ล้างบันทึกการทำงานเรียบร้อยแล้ว")
