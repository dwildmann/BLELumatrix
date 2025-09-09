import uasyncio as asyncio
from BLECommunicator import BLECommunicator

received_data = None  # Shared variable to hold received data

async def central_loop():
    global received_data
    ble = BLECommunicator(name="Pico2-adv", role="central")
    await ble.init()
    while True:
        await ble.send({"key1": 42, "key2": 100})
        data = await ble.receive()
        if data:
            received_data = data
        print("Received from peripheral:", data)
        await asyncio.sleep(0.5)

async def data_watcher():
    global received_data
    while True:
        if received_data:
            print("Watcher got new data:", received_data)
            received_data = None  # Reset after handling
        else:
            print("No News")
        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(
        central_loop(),
        data_watcher()
    )

asyncio.run(main())
