"""
Actively scans for a peripheral, connects, reads/writes characteristics.
This is the client side.
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


def parse_entries(data):
    # data is sequence of 4-byte entries: idx, r, g, b
    if not data:
        return []
    entries = []
    if len(data) % 4 != 0:
        # ignore trailing malformed bytes
        length = len(data) - (len(data) % 4)
    else:
        length = len(data)
    for i in range(0, length, 4):
        idx = data[i]
        r = data[i + 1]
        g = data[i + 2]
        b = data[i + 3]
        entries.append((idx, (r, g, b)))
    return entries


def pack_entries(entries):
    # entries: iterable of (idx, (r,g,b))
    out = bytearray()
    for idx, (r, g, b) in entries:
        # clamp values to 0..255 to avoid wrap-around
        ri = max(0, min(255, int(r)))
        gi = max(0, min(255, int(g)))
        bi = max(0, min(255, int(b)))
        out.append(idx & 0xFF)
        out.append(ri)
        out.append(gi)
        out.append(bi)
    return bytes(out)


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
        entries = parse_entries(data)

        if not entries:
            print("Received empty payload, skipping:", data)
            await asyncio.sleep(0.5)
            continue
        try:
            print("Received entries:", entries)
            # set colors on the matrix according to entries
            np.fill((0, 0, 0))
            for idx, (r, g, b) in entries:
                if 0 <= idx < len(np):
                    np[idx] = (r, g, b)
            np.write()
        except Exception as e:
            print("Error processing payload:", e, "raw:", data)

        # send to peripheral on the dedicated rx characteristic: include colors now
        # example: reply with four indices and white color
        reply = [(0, (100, 100, 100)), (2, (100, 100, 100)), (4, (100, 100, 100)), (6, (100, 100, 100))]
        message = pack_entries(reply)
        try:
            print("try to send:", reply)
            await char_rx.write(message)
        except Exception as e:
            print("char_rx write failed:", e)
        print("Sent reply:", reply)

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
