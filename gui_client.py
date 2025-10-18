# client_gui.py
import asyncio
import json
import threading
import tkinter as tk
import websockets

from beepercontroller import WebSocketSoundController

SERVER_URI = "ws://localhost:8765"


class GUIClient:
    def __init__(self, root):
        self.root = root
        self.root.title("🎶 Cliente de Sonido")

        self.ws = None
        self.loop = None
        self.connected = False

        # controlador (usa WebSocketSoundController para desacoplar GUI y transporte)
        self.controller = WebSocketSoundController()

        # Interfaz
        self.status_label = tk.Label(root, text="Desconectado", fg="red")
        self.status_label.pack(pady=10)

        tk.Button(root, text="Conectar", command=self.connect).pack(pady=5)
        tk.Button(root, text="Play", command=self.controller.start).pack(pady=5)
        tk.Button(root, text="Stop", command=self.controller.stop).pack(pady=5)
        tk.Button(root, text="Subir frecuencia", command=self.controller.freq_up).pack(pady=5)
        tk.Button(root, text="Bajar frecuencia", command=self.controller.freq_down).pack(pady=5)

    def connect(self):
        """Inicia un hilo que mantiene la conexión WebSocket."""
        threading.Thread(target=self._run_ws, daemon=True).start()
        self.controller.connect()

    def send_action(self, action):
        """Envia un mensaje JSON al servidor (fallback, no usado si se usa controller)."""
        if self.ws and self.connected and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps({"action": action})), self.loop
            )
        else:
            print("⚠️ No conectado al servidor.")

    def _run_ws(self):
        """Hilo que ejecuta el event loop asyncio."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._ws_main())

    async def _ws_main(self):
        try:
            async with websockets.connect(SERVER_URI) as ws:
                self.ws = ws
                # Attach transport so controller can send actions
                self.controller.attach_transport(ws, asyncio.get_event_loop())

                self.connected = True
                # update UI (tkinter calls from background may be unsafe but kept as original)
                self.status_label.config(text="Conectado", fg="green")
                print("✅ Conectado al servidor WebSocket")

                async for message in ws:
                    data = json.loads(message)
                    print(f"🎵 Mensaje recibido: {data}")
        except Exception as e:
            print(f"❌ Error en conexión: {e}")
        finally:
            self.connected = False
            self.controller.disconnect()
            self.status_label.config(text="Desconectado", fg="red")


if __name__ == "__main__":
    root = tk.Tk()
    app = GUIClient(root)
    root.mainloop()
