from abc import ABC, abstractmethod
import asyncio
import json
from typing import Optional


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
    Implementación simple que envía acciones al servidor por WebSocket.
    Se puede crear sin socket y luego adjuntar ws/loop con attach_transport().
    """

    def __init__(self, ws: Optional[object] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._ws = ws
        self._loop = loop

    def attach_transport(self, ws, loop: asyncio.AbstractEventLoop) -> None:
        """Adjunta el websocket y el event loop (llamar cuando se conecta)."""
        self._ws = ws
        self._loop = loop

    def detach_transport(self) -> None:
        self._ws = None
        self._loop = None

    def connect(self) -> None:
        # La conexión WebSocket la maneja el hilo / cliente; aquí no se abre nada.
        return

    def disconnect(self) -> None:
        self.detach_transport()

    def _send(self, action: str) -> None:
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