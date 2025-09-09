import uasyncio as asyncio
import aioble
import bluetooth

class BLECommunicator:
    type = "BLEDevice"
    name = "Unknown"

    SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
    CHAR_TX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
    CHAR_RX_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")

    def __init__(self, name=None, role="central"):
        if name:
            self.name = name
        self.role = role  # "central" or "peripheral"
        self.conn = None
        self.char_tx = None
        self.char_rx = None

    # ------------------- Utilities -------------------
    @staticmethod
    def pack_kv(data):
        """Serialize exactly two key-value pairs to bytes"""
        if len(data) != 2:
            raise ValueError("Data must contain exactly two key-value pairs")
        serialized = ";".join("{}={}".format(k, v) for k, v in data.items())
        return serialized.encode()

    @staticmethod
    def parse_kv(data):
        """Deserialize bytes to two key-value pairs"""
        decoded = data.decode()
        result = {}
        for pair in decoded.split(";"):
            k, v = pair.split("=")
            result[k] = v
        return result

    # ------------------- Initialization -------------------
    async def init(self):
        if self.role == "central":
            await self._init_central()
        else:
            await self._init_peripheral()

    # ------------------- Central -------------------
    async def _init_central(self):
        print("Scanning for devices...")
        device = None
        async with aioble.scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                if result.name() == self.name:
                    device = result.device
                    break
        if not device:
            raise RuntimeError("Peripheral not found")

        self.conn = await device.connect(timeout_ms=2000)
        print("Connected to peripheral:", self.conn.device)

        # Retry loop for service discovery
        service = None
        for _ in range(5):
            try:
                service = await self.conn.service(self.SERVICE_UUID)
                if service:
                    break
            except Exception:
                await asyncio.sleep(0.5)
        if not service:
            raise RuntimeError("Service not found on peripheral")

        # Retry loop for characteristics
        self.char_tx = None
        self.char_rx = None
        for _ in range(5):
            try:
                self.char_tx = await service.characteristic(self.CHAR_TX_UUID)
                self.char_rx = await service.characteristic(self.CHAR_RX_UUID)
                if self.char_tx and self.char_rx:
                    break
            except Exception:
                await asyncio.sleep(0.5)
        if not self.char_tx or not self.char_rx:
            raise RuntimeError("Characteristics not found")
        print("Central ready for communication")

    # ------------------- Peripheral -------------------
    async def _init_peripheral(self):
        service = aioble.Service(self.SERVICE_UUID)
        self.char_tx = aioble.Characteristic(service, self.CHAR_TX_UUID, read=True, write=True, notify=True)
        self.char_rx = aioble.Characteristic(service, self.CHAR_RX_UUID, read=True, write=True, capture=True)
        aioble.register_services(service)

        print("Peripheral ready. Advertising...")
        self.conn = await aioble.advertise(500_000, name=self.name, services=[self.SERVICE_UUID])
        print("Peripheral connected to", self.conn.device)

    # ------------------- Send / Receive -------------------
    async def send(self, data):
        payload = self.pack_kv(data)
        if self.role == "central":
            if self.char_rx:
                await self.char_rx.write(payload)
        else:
            # Only send if central is connected
            if self.conn and self.char_tx:
                try:
                    self.char_tx.write(payload)
                    self.char_tx.notify(self.conn, payload)
                except Exception as e:
                    print("TX failed:", e)
            else:
                print("TX skipped: no central connected")

    async def receive(self):
        if self.role == "central":
            if self.char_tx:
                return self.parse_kv(await self.char_tx.read())
            return {}
        else:
            # Wait for a new write from central
            try:
                _, data = await self.char_rx.written()
                return self.parse_kv(data)
            except Exception:
                return {}
