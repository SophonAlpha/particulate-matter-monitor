"""
Test suite for particulate matter sensor Sensirion SPS30:
https://www.sensirion.com/en/environmental-sensors/particulate-matter-sensors-pm25/
"""

import pytest

import pmmonitor

TESTS_BUILD_MOSI_FRAME = [
    ('00', '01 03', '7E0000020103F97E'),  # Start Measurement (CMD: 0x00)
    ('01', '', '7E000100FE7E'),  # Stop Measurement (CMD: 0x01)
    ('03', '', '7E000300FC7E'),  # Read Measured Values (CMD: 0x03)
    ('80', '00', '7E008001007D5E7E'),  # Read Auto Cleaning Interval (CMD: 0x80)
    ('80', '00 00 00 00 00', '7E00800500000000007A7E'),  # Write Auto Cleaning Interval (CMD: 0x80)
    ('56', '', '7E005600A97E'),  # Start Fan Cleaning (CMD: 0x56)
    ('D0', '01', '7E00D001012D7E'),  # Device Information - Product Name (CMD 0xD0)
    ('D0', '02', '7E00D001022C7E'),  # Device Information - Article Code (CMD 0xD0)
    ('D0', '03', '7E00D001032B7E'),  # Device Information - Serial Number (CMD 0xD0)
    ('D3', '', '7E00D3002C7E'),  # Device Reset (CMD: 0xD3)
]

TESTS_UNSTUFFING = [
    (['7E', '00', '80', '01', '00', '7D', '5E', '7E'],
     ['7E', '00', '80', '01', '00', '7E', '7E']),
    (['7E', '7D', '5D', '80', '01', '00', '7E', '7E'],
     ['7E', '7D', '80', '01', '00', '7E', '7E']),
    (['7D', '31', '00', '80', '01', '00', '7E', '7E'],
     ['11', '00', '80', '01', '00', '7E', '7E']),
    (['7E', '00', '80', '01', '00', '7E', '7D', '33'],
     ['7E', '00', '80', '01', '00', '7E', '13']),
    (['7D', '5E', '7D', '5D', '7D', '31', '7D', '33', '00', '7E', '7E'],
     ['7E', '7D', '11', '13', '00', '7E', '7E']),
]

TESTS_VALIDATE_MISO_FRAME = [
    (['7E', '00', '80', '01', '00', '7D', '5E', '7E'], '80',
     True, None),  # correct frame
    (['7F', '00', '80', '01', '00', '7D', '5E', '7E'], '80', False,
     'MISO frame start byte 0 invalid. Expected: \'7E\'. Received: \'7F\''),  # wrong start byte
    (['7E', '01', '80', '01', '00', '7D', '5E', '7E'], '80', False,
     'MISO frame address byte 1 invalid. Expected: \'00\'. Received: \'01\''),  # wrong address byte
    (['7E', '00', '66', '01', '00', '7D', '5E', '7E'], '80', False,
     'MISO frame command byte 2 invalid. Expected: \'80\'. Received: \'66\''),  # wrong command byte
    (['7E', '00', '80', '44', '00', '7D', '5E', '7E'], '80', False,
     'MISO frame state byte 3 invalid. Expected one of: \'[00, 01, 02, 03, 04, 28, 43]\'. Received: \'44\''),  # wrong state byte
    (['7E', '00', '80', '01', '01', '7D', '5E', '7E'], '80', False,
     'MISO frame length byte 4 invalid. Expected: \'0\'. Received: \'1\''),  # wrong state length
    (['7E', '00', '80', '01', '00', '7D', '5D', '7E'], '80', False,
     'MISO frame checksum byte 5 invalid. Expected: \'7E\'. Received: \'7D\''),  # wrong checksum
    (['7E', '00', '80', '01', '00', '7D', '5E', '7F'], '80', False,
     'MISO frame end byte 6 invalid. Expected: \'7E\'. Received: \'7F\''),  # wrong end byte
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


@pytest.mark.parametrize('resp_frame, last_cmd, valid, err_msg',
                         TESTS_VALIDATE_MISO_FRAME)
def test_frame_unstuffing(resp_frame, last_cmd, valid, err_msg):
    """ tests """
    shdlc = pmmonitor.SHDLC()
    shdlc.last_cmd = last_cmd
    resp_valid, resp_err_msg = shdlc.validate_miso_frame(resp_frame)
    assert resp_valid == valid
    assert resp_err_msg == err_msg
