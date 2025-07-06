# main.py – Pico W mit Joystick steuert Pico Go per WLAN

from time import sleep

import network
import urequests
from machine import ADC, Pin

# Pins definieren
red = Pin(2, Pin.OUT)
yellow = Pin(3, Pin.OUT)
green = Pin(4, Pin.OUT)


# === WLAN-Zugangsdaten aus externer Datei ===
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


# === WLAN-Verbindung ===
ssid, password = read_wifi_config()

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("📶 Verbinde mit WLAN...")
wait_time = 0
while not wlan.isconnected() and wait_time < 15:
    print(".", end="")
    yellow.on()
    sleep(1)
    yellow.off()
    wait_time += 1

if not wlan.isconnected():
    print("\n❌ WLAN-Verbindung fehlgeschlagen.")
    raise RuntimeError("Keine WLAN-Verbindung")
    while True:
        red.on()
        sleep(0.5)
else:
    print("\n✅ Verbunden mit IP:", wlan.ifconfig()[0])
    green.on()

# === Ziel: IP des fahrenden Pico Go ===
PICO_GO_IP = "192.168.178.186"
BASE_URL = f"http://{PICO_GO_IP}:8080"

# === Joystick Setup ===
led_onboard = Pin(25, Pin.OUT, value=0)
btn = Pin(22, Pin.IN, Pin.PULL_UP)
adc_x = ADC(0)  # GPIO26
adc_y = ADC(1)  # GPIO27

# === Steuerung ===
last_command = None


def send_command(command):
    global last_command
    if command == last_command:
        return  # keine Wiederholung
    try:
        url = f"{BASE_URL}/{command}"
        print(f"→ Sende: {url}")
        urequests.get(url)
        last_command = command
    except Exception as e:
        print(f"⚠️ Verbindung fehlgeschlagen: {e}")


# === Hauptloop ===
while True:
    x = adc_x.read_u16()
    y = adc_y.read_u16()
    button = not btn.value()  # gedrückt = True

    led_onboard.value(button)

    # Richtung interpretieren
    direction = None

    if x < 29000:
        direction = "right"
    elif x > 36000:
        direction = "left"
    elif y < 29000:
        direction = "forward"
    elif y > 36000:
        direction = "backward"
    elif button:
        direction = "stop"

    if direction:
        send_command(direction)

    sleep(0.2)
