import smbus
from time import sleep

bus = smbus.SMBus(1)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

DEVICE_ADDRESS = 0x0A   #7 bit address (will be left shifted to add the read write bit)
SLEEP_TIME = 1		#sec

# take bytes as list and return int - little endian (LSB on the left)
def bytes_to_int(bytes):
	x = 0
	shift = 0    
	for byte in bytes:
        	x |= (byte << shift)
		shift += 8
	return x

# parse byte array to data
def parse_lifetester_byte_array(bytes):
	data = {
	'time' : bytes_to_int(bytes[0:4]),
	'v_a' : bytes_to_int(bytes[4:6]),
	'i_a' : bytes_to_int(bytes[6:8]),
	'v_b' : bytes_to_int(bytes[8:10]),
	'i_b' : bytes_to_int(bytes[10:12]),
	'temperature' : bytes_to_int(bytes[12:14]),
	'light_intensity' : bytes_to_int(bytes[14:16]),
	'error_a' : bytes[16],
	'error_b' : bytes[17]
	}
	return data

def display_lifetester_data(data):
	print "t%r: ch_A(v%r, i%r, err%r) ch_B(v%r, i%r, err%r) temp %r intensity %r" % (data['time'], data['v_a'], data['i_a'], data['error_a'], data['v_b'], data['i_b'], data['error_b'], data['temperature'], data['light_intensity'])

while (True):
	sleep(SLEEP_TIME)
	block = bus.read_i2c_block_data(DEVICE_ADDRESS, 0, 18)
	#print block
	lifetester_data = parse_lifetester_byte_array(block)
	display_lifetester_data(lifetester_data)

