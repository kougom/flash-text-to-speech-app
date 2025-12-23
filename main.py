import os
import time
import threading
from pynput import keyboard
from PIL import Image
import pystray
from execution.audio_recorder import AudioRecorder
from execution.transcribe_and_type import Transcriber

import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FlashSTTApp:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        # .tmp should stay in the current working directory of the user, not the bundled temp folder
        self.output_dir = os.path.join(os.getcwd(), ".tmp")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.output_path = os.path.join(self.output_dir, "last_recording.wav")
        
        # Track state of Ctrl and Alt
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.is_recording = False
        self.running = True

        # Setup System Tray
        self.icon = None
        self.setup_tray()

    def setup_tray(self):
        image_path = resource_path("icon.png")
        image = Image.open(image_path)
        menu = pystray.Menu(
            pystray.MenuItem("Exit", self.on_quit)
        )
        self.icon = pystray.Icon("FlashSTT", image, "Flash STT (Ctrl+Alt)", menu)

    def on_press(self, key):
        if not self.running:
            return False
            
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.ctrl_pressed = True
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self.alt_pressed = True

        if self.ctrl_pressed and self.alt_pressed and not self.is_recording:
            print("\n>>> Shortcut detected! Hold to record...")
            self.recorder.start_recording()
            self.is_recording = True

    def on_release(self, key):
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.ctrl_pressed = False
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self.alt_pressed = False

        if key == keyboard.Key.esc:
            # We'll keep Esc as an option to quit if the window is focused
            self.on_quit()
            return False

        # If either key is released and we were recording, stop and process
        if self.is_recording and (not self.ctrl_pressed or not self.alt_pressed):
            print(">>> Release detected. Processing...")
            self.recorder.stop_recording(self.output_path)
            self.is_recording = False
            
            # Use a thread for transcription to avoid blocking the listener
            threading.Thread(target=self.transcriber.transcribe_and_type, args=(self.output_path,), daemon=True).start()

    def on_quit(self, icon=None, item=None):
        print("\nExiting Flash STT App...")
        self.running = False
        if self.icon:
            self.icon.stop()
        os._exit(0) # Force exit to stop all threads

    def run_listener(self):
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def run(self):
        print("Flash STT App is running in the system tray.")
        print("Shortcut: Hold Ctrl + Alt to record voice.")
        print("Release to transcribe and type at cursor.")
        
        # Start keyboard listener in a background thread
        listener_thread = threading.Thread(target=self.run_listener, daemon=True)
        listener_thread.start()
        
        # Run the system tray icon in the main thread
        self.icon.run()

if __name__ == "__main__":
    app = FlashSTTApp()
    app.run()
