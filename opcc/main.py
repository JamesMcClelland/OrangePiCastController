import OPi.GPIO as GPIO
import time
import os
import telnetlib
import socket
import json, numpy
import spidev
from threading import Timer

RoAPin = 8
RoBPin = 14
RoSPin = 15

globalCounter = 0

flag = 0
Last_RoB_Status = 0
Current_RoB_Status = 0
this_host_id = ""
this_host_volume = 0

host = "192.168.0.28"
tn = telnetlib.Telnet(host, 1705, 5)

spi = spidev.SpiDev()
spi.open(1,0)

if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                ifname[:15]))[20:24])


def get_lan_ip():
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = [
            "eth0",
            "eth1",
            "eth2",
            "wlan0",
            "wlan1",
            "wifi0",
            "ath0",
            "ath1",
            "ppp0",
            ]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break
            except IOError:
                pass
    return ip


# Function derived from https://github.com/joosteto/ws2812-spi
def write2812_pylist4(spi, color_data):
    tx=[0x00]
    for rgb in color_data:
        for byte in rgb:
            for ibit in range(3,-1,-1):
                tx.append(((byte>>(2*ibit+1))&1)*0x60 +
                          ((byte>>(2*ibit+0))&1)*0x06 +
                          0x88)
    spi.xfer(tx, int(4/1.05e-6))


def clear_ws2812(spi):
    write2812_pylist4(spi, [[0,0,0]*12])


def make_request(tel, to_send):
    tel.write(to_send + '\r\n')
    data = tel.read_until("\r\n")
    return json.loads(data)


def get_host_info(tel):
    self_ip = get_lan_ip()
    read_data = make_request(tel, '{"id":8,"jsonrpc":"2.0","method":"Server.GetStatus"}')
    for group in read_data['result']['server']['groups']:
        for client in group['clients']:
            check_ip = client['host']['ip']
            check_ip = check_ip.replace("::ffff:", "")
            if check_ip == self_ip:
                return client['id'], client['config']['volume']
    return False


def set_host_volume(tel, host_id, vol):
    read_data = make_request(tel, '{"id":8,"jsonrpc":"2.0","method":"Client.SetVolume","params":{"id":"' + str(host_id) +
                             '","volume":{"muted":false,"percent":' + str(vol) + '}}}')
    print(read_data)


def volume_led_color(volume):
    global spi
    print(volume)
    multi = 8.33 # 100 / 12
    full_lit = int(volume // multi)
    remainder = int(((volume / multi) - full_lit) * 20)
    print(full_lit)
    print(remainder)
    clear_ws2812(spi)
    if full_lit > 0 :
        write2812_pylist4(spi, [[20, 20, 20] * full_lit, [remainder, remainder, remainder]])
    else:
        write2812_pylist4(spi, [[remainder, remainder, remainder]])


def volume_update_bounce():
    global this_host_id
    global this_host_volume
    set_host_volume(tn, this_host_id, this_host_volume)
    vol_bounce_timer = Timer(0.2, volume_update_bounce)


def setup():
    global this_host_id
    global vol_bounce_timer
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RoAPin, GPIO.IN)    # input mode
    GPIO.setup(RoBPin, GPIO.IN)
    GPIO.setup(RoSPin, GPIO.IN)
    host_info = get_host_info(tn)
    this_host_id = host_info[0]
    rotary_clear()
    vol_bounce_timer = Timer(0.2, volume_update_bounce)


def rotary_deal():
    global flag
    global Last_RoB_Status
    global Current_RoB_Status
    global globalCounter
    global this_host_volume
    global vol_bounce_timer
    Last_RoB_Status = GPIO.input(RoBPin)
    while not GPIO.input(RoAPin):
        Current_RoB_Status = GPIO.input(RoBPin)
        flag = 1
    if flag == 1:
        flag = 0
        if (Last_RoB_Status == 0) and (Current_RoB_Status == 1):
            if globalCounter < 20:
                globalCounter = globalCounter + 1
            # print('globalCounter = %d' % globalCounter)
        if (Last_RoB_Status == 1) and (Current_RoB_Status == 0):
            if globalCounter > 0:
                globalCounter = globalCounter - 1
            # print('globalCounter = %d' % globalCounter)

        this_host_volume = globalCounter * 5

        volume_led_color(this_host_volume)
        # Recreating the timer so API is only hit if a change has been longer than 0.1 seconds ago
        vol_bounce_timer.cancel()
        vol_bounce_timer = Timer(0.1, volume_update_bounce)
        vol_bounce_timer.start()


def clear():
    global globalCounter
    globalCounter = 0
    print('globalCounter = %d' % globalCounter)
    time.sleep(1)


def rotary_clear():
    GPIO.add_event_detect(RoSPin, GPIO.BOTH, clear)


def loop():
    global globalCounter
    while True:
        rotary_deal()


def destroy():
    GPIO.cleanup()             # Release resource


setup()
try:
    loop()
except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
    destroy()