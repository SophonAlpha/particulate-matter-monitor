"""
Test suite for particulate matter sensor Sensirion SPS30:
https://www.sensirion.com/en/environmental-sensors/particulate-matter-sensors-pm25/
"""

import pytest
import time

import pmmonitor

TESTS_BUILD_MOSI_FRAME = [
    ('0x0', ['0x1', '0x3'],
     ['0x7e', '0x0', '0x0', '0x2', '0x1', '0x3', '0xf9', '0x7e']),  # Start Measurement (CMD: 0x00)
    ('0x1', [],
     ['0x7e', '0x0', '0x1', '0x0', '0xfe', '0x7e']),  # Stop Measurement (CMD: 0x01)
    ('0x3', [],
     ['0x7e', '0x0', '0x3', '0x0', '0xfc', '0x7e']),  # Read Measured Values (CMD: 0x03)
    ('0x80', ['0x0'],
     ['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7e']),  # Read Auto Cleaning Interval (CMD: 0x80)
    ('0x80', ['0x0', '0x0', '0x0', '0x0', '0x0'],
     ['0x7e', '0x0', '0x80', '0x5', '0x0', '0x0', '0x0', '0x0', '0x0', '0x7a', '0x7e']),  # Write Auto Cleaning Interval (CMD: 0x80)
    ('0x56', [],
     ['0x7e', '0x0', '0x56', '0x0', '0xa9', '0x7e']),  # Start Fan Cleaning (CMD: 0x56)
    ('0xd0', ['0x1'],
     ['0x7e', '0x0', '0xd0', '0x1', '0x1', '0x2d', '0x7e']),  # Device Information - Product Name (CMD 0xD0)
    ('0xd0', ['0x2'],
     ['0x7e', '0x0', '0xd0', '0x1', '0x2', '0x2c', '0x7e']),  # Device Information - Article Code (CMD 0xD0)
    ('0xd0', ['0x3'],
     ['0x7e', '0x0', '0xd0', '0x1', '0x3', '0x2b', '0x7e']),  # Device Information - Serial Number (CMD 0xD0)
    ('0xd3', [],
     ['0x7e', '0x0', '0xd3', '0x0', '0x2c', '0x7e']),  # Device Reset (CMD: 0xD3)
]

TESTS_UNSTUFFING = [
    (['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7e'],
     ['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7e', '0x7e']),
    (['0x7e', '0x7d', '0x5d', '0x80', '0x1', '0x0', '0x7e', '0x7e'],
     ['0x7e', '0x7d', '0x80', '0x1', '0x0', '0x7e', '0x7e']),
    (['0x7d', '0x31', '0x0', '0x80', '0x1', '0x0', '0x7e', '0x7e'],
     ['0x11', '0x0', '0x80', '0x1', '0x0', '0x7e', '0x7e']),
    (['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7e', '0x7d', '0x33'],
     ['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7e', '0x13']),
    (['0x7d', '0x5e', '0x7d', '0x5d', '0x7d', '0x31', '0x7d', '0x33', '0x0', '0x7e', '0x7e'],
     ['0x7e', '0x7d', '0x11', '0x13', '0x0', '0x7e', '0x7e']),
]

