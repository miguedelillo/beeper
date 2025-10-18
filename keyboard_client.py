import threading
import json
import time
from typing import Set

import numpy as np
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.figure as mplfig
from beepercontrollers import WebSocketSoundController
from pynput import keyboard, mouse
# servidor por defecto ahora lo maneja el controller
# SERVER_URI = "ws://localhost:8765"


SEMITONE_RATIO = 2 ** (1 / 12)
DEFAULT_FREQ = 440.0
SR = 44100

# map de teclas -> acción del servidor
KEY_ACTION_MAP = {
    "s": "start",      # start beep
    "e": "stop",       # stop beep
    "up": "freq_up",   # flecha arriba
    "down": "freq_down",
    "x": "freq_up",  # flecha arriba
    "z": "freq_down",
    }# flecha abajo

class KeyboardGuiClient:
    """
    Cliente con interfaz gráfica que:
    - usa WebSocketSoundController.connect() para conectarse al servidor
    - escucha teclas globales con pynput (acción al presionar)
    - muestra la frecuencia actual (estimada/local)
    - plotea en tiempo real una onda sintética con la misma frecuencia
    - muestra posición del mouse en tiempo real (global)
    """

    def __init__(self, server_uri: str = "ws://localhost:8765"):
        self.controller = WebSocketSoundController(uri=server_uri)
        self.pressed: Set[str] = set()
        self._listener = None
        self._mouse_listener = None

        # local state shown in GUI (keeps approximate frequency shown)
        self.current_freq = DEFAULT_FREQ
        self.playing = False

        # plotting state
        self.fs = SR
        self.phase = 0.0  # in samples
        self.plot_len = 2048  # samples to plot
        self.plot_dt = 1 / 30  # update interval in seconds (~30 FPS)

        # build GUI (must be in main thread)
        self.root = tk.Tk()
        self.root.title("Keyboard Sound Controller")
        self._build_ui()

        # ensure clean shutdown when window closed
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(frm)
        top.pack(fill=tk.X)

        self.status_label = ttk.Label(top, text="Desconectado", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.freq_label = ttk.Label(top, text=f"Freq: {self.current_freq:.1f} Hz")
        self.freq_label.pack(side=tk.LEFT, padx=(0, 10))

        # mouse position label
        self.mouse_label = ttk.Label(top, text="Mouse: -, -")
        self.mouse_label.pack(side=tk.LEFT, padx=(0, 10))

        # control buttons for convenience
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Conectar", command=self._on_connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Desconectar", command=self._on_disconnect).pack(side=tk.LEFT, padx=4)

        # matplotlib figure
        fig = mplfig.Figure(figsize=(6, 2.5), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.set_xlim(0, self.plot_len)
        self.ax.set_yticks([-1, 0, 1])
        self.ax.set_xticks([])

        self.line_x = np.arange(self.plot_len)
        self.line_y = np.zeros(self.plot_len, dtype=np.float32)
        self.line, = self.ax.plot(self.line_x, self.line_y, lw=1)

        canvas = FigureCanvasTkAgg(fig, master=frm)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=8)
        self.canvas = canvas

        help_text = (
            "Teclas: s=start, x=stop, ↑/↓ o u/d para subir/bajar frecuencia.\n"
            "La acción se envía al presionar. Se permiten múltiples teclas."
        )
        ttk.Label(frm, text=help_text).pack(anchor=tk.W, pady=(0, 6))

    def _on_connect(self):
        self.status_label.config(text="Conectando...", foreground="orange")
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        self.controller.connect()
        # controller.connect() is synchronous (waits until connected or timeout)
        self.status_label.after(0, lambda: self.status_label.config(text="Conectado", foreground="green"))
        # start keyboard listener once connected
        if self._listener is None:
            self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener.start()
        # start mouse listener once connected
        if self._mouse_listener is None:
            self._mouse_listener = mouse.Listener(on_move=self._on_mouse_move)
            self._mouse_listener.start()
        # start plotting loop
        self.root.after(int(self.plot_dt * 1000), self._update_plot)

    def _on_disconnect(self):
        self.controller.disconnect()
        self.status_label.config(text="Desconectado", foreground="red")
        # stop listener if running
        if self._listener:
            self._listener.stop()
            self._listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

    def _on_window_close(self):
        # ensure listeners and controller stop before closing
        self._on_disconnect()
        self.root.destroy()

    def _normalize_key(self, key) -> str:
        if hasattr(key, "char") and key.char is not None:
            return key.char.lower()
        s = str(key).lower()
        if s.startswith("key."):
            return s.split(".", 1)[1].strip("'")
        return s.strip("'")

    def _on_press(self, key):
        name = self._normalize_key(key)
        if name in self.pressed:
            return
        self.pressed.add(name)

        action = KEY_ACTION_MAP.get(name)
        if action:
            # execute local update first (so GUI shows immediate change)
            if action == "start":
                self.playing = True
            elif action == "stop":
                self.playing = False
            elif action == "freq_up":
                self.current_freq *= SEMITONE_RATIO
            elif action == "freq_down":
                self.current_freq /= SEMITONE_RATIO

            # update displayed freq
            self.freq_label.after(0, lambda: self.freq_label.config(text=f"Freq: {self.current_freq:.1f} Hz"))

            # send action to server via controller
            try:
                getattr(self.controller, action)()
            except Exception as e:
                print("Error enviando acción:", e)
            print(f"Key press -> {name} => action: {action}")
        else:
            print(f"Key press -> {name} (no mapeada)")

    def _on_release(self, key):
        name = self._normalize_key(key)
        if name in self.pressed:
            self.pressed.discard(name)

    def _on_mouse_move(self, x, y):
        # called from pynput thread; update label via Tk event loop
        try:
            self.mouse_label.after(0, lambda: self.mouse_label.config(text=f"Mouse: {int(x)}, {int(y)}"))
        except Exception:
            pass

    def _update_plot(self):
        # generate waveform chunk to display using current_freq and phase continuity
        n = self.plot_len
        idx = np.arange(n)
        angles = 2 * np.pi * (self.current_freq / self.fs) * (idx + self.phase)
        wave = np.sin(angles).astype(np.float32)

        # update phase
        self.phase = (self.phase + n) % self.fs

        # if not playing, fade to zero for visual feedback
        if not self.playing:
            wave *= 0.0

        self.line.set_ydata(wave)
        self.canvas.draw_idle()

        # schedule next update
        self.root.after(int(self.plot_dt * 1000), self._update_plot)

    def run(self):
        # show initial mapping
        print("KEY ACTION MAP:", KEY_ACTION_MAP)
        # start GUI mainloop (Tk must run in main thread)
        self.root.mainloop()


if __name__ == "__main__":
    client = KeyboardGuiClient()
    print(KEY_ACTION_MAP)
    client.run()