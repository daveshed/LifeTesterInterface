import smbus
from time import sleep

bus = smbus.SMBus(1)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

DEVICE_ADDRESS = 0x0A      #7 bit address (will be left shifted to add the read write bit)
SLEEP_TIME = 0.5

while (True):
	sleep(SLEEP_TIME)
	block = bus.read_i2c_block_data(DEVICE_ADDRESS, 0, 18)
	print block 