TESTS_VALIDATE_MISO_FRAME = [
    (['0x7f', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7e'], '0x80',
     'MISO frame start byte 0 invalid. Expected: \'0x7e\'. Received: \'0x7f\''),  # wrong start byte
    (['0x7e', '0x1', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7e'], '0x80',
     'MISO frame address byte 1 invalid. Expected: \'0x0\'. Received: \'0x1\''),  # wrong address byte
    (['0x7e', '0x0', '0x66', '0x1', '0x0', '0x7d', '0x5e', '0x7e'], '0x80',
     'MISO frame command byte 2 invalid. Expected: \'0x80\'. Received: \'0x66\''),  # wrong command byte
    (['0x7e', '0x0', '0x80', '0x44', '0x0', '0x7d', '0x5e', '0x7e'], '0x80',
     'MISO frame state byte 3 invalid. Expected one of: \'[0x0, 0x1, 0x2, 0x3, 0x4, 0x28, 0x43]\'. Received: \'0x44\''),  # wrong state byte
    (['0x7e', '0x0', '0x80', '0x1', '0x1', '0x7d', '0x5e', '0x7e'], '0x80',
     'MISO frame length byte 4 invalid. Expected: \'0\'. Received: \'1\''),  # wrong state length
    (['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5d', '0x7e'], '0x80',
     'MISO frame checksum byte 5 invalid. Expected: \'0x7e\'. Received: \'0x7d\''),  # wrong checksum
    (['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7f'], '0x80',
     'MISO frame stop byte 6 invalid. Expected: \'0x7e\'. Received: \'0x7f\''),  # wrong end byte
]

TESTS_VALIDATE_MISO_STATE = [
    (['0x7e', '0x0', '0x80', '0x1', '0x0', '0x7d', '0x5e', '0x7e'],
     'Wrong data length for this command(too much or little data)', 1),
    (['0x7e', '0x0', '0x80', '0x2', '0x0', '0x7d', '0x5e', '0x7e'],
     'Unknown command', 2),
    (['0x7e', '0x0', '0x80', '0x3', '0x0', '0x7d', '0x5e', '0x7e'],
     'No access right for command', 3),
    (['0x7e', '0x0', '0x80', '0x4', '0x0', '0x7d', '0x5e', '0x7e'],
     'Illegal command parameter or parameter out of allowed range', 4),
    (['0x7e', '0x0', '0x80', '0x28', '0x0', '0x7d', '0x5e', '0x7e'],
     'Internal function argument out of range', 40),
    (['0x7e', '0x0', '0x80', '0x43', '0x0', '0x7d', '0x5e', '0x7e'],
     'Command not allowed in current state', 67),
]


@pytest.mark.parametrize('command, data, solution', TESTS_BUILD_MOSI_FRAME)
def test_build_mosi_frame(command, data, solution):
    """ tests """
    frame = pmmonitor.build_mosi_frame(command, data)
    assert frame == solution


@pytest.mark.parametrize('frame, unstuffed_frame', TESTS_UNSTUFFING)
def test_frame_unstuffing(frame, unstuffed_frame):
    """ tests """
    frame = pmmonitor.byte_unstuffing(frame)
    assert frame == unstuffed_frame


@pytest.mark.parametrize('resp_frame, last_cmd, err_msg',
                         TESTS_VALIDATE_MISO_FRAME)
def test_validate_miso_frame(resp_frame, last_cmd, err_msg):
    """ tests """
    shdlc = pmmonitor.SHDLC()
    shdlc.last_cmd = last_cmd
    with pytest.raises(pmmonitor.MISOFrameError) as excinfo:
        shdlc.validate_miso_frame(resp_frame)
    assert excinfo.value.args[0] == err_msg


@pytest.mark.parametrize('resp_frame, err_msg, err_code',
                         TESTS_VALIDATE_MISO_STATE)
def test_validate_miso_state(resp_frame, err_msg, err_code):
    """ tests """
    with pytest.raises(pmmonitor.StateValidationError) as excinfo:
        pmmonitor.check_state(resp_frame)
    assert excinfo.value.args[0] == err_msg
    assert excinfo.value.args[1] == err_code


def test_start_stop_measurement():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    ret_start = pm_sensor.start_measurement()
    ret_stop = pm_sensor.stop_measurement()
    assert ret_start == []
    assert ret_stop == []


def test_read_measured_values():
    pm_sensor = pmmonitor.SensirionSPS30()
    ret_start = pm_sensor.start_measurement()
    values = pm_sensor.read_measured_values()
    ret_stop = pm_sensor.stop_measurement()
    assert ret_start == []
    assert set(values.keys()) == set(['mass_concentration_PM1_0', 'mass_concentration_PM2_5',
                                      'mass_concentration_PM4_0', 'mass_concentration_PM10',
                                      'number_concentration_PM0_5', 'number_concentration_PM1_0',
                                      'number_concentration_PM2_5', 'number_concentration_PM4_0',
                                      'number_concentration_PM10','typical_particle_size'])
    assert all([isinstance(val, float) for val in values.values()])
    assert ret_stop == []


def test_read_auto_cleaning_interval():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    resp = pm_sensor.read_auto_cleaning_interval()
    assert resp == 604800


def test_write_auto_cleaning_interval():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    ret_read1 = pm_sensor.read_auto_cleaning_interval()
    pm_sensor.write_auto_cleaning_interval(65535)
    ret_read2 = pm_sensor.read_auto_cleaning_interval()
    pm_sensor.write_auto_cleaning_interval(604800)
    ret_read3 = pm_sensor.read_auto_cleaning_interval()
    assert ret_read1 == 604800
    assert ret_read2 == 65535
    assert ret_read3 == 604800


def test_start_fan_cleaning():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    ret_start = pm_sensor.start_measurement()
    ret_clean = pm_sensor.start_fan_cleaning()
    time.sleep(10)
    ret_stop = pm_sensor.stop_measurement()
    assert ret_start == []
    assert ret_clean == []
    assert ret_stop == []


def test_get_device_information():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    resp = pm_sensor.get_device_information()
    assert set(resp.keys()) == set(['article_code',
                                    'product_name',
                                    'serial_number'])
    assert 0 < len(resp['serial_number']) < 33
    assert isinstance(resp['serial_number'], str)


def test_device_reset():
    """ test """
    pm_sensor = pmmonitor.SensirionSPS30()
    resp = pm_sensor.device_reset()
    assert resp == []

