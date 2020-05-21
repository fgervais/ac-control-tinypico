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



ir_transmitter = IRTransmitter(Pin(TRANSMITTER_PIN))

spi = SPI(sck=Pin(TinyPICO.DOTSTAR_CLK),
          mosi=Pin(TinyPICO.DOTSTAR_DATA),
          miso=Pin(TinyPICO.SPI_MISO))
dotstar = DotStar(spi, 1, brightness=0.0)
dotstar[0] = (0, 188, 255, 0.5)
TinyPICO.set_dotstar_power(True)

button = Pin(33, Pin.IN)

while True:
    # ir_transmitter.play(ir_code.POWER_ON)

    if button.value() == 0:

        for i in range(4):
            dotstar.brightness = 0.5
            time.sleep(0.05)
            dotstar.brightness = 0
            time.sleep(0.05)


    # time.sleep(2)


# ir_transmitter = PWM(Pin(TRANSMITTER_PIN), freq=38000, duty=0)
# ir_transmitter.duty(512)













while True:
    pass



BEACON_VPIN = 1
LEAK_LED_VPIN = 2
CHARGING_VPIN = 3

LEAK_CAP_THRESHOLD = 50

LEAK_TOUCHPAD_PIN = 33
BUZZER_PIN = 25


wlan = network.WLAN(network.STA_IF)
def connect():
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(secret.ESSID, secret.PSK)
        while not wlan.isconnected():
            time.sleep(1)
    print('network config:', wlan.ifconfig())

def is_leak():
    try:
        if leak_detect_pad.read() < LEAK_CAP_THRESHOLD:
            return True
    except:
        return True

    return False

def show_leak_cap_value():
    try:
        value = leak_detect_pad.read()
    except:
        value = 0

    print("Leak capacitance: " + str(value))

def usb_connected():
    return (TinyPICO.get_battery_voltage() == 3.7)


class Device:
    def __init__(self, blynk, buzzer_pwm, wifi_connect_function):
        self.blynk = blynk
        self.buzzer_pwm = buzzer_pwm
        self.wifi_connect_function = wifi_connect_function

        self.connected = False

    def connect(self):
        if not self.connected:
            self.wifi_connect_function()
            self.blynk.connect()
            self.connected = True

    def blynk_virtual_write(self, vpin, value):
        self.connect()

        self.blynk.virtual_write(vpin, value)
        self.blynk.run()

    def blynk_notify(self, msg):
        self.connect()

        self.blynk.notify(msg);
        self.blynk.run()

    def beacon(self):
        self.blynk_virtual_write(
            BEACON_VPIN,
            TinyPICO.get_battery_voltage())

    def alarm(self, seconds):
        start_time = time.time()
        while time.time() < start_time + seconds:
            for i in range(3):
                self.buzzer_pwm.duty(512)
                time.sleep(0.25)
                self.buzzer_pwm.duty(0)
                time.sleep(0.25)

    @property
    def leak_led(self):
        return False

    @leak_led.setter
    def leak_led(self, state):
        self.blynk_virtual_write(LEAK_LED_VPIN, 255 if state else 0)

    @property
    def charging(self):
        return False

    @charging.setter
    def charging(self, state):
        self.blynk_virtual_write(CHARGING_VPIN, 255 if state else 0)

    def leak_detected(self):
        self.leak_led = True
        self.blynk_notify("A leak has been detected!");

    def teardown(self):
        if self.connected:
            self.blynk.disconnect()


initial_buzzer_duty = 0
if machine.reset_cause() == machine.PWRON_RESET:
    initial_buzzer_duty = 512

buzzer = PWM(Pin(BUZZER_PIN), freq=4000, duty=initial_buzzer_duty)
time.sleep(0.05)
buzzer.duty(0)

leak_detect_pad = TouchPad(Pin(LEAK_TOUCHPAD_PIN))
leak_detect_pad.config(LEAK_CAP_THRESHOLD)

rtc = RTC()
print("RTC memory: {}".format(rtc.memory()))
error_reported = True if rtc.memory() else False

blynk = blynklib.Blynk(secret.BLYNK_AUTH, log=print)
dishwasher = Device(blynk, buzzer, connect)

show_leak_cap_value()

if not is_leak():
    print("There is no leak")
    dishwasher.leak_led = False
    dishwasher.beacon()
    esp32.wake_on_touch(True)
    sleep_time = 7 * 24 * 60 * 60 * 1000 # 1 week

    print("Let say we are not charging")
    dishwasher.charging = False

else:
    print("A leak has been detected!")
    if not error_reported:
        dishwasher.leak_detected()
        rtc.memory(b'\x01')

    dishwasher.alarm(60)

    esp32.wake_on_touch(False)
    sleep_time = 0 # forever


dishwasher.teardown()

if wlan.isconnected():
    wlan.disconnect()
    while wlan.isconnected():
        time.sleep(1)

print("Going to sleep")
TinyPICO.go_deepsleep(sleep_time)

print("not reached")

while True:
    pass
