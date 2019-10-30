import serial, time

# Honeywell HPMA115S0-XXX particulate matter sensor
START_PARTICLE_MEASUREMENT = bytes.fromhex('68010196')
READ_PARTICLE_MEASURING_RESULTS = bytes.fromhex('68010493')
STOP_PARTICLE_MEASUREMENT = bytes.fromhex('68010295')
ENABLE_AUTO_SEND = bytes.fromhex('68014057')
STOP_AUTO_SEND = bytes.fromhex('68012077')
RESPONSE_POS_ACK = bytes.fromhex('A5A5')
RESPONSE_NEG_ACK = bytes.fromhex('9696')

# Sensirion SPS30 particulate matter sensor
START_MEASUREMENT = bytes.fromhex('7E0000020103F97E')
READ_MEASURED_VALUES = bytes.fromhex('7E000300FC7E')
DEVICE_RESET = bytes.fromhex('7E00D3002C7E')

port = serial.Serial('/dev/serial0',
                     baudrate=115200,
                     parity=serial.PARITY_NONE,
                     stopbits=serial.STOPBITS_ONE,
                     bytesize=serial.EIGHTBITS,
                     timeout=1.5)

if port.isOpen():
    print('closing port ...')
    port.close()
print('open serial port ...')
port.open()
time.sleep(1)
print()

print('start particle measurement ...')
port.write(START_MEASUREMENT)
data = port.read(16)
print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
print()

print('read measured values ...')
port.write(READ_MEASURED_VALUES)
data = port.read(50)
print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
print()

print('reset device ...')
port.write(DEVICE_RESET)
data = port.read(50)
print(' '.join(['{}'.format(hex(data[pos])) for pos in range(len(data))]))
print()

port.close()
