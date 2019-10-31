# import serial, time

# Honeywell HPMA115S0-XXX particulate matter sensor
START_PARTICLE_MEASUREMENT = bytes.fromhex('68010196')
READ_PARTICLE_MEASURING_RESULTS = bytes.fromhex('68010493')
STOP_PARTICLE_MEASUREMENT = bytes.fromhex('68010295')
ENABLE_AUTO_SEND = bytes.fromhex('68014057')
STOP_AUTO_SEND = bytes.fromhex('68012077')
RESPONSE_POS_ACK = bytes.fromhex('A5A5')
RESPONSE_NEG_ACK = bytes.fromhex('9696')

# Sensirion SPS30 particulate matter sensor
DEVICE_RESET = bytes.fromhex('7E00D3002C7E')

def build_MOSI_frame(command, data=''):
    start = '7E'
    address = '00'
    length = format(len(command), 'x')
    tx_data = ''.join(data.split())
    check = ~(sum([int(address, 16),
                   int(command, 16),
                   int(length, 16)] +
                  [int(byte, 16) for byte in data.split()]) & 0xFF)
    check = format(check, 'x')
    stop = '7E'
    frame = start + address + command + length + tx_data + check + stop
    return frame

print()

def build_MISO_frame(command):
    pass

class SHDLC:
    def __init__(self):
        pass

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
