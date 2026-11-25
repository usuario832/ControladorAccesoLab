# Sistema de control de acceso para laboratorios con Raspberry Pi Pico 2 W

Proyecto final del curso **Arquitectura del Computador I (16953)**, Universidad ESAN, semestre 2026-2.
Profesor: Marks Calderón Niquin.

**Integrantes**
- Jefferson Samuel Arotoma Chávez
- Mathias Eduardo Hernández Chávez
- Luis Angel Neira Carhupoma
- Fabrizio Alonso Rodríguez García

## ¿Qué hace este proyecto?

Es una puerta inteligente para un laboratorio. La persona acerca su tarjeta al lector:

- Si la tarjeta está autorizada, se prende el LED verde y la cerradura se abre por 3 segundos.
- Si no está autorizada, se prende el LED rojo y la cerradura sigue cerrada.
- Un sensor magnético avisa si la puerta está abierta o cerrada.
- Todo lo que pasa se envía por internet a un panel (dashboard) en Ubidots, donde se ve el historial.
- Si un acceso es denegado, llega una alerta al celular.

Si se cae el Wi-Fi, la puerta sigue funcionando igual. Los eventos se guardan y se envían cuando vuelve el internet.

## Piezas que usamos

| Pieza | Para qué sirve |
|---|---|
| Raspberry Pi Pico 2 W | Es el cerebro del sistema |
| Lector RFID RC522 | Lee las tarjetas |
| Sensor magnético MC-38 (reed) | Detecta si la puerta está abierta o cerrada |
| Cerradura solenoide de 12 V | Abre y cierra la puerta |
| Transistor MOSFET IRLZ44N | Le permite a la Pico controlar la cerradura de 12 V |
| Diodo 1N4007 | Protege el circuito cuando la cerradura se apaga |
| Fuente de 12 V, 2 A | Da la energía a la cerradura |
| LEDs verde y rojo con resistencias de 330 Ω | Muestran si el acceso fue permitido o denegado |
| Caja impresa en 3D | Guarda y protege la electrónica |

## Conexiones

| Qué | Pin de la Pico |
|---|---|
| Lector RC522: SCK, MOSI, MISO | GP18, GP19, GP16 |
| Lector RC522: CS (SDA) y RST | GP17 y GP20 |
| Lector RC522: alimentación | 3V3 (pin 36) |
| Sensor de puerta | GP14 y GND |
| LED verde | GP12 |
| LED rojo | GP13 |
| Cerradura (por el MOSFET) | GP10 |

**Muy importante**
- El lector RC522 va a **3,3 V**. Nunca a 5 V, porque se daña.
- La cerradura usa 12 V y **no se conecta directo a la Pico**: pasa por el MOSFET.
- El diodo va en paralelo con la cerradura, con la raya del lado del +12 V.
- Todo el cableado se hace con la fuente desenchufada.
- La cerradura no se energiza más de 3 o 4 segundos seguidos.

El diagrama de conexiones está en la carpeta `docs/`.

## Archivos del repositorio

| Archivo o carpeta | Qué contiene |
|---|---|
| `main.py` | Programa principal |
| `rc522.py` | Código para leer las tarjetas |
| `medicion.py` | Programa con el que medimos el reto (interrupciones contra sondeo) |
| `docs/` | Diagrama de conexiones e informe |
| `cad/` | Archivos de la caja 3D (CAD y STL) |

## Cómo usarlo

1. Instalar **MicroPython 1.29.0** en la Pico 2 W.
2. Copiar `main.py` y `rc522.py` a la Pico (por ejemplo con Thonny).
3. Abrir `main.py` y completar tus datos en la parte de configuración:
   - nombre y contraseña de tu Wi-Fi (debe ser de **2,4 GHz**),
   - tu token de Ubidots,
   - la lista de tarjetas autorizadas.
4. Conectar todo como indica la tabla de conexiones.
5. Reiniciar la Pico. En la consola debe aparecer `SISTEMA DE ACCESO INICIADO`.

> Los datos privados (contraseña, token y números de las tarjetas) **no están en este repositorio**. Cada persona debe poner los suyos.

## Cómo funciona por dentro

El programa hace tres cosas al mismo tiempo, sin que una bloquee a las otras (usamos `asyncio`):

1. **Leer tarjetas:** compara cada tarjeta con la lista de autorizadas y abre o no la cerradura.
2. **Vigilar la puerta:** cuando la puerta cambia de estado, avisa y registra el evento.
3. **Enviar a la nube:** manda los eventos a Ubidots por MQTT. Si no hay internet, los guarda y los reenvía al volver.

## Nuestro reto: interrupciones en vez de revisar todo el tiempo

Antes el sensor de la puerta se revisaba cada cierto tiempo (*sondeo* o *polling*). Ahora usa **interrupciones**: el sensor avisa solo cuando cambia, sin que la Pico tenga que estar preguntando.

Lo medimos con 30 pruebas por versión:

| Qué medimos | Revisando cada 20 ms | Con interrupciones |
|---|---|---|
| Tiempo en detectar el cambio | 10,742 ms | 0,055 ms |
| Pulsos cortos que se perdieron | 80 % | 0 % |
| Uso del procesador | casi igual | casi igual |

**Conclusión:** las interrupciones detectan el cambio unas 195 veces más rápido y no se pierde ninguna señal corta. Gastar menos procesador no fue la ventaja en este caso.

## Otros resultados

- La Pico tarda menos de 1 ms en activar la cerradura después de leer una tarjeta.
- Leer una tarjeta toma unos 6 ms.
- Acertó el 100 % de las pruebas con tarjetas autorizadas y denegadas (22 de 22).
- Con el Wi-Fi caído se generaron 4 eventos y se recuperaron los 4 al volver la conexión.

## Limitaciones

- Si la Pico se reinicia mientras no hay Wi-Fi, se pierden los eventos que estaban guardados.
- Los eventos reenviados llegan con la hora del reenvío, no con la hora real en que pasaron.
- El número de las tarjetas MIFARE Classic se puede copiar, así que no es una seguridad fuerte.
- No se midió el consumo de energía porque no teníamos un medidor.

## Ideas para mejorar

- Guardar los eventos pendientes en la memoria flash.
- Enviar la hora real con cada evento.
- Abrir la puerta de forma remota desde Ubidots.
- Usar la interrupción del propio lector RC522 y probar DMA.
- Guardar un código cifrado (hash) de cada tarjeta en vez del número real.

## Uso de inteligencia artificial

Usamos Claude, ChatGPT y Gemini para encontrar errores, entender fallos y mejorar imágenes. Cada solución se probó en el montaje real.
