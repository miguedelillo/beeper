import asyncio
import websockets
import json
from beeper import Beeper, beep

clients = set()
ws_beepers = {}  # mapa websocket -> (Beeper, OutputStream)
SEMITONE_RATIO = 2 ** (1/12)
async def handler(ws):
    clients.add(ws)
    try:
        async for message in ws:
            try:
                data = json.loads(message)
            except Exception:
                print("Mensaje no JSON:", message)
                continue

            action = data.get("action")
            print(f"Received message: {data}")

            if action == "start":
                if ws in ws_beepers:
                    print("⚠️ Beeper already running for this client.")
                    continue
                beeper = Beeper()
                try:
                    stream = beeper.constant_beep()
                    ws_beepers[ws] = (beeper, stream)
                    print("✅ Started beeper (output stream running).")
                except Exception as e:
                    print(f"❌ Failed to start beeper: {e}")

            elif action == "stop":
                if ws not in ws_beepers:
                    print("⚠️ No beeper running for this client.")
                    continue
                beeper, stream = ws_beepers.pop(ws)
                try:
                    stream.stop()
                except Exception as e:
                    print(f"⚠️ Error stopping stream: {e}")
                try:
                    stream.close()
                except Exception as e:
                    print(f"⚠️ Error closing stream: {e}")
                print("✅ Stopped beeper and closed stream.")

            elif action == "freq_up":
                if ws not in ws_beepers:
                    print("⚠️ No beeper to change frequency.")
                    continue
                beeper, _ = ws_beepers[ws]
                beeper.target_freq *= SEMITONE_RATIO
                print(f"🔊 Frequency increased to {beeper.freq} Hz")

            elif action == "freq_down":
                if ws not in ws_beepers:
                    print("⚠️ No beeper to change frequency.")
                    continue
                beeper, _ = ws_beepers[ws]
                beeper.target_freq /= SEMITONE_RATIO
                print(f"🔊 Frequency decreased to {beeper.freq} Hz")

            else:
                # fallback: play short local beep on server
                try:
                    beep()
                except Exception as e:
                    print(f"❌ Error playing short beep: {e}")

    finally:
        # cleanup if the client disconnects unexpectedly
        if ws in ws_beepers:
            _, stream = ws_beepers.pop(ws)
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
            print("ℹ️ Cleaned up beeper for disconnected client.")
        clients.discard(ws)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
