"""
Actively scans for a peripheral, connects, reads/writes characteristics. This is the client side.
"""


import uasyncio as asyncio
import aioble
import bluetooth
import struct

from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms


SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
CHAR_TX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")  # peripheral -> central
CHAR_RX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")  # central -> peripheral


def process_list(data):
    if not data:
        return []
    return list(data)


def process_value(data):
    if not data or len(data) < 2:
        raise struct.error("buffer too small")
    return struct.unpack("<h", data)[0]


async def central_task():
    print("Scanning for devices...")
    device = None
    async with aioble.scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            print("Found:", result.name(), result.device)
            if "PicoAdvertiser" == result.name():
                device = result.device
                break

    if not device:
        print("No PicoAdvertiser found")
        return

    print("Connecting...")
    connection = await device.connect(timeout_ms=2000)
    print("Connected!")

    service = await connection.service(SERVICE_UUID)
    char_tx = await service.characteristic(CHAR_TX_UUID)  # read notifications / reads from peripheral
    char_rx = await service.characteristic(CHAR_RX_UUID)  # write to peripheral

    while connection.is_connected():
        # read peripheral->central data
        data = await char_tx.read()
        indices = process_list(data)

        if not indices:
            print("Received empty payload, skipping:", data)
            await asyncio.sleep(0.5)
            continue
        try:
            print("Received indices:", indices)
            # set color on all indices
            np.fill((0, 0, 0))
            for idx in indices:
                if 0 <= idx < len(np):
                    np[idx] = (100, 100, 100)
            np.write()
        except Exception as e:
            print("Error processing payload:", e, "raw:", data)

        # send to peripheral on the dedicated rx characteristic
        send_indices = [0,2,4,6]
        message = bytes(send_indices)
        try:
            print("try to send: ", send_indices)
            await char_rx.write(message)
        except Exception as e:
            print("char_rx write failed:", e)

        await asyncio.sleep(0.5)


def test_matrix():
    np[0] = (100, 100, 100)
    np.write()
    sleep_ms(500)
    np[0] = (0, 0, 0)
    np.write()
    sleep_ms(500)


if __name__ == '__main__':
    pin = Pin(19, Pin.OUT)
    np = NeoPixel(pin, 64)
    test_matrix()

    asyncio.run(central_task())
