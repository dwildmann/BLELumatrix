"""
Advertises, waits for connections from central(s), provides services/characteristics.
This is the server side.
"""


import uasyncio as asyncio
import aioble
import bluetooth

from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms

SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
CHAR_TX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")  # peripheral -> central
CHAR_RX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")  # central -> peripheral


def parse_entries(data):
    # parse 4-byte entries idx,r,g,b -> list of (idx,(r,g,b))
    if not data:
        return []
    entries = []
    if len(data) % 4 != 0:
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
    out = bytearray()
    for idx, (r, g, b) in entries:
        # clamp color bytes to 0..255
        ri = max(0, min(255, int(r)))
        gi = max(0, min(255, int(g)))
        bi = max(0, min(255, int(b)))
        out.append(idx & 0xFF)
        out.append(ri)
        out.append(gi)
        out.append(bi)
    return bytes(out)


async def peripheral_task():
    count = 0
    while True:
        print("Advertising...")
        conn = await aioble.advertise(
            500_000,
            name="PicoAdvertiser",
            services=[SERVICE_UUID],
        )
        print("Connected to", conn.device)

        try:
            while conn.is_connected():
                indices = [(count + i) % 64 for i in range(8)]
                # attach a color to each index (example: varying red). pack and send each entry
                entries = [(idx, (count * 10, 100, 100)) for idx in indices]
                # send each entry as a separate 4-byte notification to avoid MTU truncation
                for entry in entries:
                    chunk = pack_entries([entry])  # single 4-byte payload
                    try:
                        char_tx.write(chunk)
                    except Exception as e:
                        print("char_tx write failed:", e)
                    try:
                        # notify is not awaitable
                        char_tx.notify(conn, chunk)
                    except Exception:
                        pass
                    # small gap so central can process notifications
                    await asyncio.sleep(0.01)
                print("Sent entries:", entries)

                count = (count + 1) & 0x7FFF

                try:
                    source_conn, data = await char_rx.written() # source_conn lets you know the origin of the message
                except Exception as e:
                    print("char_rx read error:", e)
                    await asyncio.sleep(0.5)
                    continue

                # process incoming payload from central
                rec_entries = parse_entries(data)
                print("Received from central:", rec_entries)
                np.fill((0, 0, 0))
                for idx, (r, g, b) in rec_entries:
                    if 0 <= idx < len(np):
                        np[idx] = (r, g, b)
                np.write()
                await asyncio.sleep(0.5)
        except Exception as e:
            print("Connection lost:", e)


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

    service = aioble.Service(SERVICE_UUID)
    char_tx = aioble.Characteristic(service, CHAR_TX_UUID, read=True, write=True, notify=True)
    char_rx = aioble.Characteristic(service, CHAR_RX_UUID, read=True, write=True, capture=True)
    aioble.register_services(service)

    asyncio.run(peripheral_task())
