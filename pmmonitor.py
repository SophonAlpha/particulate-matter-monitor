#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import yaml
import platform
import time
import serial
import logging.handlers
import struct
import requests
from influxdb import InfluxDBClient
import datetime
import Adafruit_DHT


# noinspection SpellCheckingInspection
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


class MISOFrameError(Exception):
    pass


class StateValidationError(Exception):
    pass


class SHDLC:
    def __init__(self):
        self.valid_states = ['0x0', '0x1', '0x2', '0x3', '0x4', '0x28', '0x43']
        self.last_cmd = None
        self.buffer_size = 64
        self.port = None
        if platform.system() == 'Linux':
            self.open_serial_port()

    def open_serial_port(self):
        self.port = serial.Serial('/dev/serial0',
                                  baudrate=115200,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  bytesize=serial.EIGHTBITS,
                                  timeout=1.5)
        if self.port.isOpen():
            self.port.close()
        self.port.open()

    def close_serial_port(self):
        self.port.close()

    def send_command(self, cmd, data):
        mosi_frame = build_mosi_frame(cmd, data)
        my_logger.info('sending MOSI frame: {}'.format(mosi_frame))
        mosi_frame = ''.join(['{:02x}'.format(int(byte, 0))
                              for byte in mosi_frame])
        mosi_frame = bytes.fromhex(mosi_frame)
        self.port.write(mosi_frame)
        self.last_cmd = cmd

    def get_response(self):
        data = self.port.read(self.buffer_size)
        miso_frame = [hex(data[pos]) for pos in range(len(data))]
        my_logger.info('received MISO frame: {}'.format(miso_frame))
        self.validate_miso_frame(miso_frame)
        check_state(miso_frame)
        payload = miso_frame[5:-2]
        return payload

    def validate_miso_frame(self, miso_frame):
        miso_frame = byte_unstuffing(miso_frame)
        miso_frame_int = [int(byte, 16) for byte in miso_frame]
        chk = calculate_checksum(miso_frame_int[1:-2])
        if not miso_frame[0] == '0x7e':  # start
            err_msg = 'MISO frame start byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(0, '0x7e', miso_frame[0])
            raise MISOFrameError(err_msg)
        elif not miso_frame[1] == '0x0':  # address
            err_msg = 'MISO frame address byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(1, '0x0', miso_frame[1])
            raise MISOFrameError(err_msg)
        elif not miso_frame[2] == self.last_cmd:  # command
            err_msg = 'MISO frame command byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(2, self.last_cmd, miso_frame[2])
            raise MISOFrameError(err_msg)
        elif not miso_frame[3] in self.valid_states:  # state
            txt = ', '.join(self.valid_states)
            err_msg = 'MISO frame state byte {} invalid. Expected one of: \'[{}]\'. ' \
                      'Received: \'{}\''.format(3, txt, miso_frame[3])
            raise MISOFrameError(err_msg)
        elif not int(miso_frame[4], 16) == len(miso_frame[5:-2]):  # length
            err_msg = 'MISO frame length byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(4, len(miso_frame[5:-2]),
                                                miso_frame_int[4])
            raise MISOFrameError(err_msg)
        elif not miso_frame_int[-2] == chk:  # checksum
            err_msg = 'MISO frame checksum byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(len(miso_frame) - 2,
                                                hex(chk),
                                                hex(miso_frame_int[-2]))
            raise MISOFrameError(err_msg)
        elif not miso_frame[-1] == '0x7e':  # end
            err_msg = 'MISO frame stop byte {} invalid. Expected: \'{}\'. ' \
                      'Received: \'{}\''.format(len(miso_frame) - 1, '0x7e',
                                                miso_frame[-1])
            raise MISOFrameError(err_msg)
        return


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
    frame = ['0x7e', '0x0', command, '0x{:x}'.format(len(data))]
    frame.extend(data)  # TX data
    check = calculate_checksum([int(frame[1], 16), int(frame[2], 16),
                                int(frame[3], 16)] + [int(byte, 16)
                                                      for byte in data])
    check = '0x{:x}'.format(check)
    frame.append(check)  # check
    frame.append('0x7e')  # stop
    frame = [byte for byte in frame]
    frame = byte_stuffing(frame)
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

    The 0x7e character is sent at the beginning and at the end of the frame to
    signalize frame start and stop. If this byte (0x7E) occurs anywhere else in
    the frame, it must be replaced by two other bytes (byte-stuffing).
    This also applies to the characters 0x7D, 0x11 and 0x13.

    :param frame: the frame a list of hex values in string format
    :return: new 'byte stuffed' frame
    """
    stuffing = {
        '0x7e': ['0x7d', '0x5e'],
        '0x7d': ['0x7d', '0x5d'],
        '0x11': ['0x7d', '0x31'],
        '0x13': ['0x7d', '0x33'],
    }
    new_frame = [frame[0]]
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
        ('0x7d', '0x5e'): '0x7e',
        ('0x7d', '0x5d'): '0x7d',
        ('0x7d', '0x31'): '0x11',
        ('0x7d', '0x33'): '0x13',
    }
    ptr = 0
    key_len = len(list(unstuffing.keys())[0])
    while ptr < len(frame):
        seq = tuple(frame[ptr:ptr + key_len])
        if seq in unstuffing.keys():
            frame[ptr:ptr + key_len] = [unstuffing[seq]]
        ptr += 1
    return frame


def check_state(miso_frame):
    state_errors = {
        '0x1': 'Wrong data length for this command(too much or little data)',
        '0x2': 'Unknown command',
        '0x3': 'No access right for command',
        '0x4': 'Illegal command parameter or parameter out of allowed range',
        '0x28': 'Internal function argument out of range',
        '0x43': 'Command not allowed in current state',
    }
    if miso_frame[3] in state_errors.keys():
        raise StateValidationError(state_errors[miso_frame[3]], int(miso_frame[3], 0))
    pass


class Commands:
    def __init__(self):
        self.start_measurement = '0x0'
        self.stop_measurement = '0x1'
        self.read_measured_values = '0x3'
        self.read_auto_cleaning_interval = '0x80'
        self.write_auto_cleaning_interval = '0x80'
        self.start_fan_cleaning = '0x56'
        self.device_information = '0xd0'
        self.device_reset = '0xd3'


class SensirionSPS30:
    def __init__(self):
        self.shdlc = SHDLC()
        self.cmd = Commands()

    def start_measurement(self):
        data = ['0x1', '0x3']  # as per Sensirion SPS30 datasheet
        my_logger.info('start measurement ...')
        rsp = self.send_receive(self.cmd.start_measurement, data)
        return rsp

    def stop_measurement(self):
        data = []
        my_logger.info('stop measurement ...')
        rsp = self.send_receive(self.cmd.stop_measurement, data)
        return rsp

    def read_measured_values(self):
        data = []
        my_logger.info('read measured values ...')
        rsp = self.send_receive(self.cmd.read_measured_values, data)
        if rsp is not False and rsp != []:
            hexstr = ['{:02x}'.format(int(byte[2:], 16)) for byte in rsp]
            mvals = {
                'mass_concentration_PM1_0': bytes_to_float(hexstr[0:4]),
                'mass_concentration_PM2_5': bytes_to_float(hexstr[4:8]),
                'mass_concentration_PM4_0': bytes_to_float(hexstr[8:12]),
                'mass_concentration_PM10': bytes_to_float(hexstr[12:16]),
                'number_concentration_PM0_5': bytes_to_float(hexstr[16:20]),
                'number_concentration_PM1_0': bytes_to_float(hexstr[20:24]),
                'number_concentration_PM2_5': bytes_to_float(hexstr[24:28]),
                'number_concentration_PM4_0': bytes_to_float(hexstr[28:32]),
                'number_concentration_PM10': bytes_to_float(hexstr[32:36]),
                'typical_particle_size': bytes_to_float(hexstr[36:40]),
                }
        else:
            mvals = {}
        return mvals

    def read_auto_cleaning_interval(self):
        data = ['0x0']  # subcommand, must be '0x0'
        my_logger.info('read auto cleaning interval ...')
        rsp = self.send_receive(self.cmd.read_auto_cleaning_interval, data)
        interval = int(''.join([byte[2:] for byte in rsp]), 16)
        return interval

    def write_auto_cleaning_interval(self, interval):
        data_hex = '{:08x}'.format(interval)
        data = ['0x0']  # subcommand, must be '0x0'
        data.extend(['0x' + data_hex[pos:pos + 2] for pos in range(0, len(data_hex), 2)])
        my_logger.info('write auto cleaning interval ...')
        rsp = self.send_receive(self.cmd.write_auto_cleaning_interval, data)
        return rsp

    def start_fan_cleaning(self):
        data = []
        my_logger.info('start fan cleaning ...')
        rsp = self.send_receive(self.cmd.start_fan_cleaning, data)
        return rsp

    def get_device_information(self):
        dev_info = {
            'product_name': ['0x1'],
            'article_code': ['0x2'],
            'serial_number': ['0x3'],
            }
        dev_info_txt = {}
        for info in dev_info:
            my_logger.info('get device information for {} ...'.format(info))
            rsp = self.send_receive(self.cmd.device_information, dev_info[info])
            dev_info_txt[info] = ''.join([chr(int(char, 0)) for char in rsp[:-1]])               
        return dev_info_txt

    def device_reset(self):
        data = []
        my_logger.info('do device reset ...')
        rsp = self.send_receive(self.cmd.device_reset, data)
        return rsp
    
    def send_receive(self, cmd, data):
        my_logger.info('sending command {} ...'.format(cmd))
        self.shdlc.send_command(cmd, data)
        try:
            rsp = self.shdlc.get_response()
        except StateValidationError as excinfo:
            err_msg, err_code = excinfo.args
            my_logger.error('command failed with error: {}'.format(err_msg))
            rsp = False
        else:
            my_logger.info('command completed successful')
        return rsp


def bytes_to_float(hex_bytes):
    hexstr = ''.join(hex_bytes)
    return struct.unpack('>f', bytes.fromhex(hexstr))[0]


class Database:

    def __init__(self, host, port, dbuser, dbuser_password, dbname):
        self.client = InfluxDBClient(host, port,
                                     dbuser, dbuser_password,
                                     dbname)
        my_logger.info('database configuration: host: {}:{}, '
                       'user: {}, database: {}'.format(host, port,
                                                       dbuser, dbname))

    def write(self, data):
        my_logger.info('writing {} attributes for measurement \'{}\' to '
                       'database'.format(len(data[0]['fields'].keys()), data[0]['measurement']))
        try:
            self.client.write_points(data)
        except requests.exceptions.ConnectionError as err:
            my_logger.error('writing to database failed with '
                            'error: \'{}\'.'.format(err))
        else:
            my_logger.info('data written to database')


def parse_args():
    """ parse the args from the command line call """
    parser = argparse.ArgumentParser(description='Read sensor data.')
    parser.add_argument('-c', '--config', type=str,
                        default='airmonitor_config.yml',
                        help='configuration file')
    return parser.parse_args()


my_logger = set_up_logging()


if __name__ == '__main__':
    my_logger.info('---------- script started ----------')
    my_logger.info('reading configuration file')
    args = parse_args()
    with open(args.config, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    database = Database(host=cfg['database']['host'],
                        port=cfg['database']['port'],
                        dbuser=cfg['database']['user'],
                        dbuser_password=cfg['database']['password'],
                        dbname=cfg['database']['name'])

    #  Sensirion SPS30 particulate matter sensor

    shdlc = SHDLC()
    pm_sensor = SensirionSPS30()
    my_logger.info('start Sensirion SPS30 particulate matter sensor')
    pm_sensor.start_measurement()
    my_logger.info('wait 10 seconds for sensor fan to spin up')
    time.sleep(10)  # let the sensor fan run for a few seconds before measurements
    measurements = []
    values = None
    for idx in range(3):
        my_logger.info('take measurement {}'.format(idx + 1))
        values = pm_sensor.read_measured_values()
        measurements.append(values)
        time.sleep(1)
    measurement_avgs = {}
    my_logger.info('calculate averages for measurement values')
    for key in values:
        measurement_avgs[key] = sum([measurement[key] for measurement in measurements]) / len(measurements)
    data_json = [{
        'measurement': cfg['SensirionSPS30']['measurement'],
        'time': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
        'fields': measurement_avgs
        }]
    my_logger.info('write {} measurement values to database'.format(len(measurement_avgs)))
    database.write(data_json)
    my_logger.info('stop Sesirion SPS30 particulate matter sensor')
    pm_sensor.stop_measurement()

    #  DHT22 humidity and temperature sensor

    my_logger.info('take humidity and temperature measurement from DHT22 sensor')
    sensor = Adafruit_DHT.DHT22
    pin = 4
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
    measurement = {
        'humidity': humidity,
        'temperature': temperature,
        }
    data_json = [{
        'measurement': cfg['DHT22']['measurement'],
        'time': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
        'fields': measurement
        }]
    my_logger.info('write {} measurement values to database'.format(len(measurement)))
    database.write(data_json)

    my_logger.info('---------- script stopped ----------')
