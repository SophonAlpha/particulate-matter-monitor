import time
import serial
import logging.handlers


def set_up_logging():
    # set up logging, rotating log file, max. file size 100 MBytes
    my_logger = logging.getLogger('MyLogger')
    my_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    handler = logging.handlers.RotatingFileHandler('airmonitor.log',
                                                   maxBytes=104857600,
                                                   backupCount=1)
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)
    return my_logger


class SHDLC:
    def __init__(self):
        self.valid_states = ['00', '01', '02', '03', '04', '28', '43']
        self.last_cmd = None
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
        my_logger.info('sending MOSI frame: {}'.format(mosi_frame))
        mosi_frame = bytes.fromhex(mosi_frame)
        self.port.write(mosi_frame)
        self.last_cmd = cmd

    def get_response(self):
        data = self.port.read(self.buffer_size)
        miso_frame = ['{}'.format(hex(data[pos])) for pos in range(len(data))]
        my_logger.info('received MISO frame: {}'.format(' '.join(miso_frame)))
        valid, err_msg = self.validate_miso_frame(miso_frame)
        if valid:
            # TODO: extract data from MISO frame
            pass
        return data
    
    def validate_miso_frame(self, miso_frame):
        valid = True
        err_msg = None
        miso_frame = byte_unstuffing(miso_frame)
        miso_frame_int = [int(byte, 16) for byte in miso_frame]
        chk = calculate_checksum(miso_frame_int[1:-2])
        if not miso_frame[0] == '7E':  # start
            valid = False
            err_msg = 'MISO frame start byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(0, '7E', miso_frame[0])
            my_logger.error(err_msg)
        elif not miso_frame[1] == '00':  # address
            valid = False
            err_msg = 'MISO frame address byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(1, '00', miso_frame[1])
            my_logger.error(err_msg)
        elif not miso_frame[2] == self.last_cmd:  # command
            valid = False
            err_msg = 'MISO frame command byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(2, self.last_cmd, miso_frame[2])
            my_logger.error(err_msg)
        elif not miso_frame[3] in self.valid_states:  # state
            valid = False
            txt = ', '.join(self.valid_states)
            err_msg = 'MISO frame state byte {} invalid. Expected one of: \'[{}]\'. ' \
                      'Received: \'{}\''.format(3, txt, miso_frame[3])
            my_logger.error(err_msg)
        elif not int(miso_frame[4], 16) == len(miso_frame[5:-2]):  # length
            valid = False
            err_msg = 'MISO frame length byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(4, len(miso_frame[5:-2]),
                                                miso_frame_int[4])
            my_logger.error(err_msg)
        elif not miso_frame_int[-2] == chk:  # checksum
            valid = False
            err_msg = 'MISO frame checksum byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(len(miso_frame) - 2,
                                                format(chk, 'x').upper(),
                                                format(miso_frame_int[-2], 'x').upper())
        elif not miso_frame[-1] == '7E':  # end
            valid = False
            err_msg = 'MISO frame end byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(len(miso_frame) - 1, '7E', miso_frame[-1])
            my_logger.error(err_msg)
        return valid, err_msg


class Commands:
    def __init__(self):
        self.start_measurement = '00'
        self.stop_measurement = '01'
        self.read_measured_values = '03'
        self.read_auto_cleaning_interval = '80'
        self.write_auto_cleaning_interval = '80'
        self.start_fan_cleaning = '56'
        self.device_information = 'D0'
        self.device_reset = 'D3'


class SensirionSPS30:
    def __init__(self):
        self.shdlc = SHDLC()
        self.cmd = Commands()

    def start_measurement(self):
        data = '01 03'  # as per Sensirion SPS30 datasheet
        self.shdlc.send_command(self.cmd.start_measurement, data)
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
    # TODO: simplify the checksum calculation
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
    Do byte-stuffing.

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


def byte_unstuffing(frame):
    """
    Reverse byte-stuffing in received frames.

    The 0x7E character is sent at the beginning and at the end of the frame to
    signalize frame start and stop. If this byte (0x7E) occurs anywhere else in
    the frame, it must be replaced by two other bytes (byte-stuffing).
    This also applies to the characters 0x7D, 0x11 and 0x13.

    :param frame: the frame a list of hex values in string format
    :return: new 'byte stuffed' frame
    """
    unstuffing = {
        ('7D', '5E'): '7E',
        ('7D', '5D'): '7D',
        ('7D', '31'): '11',
        ('7D', '33'): '13',
    }
    ptr = 0
    key_len = len(list(unstuffing.keys())[0])
    while ptr < len(frame):
        seq = tuple(frame[ptr:ptr + key_len])
        if seq in unstuffing.keys():
            frame[ptr:ptr + key_len] = [unstuffing[seq]]
        ptr += 1
    return frame


my_logger = set_up_logging()


if __name__ == '__main__':
    # start measurement
    shdlc = SHDLC()
    resp_frame = ['7E', '00', '80', '01', '00', '7D', '5E', '7E']
    shdlc.last_cmd = '80'
    print(shdlc.validate_miso_frame(resp_frame))
    # pm_sensor = SensirionSPS30()
    # resp = pm_sensor.start_measurement()
    # print(resp)
