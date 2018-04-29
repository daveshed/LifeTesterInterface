from smbus2 import SMBus, i2c_msg  # python3
import csv
import time
import sys
from collections import namedtuple
from time import sleep

# sec delay between measurements
SLEEP_TIME = 1
POLL_DELAY = 0.01
# I2C settings :
DEVICE_ADDRESS = 0X0A
I2C_BUS = 1  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
# I2C commands :
RESET_CH_A = 0x3
RESET_CH_B = 0x83
READ_CMD_REG = 0x0
WRITE_CMD_REG = 0x40
WRITE_CH_B_CMD = 0xC0
READ_CH_A_DATA = 0x2
READ_CH_B_DATA = 0x82
READ_PARAMS = 0x1
WRITE_PARAMS = 0x41
# Register map
ERR_OFFSET = 3
ERR_MASK = 3
RDY_OFFSET = 5
# Data conversion factors
DAC_GAIN = 1.0
DAC_RESOLUTION = 8
DAC_VREF = 2.048
DAC_CONVERSION = DAC_VREF * DAC_GAIN / 2**DAC_RESOLUTION
SENSE_RESISTOR = 10.0  # Ohms
R_F = 249.0
R_IN = 1.0
OPAMP_GAIN = R_F / R_IN
ADC_VREF = 2.5
ADC_RESOLUTION = 16
ADC_CONVERSION = ADC_VREF / (2**ADC_RESOLUTION * OPAMP_GAIN * SENSE_RESISTOR)
TEMP_CONVERSION = 0.0625  # Deg C per code
ERROR_CODES = ['ok', 'low_current', 'current_limit', 'threshold']

# A single measurement at given time on a single channel
DataPacket = namedtuple('DataPacket',
                        'time, voltage, current, temperature, light_intensity, error_code, checksum')
ParamsPacket = namedtuple('ParamsPacket',
                          'settle_time, track_delay, sample_time, '
                          'threshold_current')
# Measurement record to be saved to file
HEADERS = 'time, v_a, i_a, v_b, i_b, temperature, light_intensity, error_a, error_b'
Measurement = namedtuple('Measurement', HEADERS)
# Size (bytes) of each variable in a packet
num_bytes = DataPacket(time=4, voltage=1, current=2, temperature=2,
                       light_intensity=2, error_code=1, checksum=1)
DATA_PACKET_SIZE = sum(list(num_bytes))
PARAMS_PACKET_SIZE = 8  # bytes - 2 bytes per param
BYTES_PER_PARAM = 2


def write_headers_row(filename):
    with open(filename, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)


def archive_lifetester_data(packet, filename):
    with open(filename, 'a') as archive:
        writer = csv.writer(archive)
        writer.writerow(packet)


def get_unique_filename():
    prefix = 'readings'
    device_addr = '0x%.2X' % DEVICE_ADDRESS
    date = time.strftime('%d_%b_%y-%H_%M_%S')
    suffix = '.csv'
    return '_'.join((prefix, device_addr, date, suffix))


