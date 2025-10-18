import asyncio
import threading
import json
import sys
from typing import Set

import websockets
from pynput import keyboard

from beepercontroller import WebSocketSoundController

SERVER_URI = "ws://localhost:8765"

# map de teclas -> acción del servidor
KEY_ACTION_MAP = {
    "s": "start",      # start beep
    "x": "stop",       # stop beep
    "up": "freq_up",   # flecha arriba
    "down": "freq_down",# flecha abajo
    "u": "freq_up",    # alternativa
    "d": "freq_down",  # alternativa
}

class KeyboardClient:
    def __init__(self, server_uri: str = SERVER_URI):
        self.server_uri = server_uri
        self.loop = None
        self.ws = None
        self.controller = WebSocketSoundController()
        self.pressed: Set[str] = set()  # evita envíos repetidos mientras la tecla esté presionada
        self._listener = None
        self._running = False

    def start(self):
        """Inicia event loop websocket en hilo y el listener de teclado."""
        self._running = True
        t = threading.Thread(target=self._run_ws_loop, daemon=True)
        t.start()
        # start keyboard listener in main thread (pynput uses its own threads)
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        print("Keyboard client started. Keys: s=start, x=stop, up/down or u/d to change freq. Ctrl-C to exit.")
        try:
            # keep main thread alive while listener is running
            while self._running:
                self._listener.wait()
        except KeyboardInterrupt:
            print("Exiting...")
            self.stop()

    def stop(self):
        self._running = False
        if self._listener:
            self._listener.stop()
        # try to disconnect websocket nicely
        try:
            if self.ws and self.loop:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop).result(timeout=2)
        except Exception:
            pass
        self.controller.disconnect()
        print("Stopped.")

    def _run_ws_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._ws_main())

    async def _ws_main(self):
        try:
            async with websockets.connect(self.server_uri) as ws:
                self.ws = ws
                # attach transport using the running loop
                self.controller.attach_transport(ws, asyncio.get_event_loop())
                print("Connected to server", self.server_uri)
                # keep reading messages (optional)
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        data = msg
                    print("Server ->", data)
        except Exception as e:
            print("WebSocket error:", e)
        finally:
            self.controller.disconnect()
            self.ws = None
            print("WebSocket connection closed.")

    def _normalize_key(self, key) -> str:
        """Devuelve nombre simple de la tecla (ej: 'a', 'up')."""
        if hasattr(key, "char") and key.char is not None:
            return key.char.lower()
        # str(Key.up) => 'Key.up'
        s = str(key).lower()
        if s.startswith("key."):
            return s.split(".", 1)[1].strip("'")
        return s.strip("'")

    def _on_press(self, key):
        name = self._normalize_key(key)
        if name in self.pressed:
            return  # ya enviada mientras está presionada
        self.pressed.add(name)

        action = KEY_ACTION_MAP.get(name)
        if action:
            try:
                getattr(self.controller, action)()
            except Exception as e:
                print("Error enviando acción:", e)
            print(f"Key press -> {name} => action: {action}")
        else:
            # sin map, impresión informativa
            print(f"Key press -> {name} (no mapeada)")

    def _on_release(self, key):
        name = self._normalize_key(key)
        if name in self.pressed:
            self.pressed.discard(name)


if __name__ == "__main__":
    client = KeyboardClient()
    print(KEY_ACTION_MAP)
    client.start()