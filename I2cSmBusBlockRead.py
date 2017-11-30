import smbus
from collections import namedtuple
from time import sleep

# 7 bit address (will be left shifted to add the read write bit)
DEVICE_ADDRESS = 0x0A
SLEEP_TIME = 1  # sec
HEADERS = (
    'time',
    'v_a', 'i_a',
    'v_b', 'i_b',
    'temperature', 'light_intensity',
    'error_a', 'error_b',
)

# A single measurement at given time
Packet = namedtuple('Packet', HEADERS)


def bytes_to_int(bytes):
    """take bytes as list and return int - little endian (LSB on the left)"""
    x = 0
    shift = 0
    for byte in bytes:
        x |= (byte << shift)
        shift += 8
    return x


def parse_lifetester_byte_array(bytes):
    """Return a packet representing a single point measurement."""
    packet = Packet(
        bytes_to_int(bytes[0:4]),
        bytes_to_int(bytes[4:6]),
        bytes_to_int(bytes[6:8]),
        bytes_to_int(bytes[8:10]),
        bytes_to_int(bytes[10:12]),
        bytes_to_int(bytes[12:14]),
        bytes_to_int(bytes[14:16]),
        bytes[16],
        bytes[17],
    )
    return packet


def archive_lifetester_data(data):
    with open('data.csv', w):
        pass


def main_loop():
    """Main loop archiving and printing the data coming from I2c"""
    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    bus = smbus.SMBus(1)
    while True:
        sleep(SLEEP_TIME)
        block = bus.read_i2c_block_data(DEVICE_ADDRESS, 0, 18)
        lifetester_data = parse_lifetester_byte_array(block)
        print(lifetester_data)
        archive_lifetester_data(data)


if __name__ == '__main__':
    main_loop()
