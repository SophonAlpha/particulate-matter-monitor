"""
Test suite for particulate matter sensor Sensirion SPS30:
https://www.sensirion.com/en/environmental-sensors/particulate-matter-sensors-pm25/
"""

import pytest

import pmmonitor

TESTS = [
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

@pytest.mark.parametrize('command, data, solution', TESTS)
def test_build_MOSI_frame(command, data, solution):
    """ tests """
    frame = pmmonitor.build_mosi_frame(command, data)
    assert frame == solution
