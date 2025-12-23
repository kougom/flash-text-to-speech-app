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
            pystray.MenuItem("Set API Key", self.show_settings),
            pystray.MenuItem("Exit", self.on_quit)
        )
        self.icon = pystray.Icon("FlashSTT", image, "Flash STT (Ctrl+Alt)", menu)

    def show_settings(self, icon=None, item=None):
        import tkinter as tk
        from tkinter import messagebox
        import ctypes
        
        # Enable High-DPI awareness on Windows for a sharp UI
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        class FlashSettings(tk.Toplevel):
            def __init__(self, parent, current_key, save_callback, cancel_callback):
                super().__init__(parent)
                self.title("Flash STT Settings")
                self.geometry("400x200")
                self.resizable(False, False)
                self.save_callback = save_callback
                self.cancel_callback = cancel_callback
                
                # Set window icon
                try:
                    icon_path = resource_path("icon.ico")
                    self.iconbitmap(icon_path)
                except Exception as e:
                    print(f"Could not set window icon: {e}")

                # Modern styling
                self.configure(bg="#1e1e1e")
                style_font = ("Segoe UI", 10)
                title_font = ("Segoe UI Semibold", 12)

                # Layout
                tk.Label(self, text="Gemini API Configuration", font=title_font, 
                         bg="#1e1e1e", fg="#ffffff", pady=20).pack()
                
                tk.Label(self, text="Enter your Gemini API Key:", font=style_font, 
                         bg="#1e1e1e", fg="#cccccc").pack(pady=5)
                
                self.key_entry = tk.Entry(self, width=40, font=style_font, 
                                          bg="#333333", fg="#ffffff", insertbackground="white",
                                          relief="flat", borderwidth=1)
                self.key_entry.insert(0, current_key)
                self.key_entry.pack(pady=10, padx=20)
                self.key_entry.focus_set()

                btn_frame = tk.Frame(self, bg="#1e1e1e")
                btn_frame.pack(pady=10)

                tk.Button(btn_frame, text="Save Key", command=self.save, 
                          width=12, font=style_font, bg="#0078d4", fg="white", 
                          activebackground="#005a9e", activeforeground="white",
                          relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=5)
                
                tk.Button(btn_frame, text="Cancel", command=self.cancel_callback, 
                          width=12, font=style_font, bg="#333333", fg="white",
                          activebackground="#444444", activeforeground="white",
                          relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=5)

            def save(self):
                new_key = self.key_entry.get().strip()
                if new_key:
                    self.save_callback(new_key)
                else:
                    messagebox.showwarning("Warning", "API Key cannot be empty.")

        # Main window for the settings app
        root = tk.Tk()
        root.withdraw() # Hide main root
        
        current_key = os.getenv("GEMINI_API_KEY", "")
        
        def on_save(new_key):
            self.save_api_key(new_key)
            self.transcriber.update_client(new_key)
            messagebox.showinfo("Success", "API Key updated successfully!")
            root.quit()

        def on_cancel():
            root.quit()

        settings_win = FlashSettings(root, current_key, on_save, on_cancel)
        settings_win.protocol("WM_DELETE_WINDOW", on_cancel)
        
        # Proper event loop to prevent system lag
        root.mainloop()
        root.destroy()

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
        
        # Run the system tray icon in the main thread
        self.icon.run()

if __name__ == "__main__":
    app = FlashSTTApp()
    app.run()
