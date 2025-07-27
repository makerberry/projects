import socket
import time

import neopixel
import network
import utime
from machine import PWM, Pin

NUM_LEDS = 4  # Anzahl an LEDs vorne am Pico Go
LED_PIN = 22  # Falls deine LEDs an einem anderen Pin sind: hier anpassen
np = neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS)


def blink(color, count=3, delay=0.3):
    for _ in range(count):
        for i in range(NUM_LEDS):
            np[i] = color
        np.write()
        time.sleep(delay)
        for i in range(NUM_LEDS):
            np[i] = (0, 0, 0)
        np.write()
        time.sleep(delay)


def blink_green(count=3):
    blink((0, 64, 0), count)


def blink_red(count=3):
    blink((64, 0, 0), count)


# === PicoGo Motor-Klasse ===


class PicoGo:
    def __init__(self):
        self.PWMA = PWM(Pin(16))
        self.PWMA.freq(1000)
        self.AIN2 = Pin(17, Pin.OUT)
        self.AIN1 = Pin(18, Pin.OUT)
        self.BIN1 = Pin(19, Pin.OUT)
        self.BIN2 = Pin(20, Pin.OUT)
        self.PWMB = PWM(Pin(21))
        self.PWMB.freq(1000)
        self.stop()

    def forward(self, speed):
        self.PWMA.duty_u16(int(speed * 0xFFFF / 100))
        self.PWMB.duty_u16(int(speed * 0xFFFF / 100))
        self.AIN2.value(1)
        self.AIN1.value(0)
        self.BIN2.value(1)
        self.BIN1.value(0)

    def backward(self, speed):
        self.PWMA.duty_u16(int(speed * 0xFFFF / 100))
        self.PWMB.duty_u16(int(speed * 0xFFFF / 100))
        self.AIN2.value(0)
        self.AIN1.value(1)
        self.BIN2.value(0)
        self.BIN1.value(1)

    def left(self, speed):
        # Linkes Rad langsamer, rechtes Rad normal
        self.setMotor(speed // 2, speed)

    def right(self, speed):
        # Rechtes Rad langsamer, linkes Rad normal
        self.setMotor(speed, speed // 2)
    
    def stop(self):
        self.PWMA.duty_u16(0)
        self.PWMB.duty_u16(0)
        self.AIN2.value(0)
        self.AIN1.value(0)
        self.BIN2.value(0)
        self.BIN1.value(0)

    def setMotor(self, left, right):
        if left >= 0:
            self.AIN1.value(0)
            self.AIN2.value(1)
            self.PWMA.duty_u16(int(left * 0xFFFF / 100))
        else:
            self.AIN1.value(1)
            self.AIN2.value(0)
            self.PWMA.duty_u16(int(-left * 0xFFFF / 100))

        if right >= 0:
            self.BIN1.value(0)
            self.BIN2.value(1)
            self.PWMB.duty_u16(int(right * 0xFFFF / 100))
        else:
            self.BIN1.value(1)
            self.BIN2.value(0)
            self.PWMB.duty_u16(int(-right * 0xFFFF / 100))

# === WLAN-Verbindung ===


def read_wifi_config(filename="wlan.ini"):
    ssid = ""
    password = ""
    with open(filename) as f:
        for line in f:
            if line.startswith("ssid"):
                ssid = line.split("=", 1)[1].strip()
            elif line.startswith("password"):
                password = line.split("=", 1)[1].strip()
    return ssid, password


ssid, password = read_wifi_config()

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("📶 Verbinde mit WLAN...")
while not wlan.isconnected():
    time.sleep(1)
    blink_red(1)

ip = wlan.ifconfig()[0]
print("✅ Verbunden mit IP:", ip)
blink_green(3)

# === HTML-Steuerseite ===

html = """
<!DOCTYPE html>
<html>
<head>
  <title>Pico Go Steuerung</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: sans-serif;
      text-align: center;
      margin-top: 40px;
    }
    .dpad {
      display: grid;
      grid-template-columns: 80px 80px 80px;
      grid-template-rows: 80px 80px 80px;
      gap: 10px;
      justify-content: center;
      align-items: center;
    }
    .dpad form {
      margin: 0;
    }
    .dpad button {
      width: 80px;
      height: 80px;
      font-size: 20px;
    }
  </style>
</head>
<body>
  <h1>Pico Go Steuerung</h1>
  <div class="dpad">
    <div></div>
    <form action="/forward"><button>↑</button></form>
    <div></div>
    
    <form action="/left"><button>←</button></form>
    <form action="/stop"><button>⏹</button></form>
    <form action="/right"><button>→</button></form>
    
    <div></div>
    <form action="/backward"><button>↓</button></form>
    <div></div>
  </div>
</body>
</html>
"""


# === Roboter-Instanz ===
car = PicoGo()

# === Webserver starten ===

addr = socket.getaddrinfo("0.0.0.0", 8080)[0][-1]
server = socket.socket()
try:
    server.bind(addr)
except Exception as e:
    print("FEHLER: {}".format(e))
    while True:
        blink_red(1)
server.listen(1)
print("🌐 Webserver läuft auf http://%s:8080" % ip)
blink_green(3)

while True:
    client, addr = server.accept()
    print("🔗 Verbindung von:", addr)
    request = client.recv(1024)
    request_str = request.decode("utf-8")
    request_line = request_str.split("\r\n")[0]
    print("📥 Anfrage:", request_line)

    # Steuerbefehle
    if "GET /forward" in request_line:
        car.forward(50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /backward" in request_line:
        car.backward(50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /left" in request_line:
        car.left(50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /right" in request_line:
        car.right(50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /stop" in request_line:
        car.stop()
    elif "GET /forwardleft" in request_line:
        car.setMotor(30, 50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /forwardright" in request_line:
        car.setMotor(50, 30)
        utime.sleep(0.5)
        car.stop()
    elif "GET /backwardleft" in request_line:
        car.setMotor(-30, -50)
        utime.sleep(0.5)
        car.stop()
    elif "GET /backwardright" in request_line:
        car.setMotor(-50, -30)
        utime.sleep(0.5)
        car.stop()

    # Immer HTML ausliefern
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
    client.send(response)
    client.close()

