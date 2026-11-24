"""
BLECommunicator - einfache Bluetooth-Verbindung zwischen zwei Picos.

Ein Pico ist der "peripheral": Er macht Werbung (advertising) und wartet.
Der andere Pico ist der "central": Er sucht den peripheral und verbindet sich.

Danach koennen beide Daten als Dictionary senden und empfangen,
zum Beispiel {"x": 3, "y": 5}.

Achtung: Eine Nachricht darf hoechstens ca. 20 Zeichen lang sein
("x=3;y=5" sind 7 Zeichen).
"""

import uasyncio as asyncio
import aioble
import bluetooth

# Diese UUIDs muessen auf beiden Picos genau gleich sein.
SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
TO_CENTRAL_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")     # peripheral -> central
TO_PERIPHERAL_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")  # central -> peripheral


# ------------------- Daten umwandeln -------------------

def encode(data):
    """Dictionary -> Bytes.   {"x": 3, "y": 5}  ->  b"x=3;y=5" """
    parts = []
    for key, value in data.items():
        parts.append(str(key) + "=" + str(value))
    return ";".join(parts).encode()


def decode(message):
    """Bytes -> Dictionary.   b"x=3;y=5"  ->  {"x": 3, "y": 5}"""
    data = {}
    if not message:
        return data  # noch nichts empfangen

    for part in message.decode().split(";"):
        key, value = part.split("=")
        try:
            value = int(value)  # Zahlen wieder in Zahlen verwandeln
        except ValueError:
            pass  # keine Zahl -> bleibt Text
        data[key] = value
    return data


# ------------------- Die Klasse -------------------

class BLECommunicator:

    def __init__(self, name, role):
        if role not in ("central", "peripheral"):
            raise ValueError('role muss "central" oder "peripheral" sein')
        self.name = name        # Name, unter dem der peripheral gefunden wird
        self.role = role
        self.connection = None
        self.to_central = None     # Kanal peripheral -> central
        self.to_peripheral = None  # Kanal central -> peripheral

    async def connect(self):
        """Verbindung aufbauen. Wartet, bis die Verbindung steht."""
        if self.role == "central":
            await self._connect_as_central()
        else:
            await self._connect_as_peripheral()

    async def send(self, data):
        """Ein Dictionary an den anderen Pico senden."""
        message = encode(data)
        if self.role == "central":
            await self.to_peripheral.write(message)
        else:
            self.to_central.write(message)

    async def receive(self):
        """Daten vom anderen Pico empfangen (als Dictionary).

        central:    liest die letzte Nachricht des peripheral (wartet nicht).
        peripheral: wartet, bis der central etwas schickt.
        """
        if self.role == "central":
            message = await self.to_central.read()
        else:
            _, message = await self.to_peripheral.written()
        return decode(message)

    # ------------------- central -------------------

    async def _connect_as_central(self):
        # 1. Suchen, bis ein Geraet mit dem richtigen Namen gefunden ist
        device = None
        while device is None:
            print("Suche nach", self.name, "...")
            async with aioble.scan(5000, interval_us=30000, window_us=30000, active=True) as scanner:
                async for result in scanner:
                    if result.name() == self.name:
                        device = result.device
                        break

        # 2. Verbinden
        self.connection = await device.connect(timeout_ms=2000)

        # 3. Die beiden Kanaele suchen.
        #    Direkt nach dem Verbinden klappt das manchmal nicht sofort,
        #    darum versuchen wir es bis zu 5 Mal.
        for attempt in range(5):
            try:
                service = await self.connection.service(SERVICE_UUID)
                self.to_central = await service.characteristic(TO_CENTRAL_UUID)
                self.to_peripheral = await service.characteristic(TO_PERIPHERAL_UUID)
                if self.to_central and self.to_peripheral:
                    print("Verbunden mit", self.name)
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)

        raise RuntimeError("Verbunden, aber die Kanaele wurden nicht gefunden")

    # ------------------- peripheral -------------------

    async def _connect_as_peripheral(self):
        # 1. Die beiden Kanaele anlegen
        service = aioble.Service(SERVICE_UUID)
        self.to_central = aioble.Characteristic(service, TO_CENTRAL_UUID, read=True)
        self.to_peripheral = aioble.Characteristic(service, TO_PERIPHERAL_UUID, write=True, capture=True)
        aioble.register_services(service)

        # 2. Werbung machen und warten, bis sich ein central verbindet
        print("Warte auf Verbindung als", self.name, "...")
        self.connection = await aioble.advertise(500_000, name=self.name, services=[SERVICE_UUID])
        print("Verbunden mit", self.connection.device)
