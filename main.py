import network
import time
import tinypico as TinyPICO
import micropython
import esp32
import blynklib_mp as blynklib
import secret
import machine
import ir_code

from machine import Pin, PWM, ADC, TouchPad, RTC, SPI
from dotstar import DotStar


TRANSMITTER_PIN = 25

LED_BRIGHTNESS = 0.5

BUTTON_VPIN = 0
LED_VPIN = 1


class IRTransmitter:
    def __init__(self, pin):
        self.pwm_pin = PWM(pin, freq=38000, duty=0)

    def pulse(self, length_us):
        self.pwm_pin.duty(512)
        time.sleep_us(length_us)
        self.pwm_pin.duty(0)

    def space(self, length_us):
        self.pwm_pin.duty(0)
        time.sleep_us(length_us)

    def play(self, code):
        send_pulse = True

        for i in code:
            if send_pulse:
                self.pulse(i)
            else:
                self.space(i)

            send_pulse = not send_pulse


def connect():
    wlan.active(True)
    if not wlan.isconnected():
        print("connecting to network...")
        wlan.connect(secret.ESSID, secret.PSK)
        while not wlan.isconnected():
            time.sleep(1)
    print("network config:", wlan.ifconfig())


def show_feedback():
    for i in range(4):
        dotstar.brightness = LED_BRIGHTNESS
        time.sleep(0.05)
        dotstar.brightness = 0
        time.sleep(0.05)


ir_transmitter = IRTransmitter(Pin(TRANSMITTER_PIN))
wlan = network.WLAN(network.STA_IF)

spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK),
          mosi=Pin(TinyPICO.DOTSTAR_DATA),
          miso=Pin(TinyPICO.SPI_MISO))
dotstar = DotStar(spi, 1, brightness=0.0)
dotstar[0] = (0, 188, 255, 0.5)
TinyPICO.set_dotstar_power(True)
syncing = True

connect()
blynk = blynklib.Blynk(secret.BLYNK_AUTH, log=print)

@blynk.handle_event("write V" + str(BUTTON_VPIN))
def write_handler(pin, value):
    if int(value[0]) == 1:
        ir_transmitter.play(ir_code.POWER_ON)
    else:
        ir_transmitter.play(ir_code.POWER_OFF)

    show_feedback()

@blynk.handle_event("write V" + str(LED_VPIN))
def write_handler(pin, value):
    dotstar[0] = tuple(map(int, value))

    if not syncing:
        dotstar.brightness = LED_BRIGHTNESS
        time.sleep(1)
        dotstar.brightness = 0.0


blynk.run()
blynk.virtual_sync(LED_VPIN)
blynk.run()
syncing = False

while True:
    blynk.run()
