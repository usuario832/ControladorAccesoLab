from machine import Pin, SPI
import time

spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT, value=1)
rst = Pin(20, Pin.OUT, value=1)

def wr(reg, val):
    cs.value(0)
    spi.write(bytes([(reg << 1) & 0x7E, val]))
    cs.value(1)

def rd(reg):
    cs.value(0)
    buf = bytearray(2)
    spi.write_readinto(bytes([((reg << 1) & 0x7E) | 0x80, 0]), buf)
    cs.value(1)
    return buf[1]

def transceive(data, ultimos_bits=0):
    wr(0x01, 0x00)                 # reposo
    wr(0x04, 0x7F)                 # borrar banderas de interrupcion
    wr(0x0A, 0x80)                 # vaciar FIFO
    for b in data:
        wr(0x09, b)
    wr(0x0D, ultimos_bits)
    wr(0x01, 0x0C)                 # transceive
    wr(0x0D, ultimos_bits | 0x80)  # iniciar envio
    t = time.ticks_ms()
    while not (rd(0x04) & 0x20):   # esperar bandera de recepcion
        if time.ticks_diff(time.ticks_ms(), t) > 30:
            wr(0x0D, 0)
            return None
    wr(0x0D, 0)
    if rd(0x06) & 0x13:            # error de protocolo, paridad o buffer
        return None
    n = rd(0x0A) & 0x7F
    return [rd(0x09) for _ in range(n)]

def iniciar():
    wr(0x01, 0x0F)                 # reinicio por software
    time.sleep_ms(50)
    wr(0x15, 0x40)
    wr(0x11, 0x3D)
    wr(0x0E, rd(0x0E) & 0x7F)
    wr(0x26, 0x60)                 # ganancia de antena
    wr(0x14, rd(0x14) | 0x03)      # encender antena

def leer_uid():
    r = transceive([0x52], 7)      # WUPA
    if r is None or len(r) != 2:
        return None
    r = transceive([0x93, 0x20], 0)
    if r is None or len(r) != 5:
        print("anticoll incompleto:", r, "ErrorReg:", hex(rd(0x06)))
        return None
    if r[0] ^ r[1] ^ r[2] ^ r[3] != r[4]:
        print("checksum del UID incorrecto:", r)
        return None
    return r[:4]

iniciar()

