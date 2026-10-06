#!/usr/bin/env python3
"""Reproducible documentary arithmetic, NOT a motor/robot performance test."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'hardware/v1_2'


def hal_over16(pclk, baud):
    # STM32 HAL macros in the pinned Unitree v1.0.1 archive.
    scaled = (pclk * 25) // (4 * baud)
    mantissa = scaled // 100
    fraction = ((scaled - mantissa * 100) * 16 + 50) // 100
    brr = (mantissa << 4) + (fraction & 0xF0) + (fraction & 0x0F)
    actual = pclk / brr
    return {'pclk_hz': pclk, 'oversampling': 16, 'requested_baud': baud,
            'brr_decimal': brr, 'actual_baud': actual,
            'nominal_error_percent': (actual / baud - 1) * 100,
            'oscillator_tolerance_included': False}


def main():
    g = json.loads((ROOT / 'config/geometry.json').read_text())
    d_m = g['wheel_diameter_mm'] / 1000
    sample = HERE / 'sources/unitree_v1.0.1_excerpt/stm32/firmware'
    main_c = (sample / 'Core/Src/main.c').read_text(errors='replace')
    uart_c = (sample / 'Core/Src/usart.c').read_text(errors='replace')
    required = ['RCC_PLLSOURCE_HSI', 'PLLM = 8', 'PLLN = 100', 'RCC_PLLP_DIV2', 'APB2CLKDivider = RCC_HCLK_DIV1']
    assert all(token in main_c for token in required), 'Source changed: re-review clock tree'
    assert 'UART_OVERSAMPLING_16' in uart_c and 'BaudRate = 6000000' in uart_c
    official = hal_over16(100_000_000, 6_000_000)
    candidate = hal_over16(96_000_000, 6_000_000)
    assert official['brr_decimal'] == 17 and candidate['brr_decimal'] == 16
    assert candidate['nominal_error_percent'] == 0
    report = {
        'revision': 'V1.2-H0.2-P1', 'evidence_layer': 'HOST_TEST',
        'calculation_execution': 'PASS', 'hardware_qualification': 'NOT_TESTED',
        'source': 'HW12-U3 pinned v1.0.1 source and included STM32 HAL macros',
        'official_reference': official, 'candidate_not_implemented': candidate,
        'clock_note': 'HSI tolerance, actual crystal/PLL setup and physical UART eye/turnaround not qualified. 96MHz is a nominal candidate, not a flash image.',
        'two_motor_roundtrip': {
            'assumed_request_bytes': 20, 'assumed_reply_bytes': 26,
            'frame_format': '8N1 = 10 bits/byte',
            'ideal_wire_only_us': 2 * (20 + 26) * 10 / 6_000_000 * 1e6,
            'status': 'ASSUMED_PACKET_LAYOUT_PENDING_PROTOCOL_RESOLUTION',
            'excluded': ['turnaround', 'servo processing', 'DMA scheduling', 'timeout', 'CRC retries'],
            'not_a_worst_case_latency': True
        },
        'wheel_speed': {
            'geometry_revision': g['revision'], 'diameter_m': d_m,
            'scenarios': [{'linear_m_s': v, 'wheel_rad_s': v / (d_m / 2),
                           'wheel_rpm': v / (math.pi * d_m) * 60} for v in [0.1, 0.3]],
            'vendor_no_load_speed_rad_s_at_12V': 16.5,
            'loaded_speed_and_low_voltage_curve': None,
            'torque_or_balance_pass': 'NOT_TESTED'
        },
        'battery_energy_sensitivity': {
            'data_status': 'ASSUMED', 'nominal_cell_V': 3.7, 'series': 3,
            'capacity_Ah_range': [2.2, 2.6], 'usable_fraction_assumed': 0.8,
            'conversion_efficiency_assumed': 0.9,
            'nominal_Wh_range': [3 * 3.7 * q for q in [2.2, 2.6]],
            'one_hour_load_budget_W_range': [3 * 3.7 * q * 0.8 * 0.9 for q in [2.2, 2.6]],
            'measured_average_W': None, 'runtime_minutes': None,
            'note': 'Chemistry/pack/loads remain unselected. This is an allowable average-power sensitivity, not a runtime prediction.'
        }
    }
    target = HERE / 'reports/interface_calculations.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(f'Official {official["actual_baud"]:.3f} baud ({official["nominal_error_percent"]:.6f}%); '
          f'candidate {candidate["actual_baud"]:.0f} baud; wire-only lower bound '
          f'{report["two_motor_roundtrip"]["ideal_wire_only_us"]:.3f} us. Hardware NOT_TESTED.')


if __name__ == '__main__':
    main()
