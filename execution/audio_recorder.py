import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import threading
import os

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = []
        self._stop_event = threading.Event()
        self._stream = None

    def _callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.recording.append(indata.copy())

    def start_recording(self):
        self.recording = []
        self._stop_event.clear()
        self._stream = sd.InputStream(samplerate=self.sample_rate,
                                    channels=self.channels,
                                    callback=self._callback)
        self._stream.start()
        print("Recording started...")

    def stop_recording(self, output_path):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            
        if self.recording:
            audio_data = np.concatenate(self.recording, axis=0)
            write(output_path, self.sample_rate, audio_data)
            print(f"Recording saved to {output_path}")
            return output_path
        return None

if __name__ == "__main__":
    # Test recording
    import time
    recorder = AudioRecorder()
    recorder.start_recording()
    time.sleep(3)
    recorder.stop_recording(".tmp/test_output.wav")
