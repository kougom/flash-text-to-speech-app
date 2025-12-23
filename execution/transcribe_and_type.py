import os
import time
from google import genai
from google.genai import types
from pynput.keyboard import Controller
from dotenv import load_dotenv

import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Look for .env in the bundled resources first, then in current working directory
env_path = resource_path(".env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.getcwd(), ".env")

load_dotenv(env_path)

class Transcriber:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY not found in .env")
        self.client = genai.Client(api_key=api_key)
        self.keyboard = Controller()

    def transcribe_and_type(self, audio_path):
        try:
            print(f"Uploading {audio_path}...")
            # Upload the file
            myfile = self.client.files.upload(file=audio_path)
            
            # Wait for file to become active if needed (usually fast for small audio)
            # but for safety:
            while myfile.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(1)
                myfile = self.client.files.get(name=myfile.name)

            print("\nTranscribing...")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp", # Latest flash model
                contents=[
                    "Please provide an accurate transcript of this audio. Return ONLY the transcribed text, no other comments.",
                    myfile
                ]
            )
            
            transcript = response.text.strip()
            print(f"Result: {transcript}")
            
            if transcript:
                self.type_text(transcript)
            
            # Clean up uploaded file from Gemini (optional but good practice)
            # self.client.files.delete(name=myfile.name)
            
        except Exception as e:
            print(f"Error during transcription: {e}")

    def type_text(self, text):
        print("Typing...")
        # Small delay to ensure the user hasn't accidentally switched focus
        time.sleep(0.5)
        self.keyboard.type(text)

if __name__ == "__main__":
    # Test script
    transcriber = Transcriber()
    # Assuming test_output.wav exists from recorder test
    if os.path.exists(".tmp/test_output.wav"):
        transcriber.transcribe_and_type(".tmp/test_output.wav")
    else:
        print("No test audio found. Run audio_recorder.py first.")
