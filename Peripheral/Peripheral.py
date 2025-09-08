"""
Advertises, waits for connections from central(s), provides services/characteristics. This is the server side.
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


def process_list(data):
    if not data:
        return []
    return list(data)


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
                tx_message = bytes(indices)  # peripheral -> central
                try:
                    char_tx.write(tx_message)
                except Exception as e:
                    print("char_tx write failed:", e)
                try:
                    char_tx.notify(conn, tx_message)
                except Exception:
                    pass
                print("Sent indices:", indices)

                count = (count + 1) & 0x7FFF

                try:
                    source_conn, data = await char_rx.written() # source_conn lets you know the origin of the message
                except Exception as e:
                    print("char_rx read error:", e)
                    await asyncio.sleep(0.5)
                    continue

                # process incoming payload from central
                rec_indices = process_list(data)
                print("Received from central:", rec_indices)
                np.fill((0, 0, 0))
                for idx in rec_indices:
                    if 0 <= idx < len(np):
                        np[idx] = (100, 100, 100)
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
