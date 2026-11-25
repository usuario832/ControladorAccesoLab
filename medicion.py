# medicion.py - Reto: Interrupciones (V1) contra polling (V0)
# Cable: GP21 (salida generadora) -> GP15 (entrada)
from machine import Pin, Timer
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms
from math import sqrt
import urandom

N = 30            # pruebas por versión
POLL_MS = 20      # mismo intervalo que main.py
DEB_MS = 20       # antirrebote de V1

gen = Pin(21, Pin.OUT, value=1)       # reposo = 1
ent = Pin(15, Pin.IN, Pin.PULL_UP)    # evento = flanco de bajada
t_bajar = Timer(-1)
t_subir = Timer(-1)
t_carga = Timer(-1)

t0 = 0
def cb_bajar(t):
    global t0
    t0 = ticks_us()
    gen.value(0)

def cb_subir(t):
    gen.value(1)

def pulso(retardo_ms, ancho_ms):
    """Programa un pulso en 'retardo_ms' con duración 'ancho_ms'."""
    t_bajar.init(mode=Timer.ONE_SHOT, period=retardo_ms, callback=cb_bajar)
    t_subir.init(mode=Timer.ONE_SHOT, period=retardo_ms + ancho_ms, callback=cb_subir)

def aleatorio(a, b):
    return a + urandom.getrandbits(8) * (b - a) // 255

def stats(v):
    n = len(v)
    m = sum(v) / n
    d = sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else 0
    return m, d

# ---------- V1: manejador de interrupción ----------
t1 = None
ev = 0
ult = 0
def handler(p):
    global t1, ev, ult
    ahora = ticks_ms()
    if ticks_diff(ahora, ult) > DEB_MS:      # antirrebote
        ult = ahora
        ev += 1
        if t1 is None:
            t1 = ticks_us()

# ---------- 1) LATENCIA ----------
def lat_v0():
    global t1
    res = []
    for _ in range(N):
        pulso(aleatorio(80, 180), 50)
        visto = None
        lim = ticks_ms()
        while visto is None and ticks_diff(ticks_ms(), lim) < 600:
            if ent.value() == 0:
                visto = ticks_us()
            else:
                sleep_ms(POLL_MS)            # polling cada 20 ms
        if visto is not None:
            res.append(ticks_diff(visto, t0) / 1000)  # ms
        sleep_ms(300)
    return res

def lat_v1():
    global t1
    res = []
    ent.irq(trigger=Pin.IRQ_FALLING, handler=handler)
    for _ in range(N):
        t1 = None
        pulso(aleatorio(80, 180), 50)
        lim = ticks_ms()
        while t1 is None and ticks_diff(ticks_ms(), lim) < 600:
            pass
        if t1 is not None:
            res.append(ticks_diff(t1, t0) / 1000)     # ms
        sleep_ms(300)
    ent.irq(handler=None)
    return res

# ---------- 2) PÉRDIDA DE LECTURAS (pulsos de 3 ms) ----------
def perd_v0():
    vistos = 0
    for _ in range(N):
        pulso(aleatorio(80, 180), 3)
        lim = ticks_ms()
        visto = False
        while ticks_diff(ticks_ms(), lim) < 300:
            if ent.value() == 0:
                visto = True
            sleep_ms(POLL_MS)
        vistos += visto
    return 100 * (N - vistos) / N

def perd_v1():
    global ev, ult
    ev = 0
    ult = 0
    ent.irq(trigger=Pin.IRQ_FALLING, handler=handler)
    for _ in range(N):
        pulso(aleatorio(80, 180), 3)
        sleep_ms(300)
    ent.irq(handler=None)
    return 100 * (N - ev) / N

# ---------- 3) USO DE CPU (contador de bucle libre, 3 s) ----------
def cb_carga(t):
    gen.toggle()           # carga: 10 flancos de bajada por segundo
    
def ventana(modo):
    """modo: 'base' | 'v0' | 'v1'. Devuelve vueltas del contador."""
    global ult
    gen.value(1)
    ult = 0
    if modo == 'v1':
        ent.irq(trigger=Pin.IRQ_FALLING, handler=handler)
    t_carga.init(mode=Timer.PERIODIC, period=50, callback=cb_carga)
    c = 0
    ini = ticks_ms()
    ultp = ini
    while True:
        ahora = ticks_ms()
        if ticks_diff(ahora, ini) >= 3000:
            break
        c += 1
        if ticks_diff(ahora, ultp) >= POLL_MS:   # mismo costo en las 3 versiones
            ultp = ahora
            if modo == 'v0':
                _ = ent.value()                  # única diferencia: leer el pin
    t_carga.deinit()
    ent.irq(handler=None)
    gen.value(1)
    return c

# ---------- EJECUCIÓN ----------
print("=== V0: polling ===")
l0 = lat_v0();  p0 = perd_v0()
print("=== V1: interrupciones ===")
l1 = lat_v1();  p1 = perd_v1()
print("=== CPU ===")
base = ventana('base')
c0 = ventana('v0')
c1 = ventana('v1')
cpu0 = 100 * (1 - c0 / base)
cpu1 = 100 * (1 - c1 / base)

m0, d0 = stats(l0)
m1, d1 = stats(l1)
print("\n------ RESULTADOS (Tabla 3) ------")
print("Muestras V0: %d | V1: %d" % (len(l0), len(l1)))
print("Latencia V0: %.3f ms (desv %.3f)" % (m0, d0))
print("Latencia V1: %.3f ms (desv %.3f)" % (m1, d1))
print("Perdida pulsos 3 ms  V0: %.1f %% | V1: %.1f %%" % (p0, p1))
print("Uso CPU extra  V0: %.3f %% | V1: %.3f %%" % (cpu0, cpu1))
print("Vueltas base/V0/V1:", base, c0, c1)