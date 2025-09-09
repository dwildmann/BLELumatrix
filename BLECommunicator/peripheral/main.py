import uasyncio as asyncio
from BLECommunicator import BLECommunicator

received_data = None # Shared variable to hold received data

async def peripheral_loop():
    global received_data
    ble = BLECommunicator(name="Pico2-adv", role="peripheral")
    await ble.init()
    count = 0
    while True:
        # Receive messages from central
        data = await ble.receive()
        if data:
            print("Received from central:", data)
            received_data = data  # Store received data

        # Periodically send a reply only if central is connected
        reply = {"key1": count, "key2": count*2}
        await ble.send(reply)
        count += 1
        await asyncio.sleep(0.5)

async def data_watcher():
    global received_data
    while True:
        if received_data:
            # Do something with the received data
            print("Processing received data:", received_data)
            received_data = None  # Reset after processing
        else:
            print("No News")
        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(
        peripheral_loop(),
        data_watcher()
    )

asyncio.run(main())
