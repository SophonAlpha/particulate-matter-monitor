import time
import serial
import logging.handlers

class SHDLC:
    def __init__(self):
        self.buffer_size = 64
        self.port = self.open_serial_port()

    def open_serial_port(self):
        port = serial.Serial('/dev/serial0',
                             baudrate=115200,
                             parity=serial.PARITY_NONE,
                             stopbits=serial.STOPBITS_ONE,
                             bytesize=serial.EIGHTBITS,
                             timeout=1.5)
        if port.isOpen():
            port.close()
        port.open()
        return port

    def close_serial_port(self):
        self.port.close()

    def send_command(self, cmd, data):
        mosi_frame = build_mosi_frame(cmd, data)
        my_logger.info(miso_frame)
        self.port.write(mosi_frame)
        return

    def get_response(self):
        data = self.port.read(self.buffer_size)
        miso_frame = ' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))])
        my_logger.info(miso_frame)
        return data


class Commands:
    def __init__(self):
        self.start_measurement = bytes.fromhex('00')
        self.stop_measurement = bytes.fromhex('01')
        self.read_measured_values = bytes.fromhex('03')
        self.read_auto_cleaning_interval = bytes.fromhex('80')
        self.write_auto_cleaning_interval = bytes.fromhex('80')
        self.start_fan_cleaning = bytes.fromhex('56')
        self.device_information = bytes.fromhex('D0')
        self.device_reset = bytes.fromhex('D3')


class SensirionSPS30:
    def __init__(self):
        self.shdlc = SHDLC()
        self.cmd = Commands()

    def start_measurement(self):
        self.shdlc.send_command(self.cmd.start_measurement, '')
        rsp = self.shdlc.get_response()

    def stop_measurement(self):
        pass

    def read_measurement_values(self):
        pass

    def read_auto_cleaning_interval(self):
        pass

    def write_auto_cleaning_interval(self):
        pass

    def start_fan_cleaning(self):
        pass

    def get_device_information(self):
        pass

    def device_reset(self):
        pass


def build_mosi_frame(command, data=''):
    """
    Build the MOSI frame according to specification "Datasheet SPS30
    Particulate Matter Sensor for Air Quality Monitoring and Control",
    section "4.1 SHDLC Frame Layer"

    :param command: the UART / SHDLC command. See also "Datasheet SPS30
    Particulate Matter Sensor for Air Quality Monitoring and Control",
    section "4.2 UART / SHDLC Commands"
    :param data: the command data
    :return: the MOSI frame as string of bytes in hex notation
    """

    frame = []
    frame.append('7E')  # start
    frame.append('00')  # address
    frame.append(command)  # command
    frame.append('{:02x}'.format(len(data.split())))  # length
    frame.append(''.join(data.split())) # TX data
    check = calculate_checksum([int(frame[1], 16), int(frame[2], 16),
                                int(frame[3], 16)] + [int(byte, 16)
                                                      for byte in data.split()])
    check = '{:02x}'.format(check)
    frame.append(check)  # check
    frame.append('7E')  # stop
    frame = [byte.upper() for byte in frame]
    frame = byte_stuffing(frame)
    frame = ''.join(frame)
    return frame


def calculate_checksum(data):
    """
    Calculate frame checksum.

    :param data: list of frame content bytes in int format
    :return: checksum as int
    """

    # Sum all bytes between start and stop (without start and stop bytes).
    checksum = sum(data)
    # Take the LSB of the result ...
    checksum = checksum & 0xFF
    # ... and invert it. This will be the checksum.
    checksum = ~checksum & 0xFF
    return checksum


def byte_stuffing(frame):
    """
    The 0x7E character is sent at the beginning and at the end of the frame to
    signalize frame start and stop. If this byte (0x7E) occurs anywhere else in
    the frame, it must be replaced by two other bytes (byte-stuffing).
    This also applies to the characters 0x7D, 0x11 and 0x13.

    :param frame: the frame a list of hex values in string format
    :return: new 'byte stuffed' frame
    """
    stuffing = {
        '7E': ['7D', '5E'],
        '7D': ['7D', '5D'],
        '11': ['7D', '31'],
        '13': ['7D', '33'],
    }
    new_frame = []
    new_frame.append(frame[0])  # add start frame
    for index, byte in enumerate(frame[1:-1]):
        if byte in stuffing.keys():
            new_frame.extend(stuffing[byte])
        else:
            new_frame.append(byte)
    new_frame.append(frame[-1])  # add end frame
    return new_frame


# print('start particle measurement ...')
# port.write(START_MEASUREMENT)
# data = port.read(16)
# print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
# print()
#
# print('read measured values ...')
# port.write(READ_MEASURED_VALUES)
# data = port.read(50)
# print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
# print()
#
# print('reset device ...')
# port.write(DEVICE_RESET)
# data = port.read(50)
# print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
# print()

if __name__ == '__main__':
    # set up logging, rotating log file, max. file size 100 MBytes
    my_logger = logging.getLogger('MyLogger')
    my_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler = logging.handlers.RotatingFileHandler(cfg['LogFile'],
                                                   maxBytes=104857600,
                                                   backupCount=1)
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)
    # start measurement
    pm_sensor = SensirionSPS30()
    resp = pm_sensor.start_measurement()
    print(resp)
