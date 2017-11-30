import smbus
import csv
import time
import sys
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


def write_headers_row(filename):
    with open(filename, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)


def archive_lifetester_data(packet, filename):
    with open(filename, 'ab') as archive:
        writer = csv.writer(archive)
        writer.writerow(packet)


def get_unique_filename():
    prefix = 'readings'
    device_addr = '0x%.2X' % DEVICE_ADDRESS
    date = time.strftime('%d_%b_%y-%H_%M_%S')
    suffix = '.csv'
    return '_'.join((prefix, device_addr, date, suffix))


def main_loop():
    """Main loop archiving and printing the data coming from I2c"""
    DEVICE_ADDRESS = int(sys.argv[1], base=16)
    data_file = get_unique_filename()
    write_headers_row(data_file)
    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    bus = smbus.SMBus(1)
    while True:
        sleep(SLEEP_TIME)
        block = bus.read_i2c_block_data(DEVICE_ADDRESS, 0, 18)
        reading = parse_lifetester_byte_array(block)
        print(reading)
        archive_lifetester_data(reading, data_file)


if __name__ == '__main__':
    main_loop()
