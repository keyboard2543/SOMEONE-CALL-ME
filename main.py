import sys
import os
import tkinter as tk

# Ensure src module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.notifier import Notifier
from src.audio_listener import AudioListener
from src.gui import AppGUI

def main():
    config = ConfigManager("config.json")
    notifier = Notifier(config)
    listener = AudioListener(config, notifier)

    root = tk.Tk()
    app = AppGUI(root, config, notifier, listener)

    def on_closing():
        if listener.is_listening:
            listener.stop_listening()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
