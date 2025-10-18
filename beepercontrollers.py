from abc import ABC, abstractmethod
import asyncio
import json
from typing import Optional
import threading
import websockets


class BeeperController(ABC):
    """
    Interfaz abstracta para controladores de sonido usados por la GUI.
    Implementar los métodos para integrar diferentes transportes (WS, local, tests...).
    Todos los métodos son síncronos para poder llamarlos desde el hilo de la GUI.
    """

    @abstractmethod
    def connect(self) -> None:
        """Iniciar conexión / recursos necesarios (si aplica)."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Liberar conexión / recursos."""
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        """Iniciar beep continuo en el servidor."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Parar beep continuo en el servidor."""
        raise NotImplementedError

    @abstractmethod
    def freq_up(self) -> None:
        """Incrementar la frecuencia del beep."""
        raise NotImplementedError

    @abstractmethod
    def freq_down(self) -> None:
        """Reducir la frecuencia del beep."""
        raise NotImplementedError


class WebSocketSoundController(BeeperController):
    """
    Implementación que administra internamente la conexión WebSocket en un hilo
    y proporciona métodos síncronos para enviar acciones al servidor.
    """

    def __init__(self, uri: str = "ws://localhost:8765"):
        self._uri = uri
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._connected = threading.Event()

    def attach_transport(self, ws, loop: asyncio.AbstractEventLoop) -> None:
        """Compatibilidad retroactiva (no usada)."""
        self._ws = ws
        self._loop = loop

    def detach_transport(self) -> None:
        self._ws = None
        self._loop = None

    def connect(self) -> None:
        """Inicia hilo + event loop y establece la conexión websocket."""
        if self._thread and self._thread.is_alive():
            return  # ya conectado / en proceso

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            # crear evento en el mismo loop
            self._stop_event = asyncio.Event()
            try:
                loop.run_until_complete(self._ws_main())
            finally:
                # limpieza del loop
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                self._loop = None
                self._stop_event = None
                self._connected.clear()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        # esperar a que la conexión se establezca (o falle) para que connect sea síncrono
        self._connected.wait(timeout=5)

    def disconnect(self) -> None:
        """Cierra la conexión y detiene el hilo/loop."""
        if not self._loop:
            return
        try:
            # señalizar cierre desde el event loop
            self._loop.call_soon_threadsafe(lambda: self._stop_event.set())
        except Exception:
            pass
        # esperar que el hilo termine
        if self._thread:
            self._thread.join(timeout=3)
        self.detach_transport()

    async def _ws_main(self):
        """Corutina que establece la conexión y espera al event para cerrarla."""
        try:
            async with websockets.connect(self._uri) as ws:
                self._ws = ws
                self._connected.set()
                print("WebSocketSoundController: conectado a", self._uri)
                # Mantener la conexión abierta hasta que _stop_event sea seteado
                try:
                    await self._stop_event.wait()
                finally:
                    # opcional: enviar mensaje de cierre si hace falta
                    pass
        except Exception as e:
            print("WebSocketSoundController: error en conexión:", e)
        finally:
            self._ws = None
            print("WebSocketSoundController: desconectado")

    def _send(self, action: str) -> None:
        """Envía acción al servidor de forma segura (no bloqueante)."""
        if not (self._ws and self._loop):
            print(f"⚠️ No transport available to send action '{action}'")
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws.send(json.dumps({"action": action})),
                self._loop
            )
        except Exception as e:
            print(f"❌ Error enviando acción '{action}': {e}")

    def start(self) -> None:
        self._send("start")

    def stop(self) -> None:
        self._send("stop")

    def freq_up(self) -> None:
        self._send("freq_up")

    def freq_down(self) -> None:
        self._send("freq_down")


class NullBeeperController(BeeperController):
    """Controlador de prueba que no hace nada real (útil para testing local)."""

    def connect(self) -> None:
        print("NullBeeperController: connect()")

    def disconnect(self) -> None:
        print("NullBeeperController: disconnect()")

    def start(self) -> None:
        print("NullBeeperController: start()")

    def stop(self) -> None:
        print("NullBeeperController: stop()")

    def freq_up(self) -> None:
        print("NullBeeperController: freq_up()")

    def freq_down(self) -> None:
        print("NullBeeperController: freq_down()")