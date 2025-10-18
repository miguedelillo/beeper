import sounddevice as sd
import numpy as np

def beep(freq=440, duration=0.1):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    sd.play(wave, sr)
    sd.wait()

def callback(indata: np.ndarray, outdata: np.ndarray, frames: int,
         time: CData, status: CallbackFlags) -> None:
    t = np.arange(frames) / 44000
    wave = np.sin(2 * np.pi * 440 * t)
    outdata[:, 0] = wave  # canal izquierdo
    outdata[:, 1] = wave  # canal derecho
    self.phase = (self.phase + frames) % self.fs
    
def constant_beep(freq=440):
    sd.OutputStream(
        channels=2,
        samplerate=44100,
        callback=callback,
    ).stream.start()

if __name__ == "__main__":
    beep()
