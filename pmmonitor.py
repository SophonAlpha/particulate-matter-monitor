import serial, time


class SensirionSPS30:
    def __init__(self):
        pass

    def start_measurement(self):
        START_MEASUREMENT = bytes.fromhex('7E 00 00 02 01 03 F9 7E')

    def stop_measurement(self):
        STOP_MEASUREMENT = bytes.fromhex('7E 00 01 00 FE 7E')

    def read_measurement_values(self):
        READ_MEASURED_VALUES = bytes.fromhex('7E 00 03 00 FC 7E')

    def read_auto_cleaning_interval(self):
        READ_AUTO_CLEANING_INTERVAL = bytes.fromhex('7E 00 80 01 00 7D 5E 7E')

    def write_auto_cleaning_interval(self):
        WRITE_AUTO_CLEANING_INTERVAL = bytes.fromhex(' ')

    def start_fan_cleaning(self):
        START_FAN_CLEANING = bytes.fromhex('7E 00 56 00 A9 7E')

    def get_device_information(self):
        PRODUCT_NAME = bytes.fromhex('7E 00 D0 01 01 2D 7E')
        ARTICLE_CODE = bytes.fromhex('7E 00 D0 01 02 2C 7E')
        SERIAL_NUMBER = bytes.fromhex('7E 00 D0 01 03 2B 7E')

    def device_reset(self):
        DEVICE_RESET = bytes.fromhex('7E 00 D3 00 2C 7E')


def build_MOSI_frame(command, data=''):
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
    frame = byte_stuffing(frame[1:-1])  # bytes stuffing where needed
    frame = ''.join(frame)
    return frame


def calculate_checksum(data):
    # Sum all bytes between start and stop (without start and stop bytes).
    checksum = sum(data)
    # Take the LSB of the result ...
    checksum = checksum & 0xFF
    # ... and invert it. This will be the checksum.
    checksum = ~checksum & 0xFF
    return checksum


def byte_stuffing(frame):
    replace = {
        '7E': '7D 5E',
        '7D': '7D 5D',
        '11': '7D 31',
        '13': '7D 33',
    }
    frame = [replace[byte] if byte in replace.keys() else byte for byte in frame]
    return frame


# port = serial.Serial('/dev/serial0',
#                      baudrate=115200,
#                      parity=serial.PARITY_NONE,
#                      stopbits=serial.STOPBITS_ONE,
#                      bytesize=serial.EIGHTBITS,
#                      timeout=1.5)
#
# if port.isOpen():
#     print('closing port ...')
#     port.close()
# print('open serial port ...')
# port.open()
# time.sleep(1)
# print()
#
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
#
# port.close()

if __name__ == '__main__':
    MOSI_frame = build_MOSI_frame('80', data='00')
    print(MOSI_frame)