class LifeTester:
    # Todo: what if two instances are created with the same address?

    def __init__(self, addr):
        self.addr = addr
        self.bus = SMBus(I2C_BUS)

    def reset(self):
        """Resets both lifetester channels"""
        self._send_command(WRITE_CMD_REG)
        self._send_command(RESET_CH_A)
        self._poll_ready_state()
        self._send_command(WRITE_CMD_REG)
        self._send_command(RESET_CH_B)
        self._poll_ready_state()

    def set_params(self, new_params):
        """Sets the measurement parameters"""
        # note that polling doesn't work in this case
        self._send_command(WRITE_CMD_REG)
        self._send_command(WRITE_PARAMS)
        self._write_block_data(self._parse_bytes_from_params(new_params))

    def get_params(self):
        """Gets the current measurement parameters"""
        self._send_command(WRITE_CMD_REG)
        self._poll_ready_state()
        self._send_command(READ_PARAMS)
        self._poll_ready_state()
        params_bytes = self._read_block_data(PARAMS_PACKET_SIZE)
        return self._parse_params_from_bytes(params_bytes)

    def get_error_code(self):
        """get the error code from the command register"""
        cmd = self._read_command_reg()
        return (cmd >> ERR_OFFSET) & ERR_MASK

    def get_data(self):
        """Reads and returns data from channel A and B"""
        self._send_command(WRITE_CMD_REG)
        self._poll_ready_state()
        self._send_command(READ_CH_A_DATA)
        self._poll_ready_state()
        data_block_a = self._read_block_data(DATA_PACKET_SIZE)
        packet_a = self._parse_data(data_block_a)
        self._send_command(WRITE_CMD_REG)
        self._poll_ready_state()
        self._send_command(READ_CH_B_DATA)
        self._poll_ready_state()
        data_block_b = self._read_block_data(DATA_PACKET_SIZE)
        packet_b = self._parse_data(data_block_b)
        return self._parse_measurement(packet_a, packet_b)

    def _bytes_to_int(self, b):
        return int.from_bytes(b, byteorder='little', signed=False)

    def _dequeue(self, l, n):
        # pops a list, l, of length n from another list
        return [l.pop(0) for e in range(n)]

    def _parse_data(self, b):
        # Todo: catch empty list exception - assert len(b)?
        tmp = [self._bytes_to_int(self._dequeue(b, field))
               for field in list(num_bytes)]
        return DataPacket._make(tmp)

    def _parse_params_from_bytes(self, b):
        # Todo: catch empty list exception - assert len(b)?
        tmp = [self._bytes_to_int(self._dequeue(b, BYTES_PER_PARAM))
               for p in ParamsPacket._fields]
        return ParamsPacket._make(tmp)

    def _parse_bytes_from_params(self, params):
        msb = lambda x: x >> (8 & 0xFF)
        lsb = lambda x: x & 0xFF
        return [f(p) for p in params for f in [lsb, msb]]

    def _send_command(self, cmd):
        sleep(POLL_DELAY)
        self.bus.write_byte_data(self.addr, cmd, 0)

    def _read_byte(self):
        return self.bus.read_byte_data(self.addr, 0)

    def _read_block_data(self, num_bytes):
        msg = i2c_msg.read(self.addr, num_bytes)
        self.bus.i2c_rdwr(msg)
        return list(msg)

    def _write_block_data(self, data):
        msg = i2c_msg.write(self.addr, data)
        self.bus.i2c_rdwr(msg)

    def _read_command_reg(self):
        self._send_command(READ_CMD_REG)
        return self._read_byte()

    def _is_ready(self):
        cmd_reg = self._read_command_reg()
        mask = 1 << RDY_OFFSET
        return (bool)(cmd_reg & mask)

    def _poll_ready_state(self):
        while not self._is_ready():
            sleep(POLL_DELAY)

    def _convert_to_temp(self, reg):
        # Turn 16 bit wide register to temperature float
        return int(reg >> 3) * TEMP_CONVERSION

    def _parse_error_code(self, byte):
        if byte < len(ERROR_CODES):
            return ERROR_CODES[byte]
        else:
            return 'unkown'

    def _parse_measurement(self, a, b):
        measurement = Measurement(
            time=a.time,
            v_a=a.voltage * DAC_CONVERSION,
            i_a=a.current * ADC_CONVERSION,
            v_b=b.voltage * DAC_CONVERSION,
            i_b=b.voltage * ADC_CONVERSION,
            temperature=self._convert_to_temp(a.temperature),
            light_intensity=a.light_intensity,
            error_a=self._parse_error_code(a.error_code),
            error_b=self._parse_error_code(b.error_code))
        return measurement


def main_loop():
    """Main loop archiving and printing the data coming from I2c"""
    DEVICE_ADDRESS = int(sys.argv[1], base=16)
    lt = LifeTester(DEVICE_ADDRESS)
    default_params = ParamsPacket(
            settle_time=100,
            track_delay=1000,
            sample_time=100,
            threshold_current=100)
    data_file = get_unique_filename()
    write_headers_row(data_file)
    # TODO: Handle cmd reg error and chksum
    while True:
        sleep(SLEEP_TIME)
        measurement = lt.get_data()
        print(measurement)
        archive_lifetester_data(measurement, data_file)


if __name__ == '__main__':
    main_loop()
