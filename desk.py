# for server operations
import socketio
import signal
import sys

# for GPIO operations
import RPi.GPIO as GPIO

# Defining GPIO pins
SENSOR_PIN = 19
CLEAN_LED = 16
IN_USE_LED = 20
DIRTY_LED = 21

# define the server client
sio = socketio.Client()
#add = 'http://localhost:5000' # for testing on same machine
add = 'http://192.168.7.158:5000' # set server IP here


# runs when status is received from server
# sets pins as necessary
# status_1 for when only using the in-use pin
# status_2 for when using both in-use and pause pins
def set_status(status):
    if status == 'C':
        P.ChangeDutyCycle(0)
        GPIO.output(DIRTY_LED, GPIO.LOW)
        GPIO.output(CLEAN_LED, GPIO.HIGH)
        #print('status set to clean')

    elif status == 'I':
        GPIO.output([CLEAN_LED, DIRTY_LED], GPIO.LOW)
        P.ChangeDutyCycle(100)
        #print('status set to in-use')

    elif status == 'D':
        P.ChangeDutyCycle(0)
        GPIO.output(CLEAN_LED, GPIO.LOW)
        GPIO.output(DIRTY_LED, GPIO.HIGH)
        #print('status set to dirty')

    elif status == 'P':
        GPIO.output([CLEAN_LED, DIRTY_LED], GPIO.LOW)
        P.ChangeDutyCycle(50)
        #print('status set to pause')


# runs when client connects to server
@sio.event
def connect():
    print('connection established')

# runs when 'server_message1' is received from server
@sio.event
def server_message1(data):
    print('from server: ',data)
    set_status(data)

# runs when client disconnects
@sio.event
def disconnect():
    print('disconnected from server')
    #sys.exit(0)

# runs on keyboard interrupt - ctrl+c
def signal_handler(sig,frame):
    P.stop() # stops PWM
    GPIO.cleanup() # resets GPIO pins
    sys.exit(0)

# runs when sensor is tripped
def sensor_callback(channel):
    print('sensor tripped')
    if GPIO.input(IN_USE_LED):
        sio.emit('my_message1','P') # sends pause state to server
    elif GPIO.input(DIRTY_LED):
        sio.emit('my_message1','C') # sends clean state to server


if __name__ == '__main__':

    # configures gpio pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup([CLEAN_LED, IN_USE_LED, DIRTY_LED], GPIO.OUT)
    P = GPIO.PWM(IN_USE_LED,2)
    P.start(0)
    GPIO.add_event_detect(SENSOR_PIN, GPIO.RISING, callback=sensor_callback, bouncetime=50)
    set_status('C') # set initial status
    print('GPIO setup complete')

    # configures keyboard interrupt and server connection
    signal.signal(signal.SIGINT, signal_handler)
    sio.connect(add)
    sio.wait()
    #signal.pause()
