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
        self.show_settings_requested = False

        # Setup System Tray
        self.icon = None
        self.setup_tray()
        
        # Enable High-DPI awareness once at startup
        self.enable_dpi_awareness()

    def enable_dpi_awareness(self):
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def setup_tray(self):
        image_path = resource_path("icon.png")
        image = Image.open(image_path)
        menu = pystray.Menu(
            pystray.MenuItem("Set API Key", self.request_settings),
            pystray.MenuItem("Exit", self.on_quit)
        )
        self.icon = pystray.Icon("FlashSTT", image, "Flash STT (Ctrl+Alt)", menu)

    def request_settings(self, icon=None, item=None):
        self.show_settings_requested = True

    def _open_settings_window(self):
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("Flash STT Settings")
        root.geometry("400x220")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        
        # Set window icon
        try:
            icon_path = resource_path("icon.ico")
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not set window icon: {e}")

        # Modern styling
        root.configure(bg="#1e1e1e")
        style_font = ("Segoe UI", 10)
        title_font = ("Segoe UI Semibold", 12)

        # Layout
        tk.Label(root, text="Gemini API Configuration", font=title_font, 
                 bg="#1e1e1e", fg="#ffffff", pady=20).pack()
        
        tk.Label(root, text="Enter your Gemini API Key:", font=style_font, 
                 bg="#1e1e1e", fg="#cccccc").pack(pady=5)
        
        current_key = os.getenv("GEMINI_API_KEY", "")
        key_entry = tk.Entry(root, width=40, font=style_font, 
                                  bg="#333333", fg="#ffffff", insertbackground="white",
                                  relief="flat", borderwidth=1)
        key_entry.insert(0, current_key)
        key_entry.pack(pady=10, padx=20)
        key_entry.focus_set()

        def save():
            new_key = key_entry.get().strip()
            if new_key:
                self.save_api_key(new_key)
                self.transcriber.update_client(new_key)
                messagebox.showinfo("Success", "API Key updated successfully!", parent=root)
                root.destroy()
            else:
                messagebox.showwarning("Warning", "API Key cannot be empty.", parent=root)

        def cancel():
            root.destroy()

        btn_frame = tk.Frame(root, bg="#1e1e1e")
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="Save Key", command=save, 
                  width=12, font=style_font, bg="#0078d4", fg="white", 
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Cancel", command=cancel, 
                  width=12, font=style_font, bg="#333333", fg="white",
                  relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=5)

        root.protocol("WM_DELETE_WINDOW", cancel)
        root.lift()
        root.focus_force()
        root.mainloop()

    def save_api_key(self, key):
        print(f"Saving API Key to {env_path}...")
        # Simplistic way to update .env. for a more robust app, use a dedicated lib or parser
        # Here we just read and replace or append.
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        lines.append(f"GEMINI_API_KEY={key}\n")
                        found = True
                    else:
                        lines.append(line)
        
        if not found:
            lines.append(f"GEMINI_API_KEY={key}\n")
            
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Force reload in current process
        load_dotenv(env_path, override=True)

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
        
        # Start system tray icon in a background thread
        # This is necessary so the main thread can handle the tkinter window
        threading.Thread(target=self.icon.run, daemon=True).start()
        
        # Main thread loop to handle UI requests
        try:
            while self.running:
                if self.show_settings_requested:
                    self._open_settings_window()
                    self.show_settings_requested = False
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.on_quit()

if __name__ == "__main__":
    app = FlashSTTApp()
    app.run()
