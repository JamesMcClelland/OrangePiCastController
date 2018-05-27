import OPi.GPIO as GPIO
from time import sleep

clk = 8
dt = 14

GPIO.cleanup()

GPIO.setmode(GPIO.BCM)
GPIO.setup(clk, GPIO.IN)
GPIO.setup(dt, GPIO.IN)

counter = 0
clkLastState = 0
dtLastState = 0

bitString = ""

def checkString():
    global bitString
    if len(bitString) == 4:
        print("Check Byte Now")
        if int(bitString, 2) == 6:
            print "CCW"
        elif int(bitString, 2) == 10:
            print "CW"
        bitString = ""

def clkCallback(channel):
    global bitString
    print('Callback one')
    bitString += "0"
    checkString()

def dtCallback(channel):
    global bitString
    print('Callback two')
    bitString += "1"
    checkString()

GPIO.add_event_detect(clk, GPIO.BOTH)
GPIO.add_event_callback(clk, clkCallback)

GPIO.add_event_detect(dt, GPIO.BOTH)
GPIO.add_event_callback(dt, dtCallback)


try:

        while True:
                sleep(0.01)
finally:
        GPIO.cleanup()
