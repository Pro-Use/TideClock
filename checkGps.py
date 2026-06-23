import pps_tools
from gpiozero import OutputDevice
from time import time, sleep

LED = OutputDevice(22)
ledState = False

with pps_tools.PpsFile("/dev/pps0") as ppsf:
    while True:
        try:
            edge = ppsf.fetch(timeout=2)
            print(f"Edge: {edge}")
            print(f"Time diff: {time() - edge['assert_time']}")
            LED.toggle()
            print(f"LED state: {LED.value}")
        except TimeoutError:
            print("Timeout waiting for PPS signal")
            LED.off()