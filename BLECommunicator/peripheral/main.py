"""
PERIPHERAL: wartet, bis sich der andere Pico verbindet, und tauscht Daten aus.

Diese Datei und BLECommunicator.py auf den Pico laden.
"""

import uasyncio as asyncio
from BLECommunicator import BLECommunicator

# Muss genau gleich sein wie DEVICE_NAME im central!
DEVICE_NAME = "Pico2-adv"


async def main():
    ble = BLECommunicator(DEVICE_NAME, "peripheral")
    await ble.connect()

    counter = 0
    while True:
        # Warten, bis der central etwas schickt
        data = await ble.receive()
        print("Empfangen:", data)
        # Hier eigenen Code einfuegen, z.B. LEDs einschalten:
        # a = data["a"]

        # Antwort senden
        await ble.send({"x": counter, "y": counter * 2})
        counter += 1


asyncio.run(main())
