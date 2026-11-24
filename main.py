
from machine import Pin
import time
import asyncio
import network
import ujson
import rc522

from umqtt.simple import MQTTClient

# -----------------------------
# CONFIGURACION
# -----------------------------

SSID = "Nombre de la red"
PASSWORD = "Contraseña"

TOKEN = "TokenUbidots"

SERVIDOR = "industrial.api.ubidots.com"
DISPOSITIVO = "control_acceso_pico"

AUTORIZADOS = ["4BEB0307", "974B2606"]

# -----------------------------
# COMPONENTES
# -----------------------------

verde = Pin(12, Pin.OUT)
rojo = Pin(13, Pin.OUT)
mosfet = Pin(10, Pin.OUT, value=0)

reed = Pin(14, Pin.IN, Pin.PULL_UP)

Pin(22, Pin.OUT).value(1)

# -----------------------------
# WIFI
# -----------------------------

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

# -----------------------------
# MQTT
# -----------------------------

cliente = None
eventos = []

def publicar(datos):
    eventos.append(datos)


async def tarea_mqtt():

    global cliente

    topic = ("/v1.6/devices/" + DISPOSITIVO).encode()

    while True:

        try:

            if not wifi.isconnected():

                if cliente:
                    cliente = None

                print("Conectando Wi-Fi...")

                wifi.connect(SSID, PASSWORD)

                while not wifi.isconnected():
                    await asyncio.sleep_ms(500)

                print("WIFI CONECTADO:", wifi.ifconfig()[0])

            if cliente is None:

                print("Conectando MQTT...")

                cliente = MQTTClient(
                    b"pico2w_acceso",
                    SERVIDOR,
                    port=1883,
                    user=TOKEN,
                    password=""
                )

                cliente.connect()

                print("MQTT CONECTADO")

            if eventos:

                datos = eventos.pop(0)

                mensaje = ujson.dumps(datos).encode()

                cliente.publish(topic, mensaje)

                print("ENVIADO A UBIDOTS:", datos)

        except Exception as e:

            print("ERROR MQTT:", e)

            cliente = None

            await asyncio.sleep(3)

        await asyncio.sleep_ms(100)


# -----------------------------
# SENSOR REED
# -----------------------------

async def controlar_puerta():

    estado_anterior = reed.value()

    # Enviar estado inicial
    publicar({"puerta": estado_anterior})

    while True:

        estado_actual = reed.value()

        if estado_actual != estado_anterior:

            if estado_actual == 0:
                print("PUERTA CERRADA")
            else:
                print("PUERTA ABIERTA")

            publicar({"puerta": estado_actual})

            estado_anterior = estado_actual

        await asyncio.sleep_ms(50)


# -----------------------------
# LECTOR RFID
# -----------------------------

async def controlar_rfid():

    while True:

        uid = await rc522.leer_uid_async()

        if uid:

            s = "".join("%02X" % b for b in uid)

            if s in AUTORIZADOS:

                print("ACCESO", s)

                publicar({"acceso": 1})

                verde.on()
                rojo.off()
                mosfet.on()

                await asyncio.sleep(3)

                mosfet.off()
                verde.off()

            else:

                print("DENEGADO", s)

                publicar({"acceso": 0})

                mosfet.off()
                rojo.on()

                await asyncio.sleep(2)

                rojo.off()

            await asyncio.sleep(1)

        await asyncio.sleep_ms(100)


# -----------------------------
# PROGRAMA PRINCIPAL
# -----------------------------

async def main():

    print("SISTEMA DE ACCESO INICIADO")

    asyncio.create_task(tarea_mqtt())
    asyncio.create_task(controlar_puerta())
    asyncio.create_task(controlar_rfid())

    while True:
        await asyncio.sleep(1)


asyncio.run(main())

