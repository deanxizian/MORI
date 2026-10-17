"""S288 bench feedback protocol; only mode=0 commands are exposed.

Reference: Unitree digital_servo v1.0.1, commit 75c1ed63579dc7bb759e2990bd4b804c11b57daf.
Use the C protocol.h layout: sensor/voltage are uint8, position is int32.
The vendor Markdown table and Python demo have conflicting signedness/offsets.
No motor motion, ID configuration, firmware update, or timeout-clear API here.
"""
import math
import struct

RATIO = 70070.0 / 243.0
BAUD = 6_000_000


def valid_id(value):
    if type(value) is not int or not 0 <= value <= 14:
        raise ValueError('Use a unicast servo ID from 0 to 14; broadcast is disabled')
    return value


def crc32_words(data):
    """STM32-style CRC: LE 32-bit words, MSB first, no reflection/final XOR."""
    if len(data) % 4:
        raise ValueError('CRC input must contain whole 32-bit words')
    crc = 0xFFFFFFFF
    for (word,) in struct.iter_unpack('<I', data):
        crc ^= word
        for _ in range(32):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    return crc


def locked_query(motor_id):
    # Mode 0 is the documented lock/stop command, NOT electrical isolation.
    # Timeout protection stays enabled. All five control targets/gains are zero.
    body = bytes([0xFE, 0xEE, valid_id(motor_id) | 0x80, 0]) + bytes(12)
    return body + struct.pack('<I', crc32_words(body))


def decode_feedback(packet, expected_id):
    valid_id(expected_id)
    if len(packet) != 26 or packet[:2] != b'\xfc\xee':
        raise ValueError('Invalid feedback framing')
    if crc32_words(packet[2:22]) != struct.unpack_from('<I', packet, 22)[0]:
        raise ValueError('Feedback CRC mismatch')
    mode_byte = packet[2]
    if mode_byte & 15 != expected_id:
        raise ValueError('Feedback ID mismatch')
    mode = (mode_byte >> 4) & 7
    if mode not in (0, 1):
        raise ValueError('Unsupported feedback mode')
    temp, sensor, voltage, torque, speed, position, errors, angle_flags, extra, excom = \
        struct.unpack_from('<bBBhhiIHBB', packet, 3)
    angle = angle_flags & 8191
    return {
        'id': expected_id, 'mode': mode, 'timeout_active': bool(mode_byte & 128),
        'temperature_c': temp, 'sensor_raw': sensor, 'voltage_raw': voltage,
        'voltage_v': voltage / 2,
        'torque_raw': torque, 'speed_raw': speed, 'rotor_position_raw': position,
        'torque_estimate_nm': torque / 256000 * RATIO,
        'speed_rad_s': speed / 2.56 * math.tau / RATIO,
        'position_rad': position / 32768 * math.tau / RATIO,
        'output_position_raw': angle, 'absolute_output_rad': angle / 8192 * math.tau,
        'errors_raw': errors, 'warning_raw': angle_flags >> 13,
        'extra_sensor_raw': extra, 'extended_com_raw': excom,
        'raw_hex': packet.hex(),
    }


class FeedbackStream:
    """Bounded resynchronization for fragmented packets, noise and bad CRCs."""
    def __init__(self, motor_id):
        self.motor_id = valid_id(motor_id)
        self.buffer = bytearray()
        self.bad_frames = 0
        self.discarded_bytes = 0

    def feed(self, chunk):
        output = []
        for byte in chunk:
            self.buffer.append(byte)
            while self.buffer and (self.buffer[0] != 0xFC or
                    (len(self.buffer) > 1 and self.buffer[1] != 0xEE)):
                del self.buffer[0]
                self.discarded_bytes += 1
            if len(self.buffer) == 26:
                try:
                    output.append(decode_feedback(bytes(self.buffer), self.motor_id))
                    self.buffer.clear()
                except ValueError:
                    self.bad_frames += 1
                    del self.buffer[0]
        return output


def feedback_findings(row):
    findings = []
    if row['mode'] != 0:
        findings.append('servo_not_in_requested_mode_0')
    if row['errors_raw']:
        findings.append('servo_error')
    if row['warning_raw']:
        findings.append('servo_warning')
    if row['timeout_active']:
        findings.append('timeout_latched_not_cleared')
    if not 6.4 <= row['voltage_v'] <= 12.6:
        findings.append('voltage_outside_s288_vendor_range')
    return findings
