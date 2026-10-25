"""Versioned software target; never an alternative mechanical/electrical authority."""
import json
from pathlib import Path
PROFILE = json.loads(Path(__file__).with_name('software_profile.json').read_text())

def unavailable_sensors():
    return {
        'body_imu': {'valid': False, 'pitch_rad': None, 'pitch_rate_rad_s': None, 'sampled_us': None, 'age_us': None},
        'wheels': [{'valid': False, 'position_rad': None, 'speed_rad_s': None, 'torque_estimate_nm': None, 'sampled_us': None, 'age_us': None} for _ in range(2)],
        'head': {'valid': False, 'yaw_rad': None, 'pitch_rad': None, 'sampled_us': None, 'age_us': None},
        'power': {'valid': False, 'battery_v': None, 'current_a': None, 'temperature_c': None, 'sampled_us': None, 'age_us': None},
    }
