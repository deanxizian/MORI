#!/usr/bin/env python3
"""One explicitly armed, unloaded S288 jog. Default is a zero-TX plan.

This bench tool is not a balancing controller or a hardware torque limiter.
No broadcast, ID change, boot task, persistent drive, or automatic fault re-arm.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import signal
import struct
import time

import bench
from protocol import FeedbackStream, RATIO, crc32_words, locked_query, valid_id

PLAN = dict(speed_rad_s=0.20, kd=0.25, kp=0.0, feedforward_nm=0.0,
            ramp_s=0.5, hold_s=0.8, duration_s=1.8, frequency_hz=50,
            max_displacement_rad=0.40, max_feedback_speed_rad_s=0.45,
            max_feedback_torque_nm=0.12, max_temperature_c=60,
            voltage_min_v=7.0, voltage_max_v=12.5,
            feedback_deadline_s=0.06, maximum_loop_gap_s=0.12)


def select_duration(seconds):
    """Only the original short trial or the user-requested 10 s profile.

    This is selected once before opening hardware; speed, gains and all other
    health limits stay unchanged. No arbitrary persistent-motion duration.
    """
    if seconds not in (1.8, 10.0):
        raise ValueError('Supported durations are 1.8 or 10 seconds')
    PLAN.update(duration_s=seconds, hold_s=seconds - 2 * PLAN['ramp_s'],
                max_displacement_rad=0.4 if seconds == 1.8 else 2.1)


def select_profile(duration_s=1.8, speed_multiplier=1):
    if speed_multiplier not in (1, 10):
        raise ValueError('Only the requested 1x and 10x speeds are supported')
    if speed_multiplier == 10 and duration_s != 10:
        raise ValueError('The 10x profile requires the bounded 10 second run')
    PLAN.update(speed_rad_s=.2, ramp_s=.5, max_feedback_speed_rad_s=.45)
    select_duration(duration_s)
    if speed_multiplier == 10:
        # Explicitly requested on 2026-10-13. Ramp more gently than an abrupt
        # 10x step; retain Kd, zero Kp/FF and the existing torque/thermal limits.
        PLAN.update(speed_rad_s=2., ramp_s=2., hold_s=6.,
                    max_feedback_speed_rad_s=2.5, max_displacement_rad=18.)


def jog_packet(motor_id, speed):
    valid_id(motor_id)
    if not math.isfinite(speed) or not 0 <= speed <= PLAN['speed_rad_s']:
        raise ValueError('Speed outside this fixed, positive-only bench plan')
    raw_speed = round(speed * RATIO * 2.56 / math.tau)
    raw_kd = round(PLAN['kd'] / RATIO**2 * 128000000)
    body = bytes([0xFE, 0xEE, motor_id | 0x90, 0])
    body += struct.pack('<hhihh', 0, raw_speed, 0, 0, raw_kd)
    return body + struct.pack('<I', crc32_words(body))


def manual_timeout_clear_packet(motor_id):
    # Only used once, in mode 0, after an explicit operator acknowledgement.
    body = bytes([0xFE, 0xEE, valid_id(motor_id), 0]) + bytes(12)
    return body + struct.pack('<I', crc32_words(body))


def health(row, expected_mode, origin=None, allow_initial_timeout=False):
    if row['mode'] != expected_mode:
        raise RuntimeError('unexpected_mode')
    if row['errors_raw'] or row['warning_raw']:
        raise RuntimeError('servo_error_or_warning')
    if row['timeout_active'] and not allow_initial_timeout:
        raise RuntimeError('timeout_protection_active; no automatic re-arm')
    if not PLAN['voltage_min_v'] <= row['voltage_v'] <= PLAN['voltage_max_v']:
        raise RuntimeError('voltage_outside_conservative_bench_window')
    if not -10 <= row['temperature_c'] < PLAN['max_temperature_c']:
        raise RuntimeError('temperature_outside_bench_window')
    if abs(row['speed_rad_s']) > PLAN['max_feedback_speed_rad_s']:
        raise RuntimeError('feedback_speed_limit')
    if abs(row['torque_estimate_nm']) > PLAN['max_feedback_torque_nm']:
        raise RuntimeError('feedback_torque_limit')
    if origin is not None and abs(row['position_rad'] - origin) > PLAN['max_displacement_rad']:
        raise RuntimeError('feedback_displacement_limit')


def run_trial(exchange, motor_id, report, *, acknowledge_timeout=False,
              now=time.monotonic, sleep=time.sleep):
    """All failures exit through stop; no fault is cleared during motion."""
    report.update(status='FAIL', plan=PLAN.copy(), timeout_cleared_once=False,
                  stop_verified=False)
    origin = None
    try:
        first = exchange(locked_query(motor_id), 'initial')
        health(first, 0, allow_initial_timeout=True)
        if abs(first['speed_rad_s']) > 0.04:
            raise RuntimeError('servo_not_stationary_before_arm')
        if first['timeout_active']:
            if not acknowledge_timeout:
                raise RuntimeError('manual_timeout_acknowledgement_required')
            cleared = exchange(manual_timeout_clear_packet(motor_id), 'manual_timeout_clear')
            health(cleared, 0, allow_initial_timeout=True)
            sleep(0.02)
            health(exchange(locked_query(motor_id), 'verify_timeout_clear'), 0)
            report['timeout_cleared_once'] = True
        # Restore timeout protection immediately and maintain traffic to completion.
        for _ in range(10):
            row = exchange(locked_query(motor_id), 'preflight')
            health(row, 0)
            if abs(row['speed_rad_s']) > 0.04:
                raise RuntimeError('servo_not_stationary_during_preflight')
            sleep(0.02)
        origin = row['position_rad']
        report['start_position_rad'] = origin
        # The immediate feedback describes the preceding control cycle. Enter
        # FOC at zero speed first; after 20 ms require mode1 before any ramp.
        armed = exchange(jog_packet(motor_id, 0.0), 'arm_zero_transition')
        if armed['mode'] not in (0, 1):
            raise RuntimeError('unexpected_mode_during_arm_transition')
        health(armed, armed['mode'], origin)
        sleep(0.02)
        armed = exchange(jog_packet(motor_id, 0.0), 'arm_zero_confirm')
        health(armed, 1, origin)
        if abs(armed['speed_rad_s']) > 0.04:
            raise RuntimeError('servo_not_stationary_at_zero_speed_arm')
        start = previous = now()
        ticks = 0
        while now() - start <= PLAN['duration_s']:
            tick = now()
            elapsed = tick - start
            if tick - previous > PLAN['maximum_loop_gap_s']:
                raise RuntimeError('control_loop_gap')
            previous = tick
            scale = max(0.0, min(1.0, elapsed / PLAN['ramp_s'],
                                (PLAN['duration_s'] - elapsed) / PLAN['ramp_s']))
            row = exchange(jog_packet(motor_id, PLAN['speed_rad_s'] * scale), 'jog')
            health(row, 1, origin)
            ticks += 1
            sleep(max(0.0, 1 / PLAN['frequency_hz'] - (now() - tick)))
        if now() - previous > PLAN['maximum_loop_gap_s']:
            raise RuntimeError('control_loop_gap_at_completion')
        if ticks < math.ceil(PLAN['duration_s'] * PLAN['frequency_hz'] * 2 / 3):
            raise RuntimeError('insufficient_control_cycles')
        report['control_cycles'] = ticks
        report['motion_elapsed_s'] = now() - start
        report['status'] = 'PASS'
    except (Exception, KeyboardInterrupt) as exc:
        report['reason'] = str(exc) or type(exc).__name__
    finally:
        # Even after a failed transaction, make bounded mode-0 stop attempts.
        # Deliver stop once before verifying its result on following cycles.
        try:
            transition = exchange(locked_query(motor_id), 'stop_transition')
            if transition['mode'] not in (0, 1):
                raise RuntimeError('unexpected_mode_during_stop_transition')
            health(transition, transition['mode'], origin, allow_initial_timeout=True)
        except (Exception, KeyboardInterrupt) as exc:
            report.setdefault('stop_transition_findings', []).append(str(exc))
        sleep(0.02)
        stopped = []
        for _ in range(3):
            try:
                row = exchange(locked_query(motor_id), 'stop')
                health(row, 0, origin, allow_initial_timeout=True)
                stopped.append(row)
            except (Exception, KeyboardInterrupt) as exc:
                report.setdefault('stop_errors', []).append(str(exc))
            sleep(0.05)
        report['stop_verified'] = len(stopped) == 3 and all(
            abs(r['speed_rad_s']) <= 0.04 for r in stopped)
        if stopped and origin is not None:
            report['end_position_rad'] = stopped[-1]['position_rad']
            report['displacement_deg'] = math.degrees(stopped[-1]['position_rad'] - origin)
        if not report['stop_verified']:
            report['status'] = 'FAIL'
            report['stop_action_required'] = 'physically disconnect servo power'
        elif report['status'] == 'PASS' and abs(report.get('displacement_deg', 0)) < 1:
            report['status'] = 'FAIL'
            report['reason'] = 'movement_not_demonstrated'
    return report


def serial_exchange(port, motor_id, report):
    def exchange(packet, phase):
        port.reset_input_buffer()
        start = time.monotonic()
        item = dict(phase=phase, monotonic=start, tx_hex=packet.hex())
        report['transactions'].append(item)
        written = port.write(packet)
        item['bytes_written'] = written
        if written != len(packet):
            raise OSError('incomplete_write')
        stream = FeedbackStream(motor_id)
        deadline = start + PLAN['feedback_deadline_s']
        while time.monotonic() < deadline:
            rows = stream.feed(port.read(min(256, max(1, port.in_waiting))))
            if rows:
                item['feedback'] = rows[0]
                item['response_ms'] = (time.monotonic() - start) * 1000
                if stream.bad_frames or stream.discarded_bytes or len(rows) != 1:
                    raise RuntimeError('noisy_or_ambiguous_bus_feedback')
                if time.monotonic() > deadline:
                    raise RuntimeError('late_feedback')
                return rows[0]
        raise TimeoutError('no_valid_reply_within_60ms')
    return exchange


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--id', type=int, choices=range(15))
    parser.add_argument('--arm-single-servo', action='store_true')
    parser.add_argument('--operator-ready', action='store_true')
    parser.add_argument('--ack-query-timeout', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if not args.arm_single_servo:
        print(json.dumps(dict(status='NOT_TESTED', plan=PLAN, commands_sent=0), indent=2))
        return 0
    if not (args.operator_ready and args.port and args.id is not None and args.output):
        parser.error('arming requires port, id, unique output and onsite operator-ready')
    if platform.system() != 'Linux':
        parser.error('serial operation requires the Linux Pi')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve evidence before opening hardware; refuse existing log paths.
    with args.output.open('x') as handle:
        report = dict(utc=datetime.now(timezone.utc).isoformat(), status='BLOCKED',
                      servo_id=args.id, operator_ready=True, transactions=[])
        def interrupted(signum, _frame):
            raise KeyboardInterrupt(f'signal_{signum}')
        for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(sig, interrupted)
        try:
            record = bench.select_port(bench.port_records(), args.port)
            report['selected_port'] = record
            with bench.open_port(record) as port:
                port.timeout, port.write_timeout = 0.004, 0.04
                run_trial(serial_exchange(port, args.id, report), args.id, report,
                          acknowledge_timeout=args.ack_query_timeout)
        except (Exception, KeyboardInterrupt) as exc:
            report['reason'] = str(exc) or type(exc).__name__
        finally:
            report['motion_commands_sent'] = sum(
                t.get('bytes_written') == 20 and
                ((bytes.fromhex(t['tx_hex'])[2] >> 4) & 7) == 1
                for t in report['transactions'])
            json.dump(report, handle, indent=2)
            handle.write('\n')
        print(json.dumps({k: v for k, v in report.items() if k != 'transactions'}, indent=2))
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
