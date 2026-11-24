"""
CENTRAL: sucht den anderen Pico, verbindet sich und tauscht Daten aus.

Diese Datei und BLECommunicator.py auf den Pico laden.
"""

import uasyncio as asyncio
from BLECommunicator import BLECommunicator

# Muss genau gleich sein wie DEVICE_NAME im peripheral!
DEVICE_NAME = "Pico2-adv"


async def main():
    ble = BLECommunicator(DEVICE_NAME, "central")
    await ble.connect()

    counter = 0
    while True:
        # Daten senden
        await ble.send({"a": counter, "b": counter * 2})

        # Daten empfangen
        data = await ble.receive()
        if data:
            print("Empfangen:", data)
            # Hier eigenen Code einfuegen, z.B. LEDs einschalten:
            # x = data["x"]

        counter += 1
        await asyncio.sleep(0.5)


asyncio.run(main())
