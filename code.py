import time
import os
import busio
import digitalio
import board
import storage
import digitalio
import adafruit_sdcard

# global variables for timer callback
##led = Pin(25, Pin.OUT)
led = digitalio.DigitalInOut(board.GP25)
led.direction = digitalio.Direction.OUTPUT
LED_state = True

# Set rtc from GPS date time 
    
# Timer to blink status LED on pico
def tick():
    global led, LED_state
    LED_state = not LED_state
    led.value = LED_state

# Flash led quickly
def flash():
    global led, LED_state
    led.value = True
    time.sleep( 0.25 )
    led.value = False

# Crude debounce
# Return True if sw_pin in in desired_state for delay seconds
# False otherwise
def debounce_input ( sw_pin, desired_state, delay ):
    val = sw_pin.value
    #print( str(val ))
    if val == desired_state:
        time.sleep( delay )
        val = sw_pin.value
        if val == desired_state:
            return True
        else:
            return False
    return False

# Log GPS $GPRMC sentences to file until interrupted
# by button push
def write_file( fname, comm, sw_pin ):
    n_samples = 0
    f = open( '/sd/' + fname, 'w' )
    result = False
    while result != True:
        sentence = read_gps( comm )
        #print( sentence )
        pat = sentence.startswith( '$GPRMC')
        if pat:
            print( sentence )
            f.write(sentence + '\r\n')
            n_samples += 1
            if n_samples % 10 == 0:
                flash()
            if debounce_input( sw_pin, 0, 0.25):
                result = True
                f.close()

# start file system
def mount_sd_card( spi, cs ):
    mounted = False
    while mounted == False:
        try:
            sdcard = adafruit_sdcard.SDCard(spi, cs)
            vfs = storage.VfsFat(sdcard)
            storage.mount(vfs, "/sd")       
            mounted = True
        except OSError as e:
            print( "mount: OSError = " + str(e))
            time.sleep(2)

# Clean up GPS sentences in case of garbage
def read_gps( port ):
    result = port.readline( )
    try:
        result = result.decode("utf-8")
    except:
        result = ''
    return result.strip()

# Build a filename from GPS date and time
# get the date time from GPS and use this to create a unique
# filename
def get_fname( comm ):
    sentence = read_gps( comm )
    pat = sentence.startswith( '$GPRMC')
    while pat != True:
        sentence = read_gps( comm )
        pat = sentence.startswith( '$GPRMC')

    #print( sentence )
    time.sleep( 2 )
    field_list = sentence.split( ',')
    time_list = field_list[1].split( '.')
    fname = 'F' + field_list[9]  + '_' + time_list[0] + '.csv'
    #print( 'File name is ' + fname )
    return fname

def main( ):

    print( "Starting...")

    # Connect to the card and mount the filesystem
    spi = busio.SPI(clock=board.GP6, MOSI=board.GP7, MISO=board.GP4)
    cs = digitalio.DigitalInOut(board.GP8)
    
    # uart tx 0, uart rx 1
    # init with appropriate baudrate
    comm = busio.UART(tx=board.GP0, rx=board.GP1, baudrate=9600)

    # Set the hardware clock from GPS time
    #setGPSTime( "1234" )

    # Set up blink timer
    #blink_timer = Timer()

    # start file system
    mount_sd_card( spi, cs )
    print( "/sd mounted")

    # setup to look for button press (move to next file)
    sw_pin = digitalio.DigitalInOut(board.GP10)
    sw_pin.pull = digitalio.Pull.UP

    # Initial state is waiting to log
    #blink_timer.init(freq=5, mode=Timer.PERIODIC, callback=tick)

    # Read GPS, log to sd card file
    while True:
        # Wait to start next file until button pressed
        result = debounce_input( sw_pin, 0, 0.25 )
        #result = True
        while result == False:
            time.sleep(0.5)
            tick()
            result = debounce_input( sw_pin, 0, 0.25 )

        fname = get_fname( comm )
        print( "opened file " + fname)

        # Slow down flashing LED to 1 per second when recording
        #blink_timer.init(freq=1, mode=Timer.PERIODIC, callback=tick)
        write_file( fname, comm, sw_pin )
        print( "closed file " + fname )
        time.sleep(1.0)

        # Speed up LED blink when paused
        #blink_timer.init(freq=5, mode=Timer.PERIODIC, callback=tick)

if __name__ == "__main__":
    main( )