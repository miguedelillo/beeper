import sounddevice as sd
import numpy as np

class Beeper():
    def __init__(self, freq=440, fs=44100):
        self.phase = 0            # fase en muestras
        self.fs = fs
        self.freq = freq
        self.target_freq = freq

    def get_callback(self):
        # OutputStream callback signature: callback(outdata, frames, time, status)
        def callback(outdata: np.ndarray, frames: int, time, status) -> None:
        # genera ángulos acumulando fase correctamente
            delta_phase = 2 * np.pi * self.target_freq / self.fs  # incremento por muestra
            angles = self.phase + delta_phase * np.arange(frames)  # fase acumulada
            wave = np.sin(angles).astype('float32')
    
            # estéreo
            outdata[:, 0] = wave
            outdata[:, 1] = wave
    
            # actualizar fase
            self.phase = angles[-1] + delta_phase  # preparar para el próximo bloque
            self.freq = self.target_freq  # opcional, mantiene freq actual
        return callback

    def constant_beep(self, freq=None, samplerate=None):
        """
        Inicia y devuelve un OutputStream que genera un beep continuo.
        El llamador debe guardar el stream y pararlo/cerrarlo cuando corresponda.
        Cambiar self.freq mientras el stream está activo modifica la frecuencia en tiempo real.
        """
        if freq is not None:
            self.freq = freq
        if samplerate is not None:
            self.fs = samplerate

        stream = sd.OutputStream(
            channels=2,
            samplerate=self.fs,
            callback=self.get_callback(),
            dtype='float32'
        )
        stream.start()
        return stream

def beep(freq=440, duration=0.1):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t).astype('float32')
    sd.play(wave, sr)
    sd.wait()

if __name__ == "__main__":
    beep()
