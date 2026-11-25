
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

SSID = "RELLENAR"
PASSWORD = "RELLENAR"

TOKEN = "RELLENAR"

SERVIDOR = "industrial.api.ubidots.com"
DISPOSITIVO = "control_acceso_pico"

AUTORIZADOS = ["RELLENAR", "RELLENAR"]

# -----------------------------
# COMPONENTES
# -----------------------------

verde = Pin(12, Pin.OUT)
rojo = Pin(13, Pin.OUT)
mosfet = Pin(10, Pin.OUT, value=0)

reed = Pin(14, Pin.IN, Pin.PULL_UP)

reed_flag = asyncio.ThreadSafeFlag()

def reed_irq(pin):
    reed_flag.set()          # el handler solo avisa, no hace nada más

reed.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=reed_irq)

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
                
                t_pub = time.ticks_ms()
                cliente.publish(topic, mensaje)
                print("T_PUBLICAR_ms:", time.ticks_diff(time.ticks_ms(), t_pub))

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

        await reed_flag.wait()          # duerme hasta que llegue la interrupción
        await asyncio.sleep_ms(20)      # antirrebote
        estado_actual = reed.value()

        if estado_actual != estado_anterior:

            if estado_actual == 0:
                print("PUERTA CERRADA")
            else:
                print("PUERTA ABIERTA")

            publicar({"puerta": estado_actual})

            estado_anterior = estado_actual


# -----------------------------
# LECTOR RFID
# -----------------------------

async def controlar_rfid():

    while True:
        
        t_ini = time.ticks_ms()
        uid = await rc522.leer_uid_async()
        t_lect = time.ticks_diff(time.ticks_ms(), t_ini)
        t_uid = time.ticks_us()

        if uid:

            s = "".join("%02X" % b for b in uid)

            if s in AUTORIZADOS:

                print("ACCESO", s)

                publicar({"acceso": 1})

                verde.on()
                rojo.off()
                mosfet.on()
                print("T_LECTURA_ms:", t_lect,
                      "| T_RESPUESTA_us:", time.ticks_diff(time.ticks_us(), t_uid))

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

