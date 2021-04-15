# for server operations
import socketio
import signal
import sys

# for GPIO operations
import RPi.GPIO as GPIO

from enum import Enum

class DeviceState(Enum):
    DIRTY = 0
    CLEAN = 1
    INUSE = 2
    PAUSE = 3

class ServerState(Enum):
    DISCONNECTED = 0
    CONNECTED = 1

# Defining GPIO pins
SENSOR_PIN = 19
CLEAN_LED = 16
INUSE_LED = 20
DIRTY_LED = 21

# define the server client
sio = socketio.Client()
add = 'http://localhost:5000' # for testing on same machine
#add = 'http://192.168.7.158:5000' # set server IP here

# The following variables contain the states for the
#   server and device states.
# They need to be modifable by multiple threads (main,
#   GPIO callback, and socketio event).
# Those other thread functions need to use the keyword
#   global so that they pick up the main thread's instance.
#
device_state = DeviceState.CLEAN    
server_state = ServerState.DISCONNECTED


def set_clean_state():
    global device_state
    P.ChangeDutyCycle(0)
    GPIO.output(DIRTY_LED, GPIO.LOW)
    GPIO.output(CLEAN_LED, GPIO.HIGH)
    device_state = DeviceState.CLEAN
    print ('set_clean_state')

def set_inuse_state():
    global device_state
    GPIO.output([CLEAN_LED, DIRTY_LED], GPIO.LOW)
    P.ChangeDutyCycle(100)
    device_state = DeviceState.INUSE
    print ('set_inuse_state')

def set_dirty_state():
    global device_state
    P.ChangeDutyCycle(0)
    GPIO.output(CLEAN_LED, GPIO.LOW)
    GPIO.output(DIRTY_LED, GPIO.HIGH)
    device_state = DeviceState.DIRTY
    print('set_dirty_state')
    
def set_pause_state():
    global device_state
    GPIO.output([CLEAN_LED, DIRTY_LED], GPIO.LOW)
    P.ChangeDutyCycle(50)
    device_state = DeviceState.PAUSE
    print('set_pause_state')
 
#sends pause state to server
def send_server_pause():
    sio.emit('my_message1','P')
    print('send_server_pause')
    
#sends clean state to server
def send_server_clean():
    sio.emit('my_message1','C')
    print('send_server_clean')
    
# no operation state   
def nop_state():
    pass

#combining device and server state to use in transion of states
def create_string_state():
    global server_state
    global device_state
    return '{0}:{1}'.format(server_state.name, device_state.name)

# The following dictionaries provide the mapping of
# states to functions.
sensor_transistion = dict()
sensor_transistion['DISCONNECTED:DIRTY'] = set_clean_state
sensor_transistion['DISCONNECTED:CLEAN'] = set_inuse_state
sensor_transistion['DISCONNECTED:INUSE'] = set_dirty_state
sensor_transistion['DISCONNECTED:PAUSE'] = nop_state
sensor_transistion['CONNECTED:DIRTY'] = send_server_clean
sensor_transistion['CONNECTED:CLEAN'] = nop_state
sensor_transistion['CONNECTED:INUSE'] = send_server_pause
sensor_transistion['CONNECTED:PAUSE'] = nop_state
    
server_transistion = dict()
server_transistion['C'] = set_clean_state
server_transistion['I'] = set_inuse_state
server_transistion['D'] = set_dirty_state
server_transistion['P'] = set_pause_state

# runs when status is received from server
# sets pins as necessary
# status_1 for when only using the in-use pin
# status_2 for when using both in-use and pause pins
def set_status(status):
    next_state = server_transistion[status]
    next_state()

# runs when client connects to server
@sio.event
def connect():
    global server_state
    print('connection established')
    server_state = ServerState.CONNECTED

# runs when 'server_message1' is received from server
@sio.event
def server_message1(data):
    print('from server: ',data)
    set_status(data)

# runs when client disconnects
@sio.event
def disconnect():
    global server_state
    print('disconnected from server')
    server_state = ServerState.DISCONNECTED
    #sys.exit(0)

# runs on keyboard interrupt - ctrl+c
def signal_handler(sig,frame):
    P.stop() # stops PWM
    GPIO.cleanup() # resets GPIO pins
    sys.exit(0)

# runs when sensor is tripped
def sensor_callback(channel): 
    print('sensor tripped')
    current = create_string_state()
    #print('current = {0}'.format(current))
    next_state = sensor_transistion[current]
    next_state()


if __name__ == '__main__':    
    # configures gpio pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup([CLEAN_LED, INUSE_LED, DIRTY_LED], GPIO.OUT)
    P = GPIO.PWM(INUSE_LED,2)
    P.start(0)
    GPIO.add_event_detect(SENSOR_PIN, GPIO.FALLING, callback=sensor_callback, bouncetime=250)
    set_clean_state()
    print('GPIO setup complete')

    # configures keyboard interrupt and server connection
    signal.signal(signal.SIGINT, signal_handler)
    sio.connect(add)
    sio.wait()
    #signal.pause()

