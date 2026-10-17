#!/usr/bin/env python3
"""Manual S288 bench checks. No argument means USB inventory, with zero TX.

Only scan/read issue commands, exclusively mode=0, timeout=1, all targets zero.
They require explicit physical preconditions and a single connected servo.
No startup service or motion control is installed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

from protocol import BAUD, FeedbackStream, feedback_findings, locked_query

UNITREE = (0x2E3C, 0x7640)
ADAPTER_SERIAL = '366DCBC91974'


def port_records():
    from serial.tools import list_ports
    return [{'device': p.device, 'vid': p.vid, 'pid': p.pid,
             'serial': p.serial_number, 'location': p.location,
             'interface': p.interface, 'product': p.product}
            for p in list_ports.comports()]


def select_port(records, requested=None):
    matches = [p for p in records if (p['vid'], p['pid']) == UNITREE and
               p['serial'] == ADAPTER_SERIAL]
    if requested:
        requested = str(Path(requested).resolve(strict=True))
        matches = [p for p in matches if str(Path(p['device']).resolve()) == requested]
    if len(matches) != 1:
        raise ValueError('Expected exactly one Unitree 2e3c:7640 port. '
                         'Use check, then select an explicit --port if multiple exist. '
                         'CAM and generic/unidentified serial ports are rejected.')
    return matches[0]


def open_port(record):
    import serial
    # Set control-line states BEFORE open; no data writes during this function.
    port = serial.Serial(port=None, baudrate=BAUD, bytesize=8, parity='N',
                         stopbits=1, timeout=0.02, write_timeout=0.2,
                         xonxoff=False, rtscts=False, dsrdtr=False, exclusive=True)
    port.dtr = False
    port.rts = False
    port.port = record['device']
    port.open()
    try:
        select_port(port_records(), record['device'])
    except Exception:
        port.close()
        raise
    return port


def query(port, motor_id, audit):
    packet = locked_query(motor_id)
    stream = FeedbackStream(motor_id)
    # Discard a previous transaction's stale bytes; never reuse them as a reply.
    port.reset_input_buffer()
    start = time.monotonic()
    audit['commands_attempted'] += 1
    written = port.write(packet)
    audit['bytes_written'] += written
    if written != len(packet):
        raise OSError('Incomplete command write')
    audit['commands_sent'] += 1
    deadline = start + 0.25
    received = 0
    while time.monotonic() < deadline and received < 4096:
        chunk = port.read(min(256, max(1, port.in_waiting)))
        received += len(chunk)
        rows = stream.feed(chunk)
        if rows:
            row = rows[0]
            row.update(response_ms=round((time.monotonic() - start) * 1000, 3),
                       bad_frames=stream.bad_frames, discarded_bytes=stream.discarded_bytes,
                       findings=feedback_findings(row))
            return row
    return {'id': motor_id, 'findings': ['no_valid_reply'],
            'received_bytes': received, 'bad_frames': stream.bad_frames,
            'discarded_bytes': stream.discarded_bytes}


def emit(result, output):
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        # Do not overwrite another measurement.
        with output.open('x') as handle:
            handle.write(rendered)
    print(rendered, end='')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['check', 'port-check', 'scan', 'read'],
                        default='check')
    parser.add_argument('--port')
    parser.add_argument('--id', type=int, choices=range(15))
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--hz', type=float, default=10)
    parser.add_argument('--single-servo', action='store_true')
    parser.add_argument('--power-and-wiring-checked', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.action in ('scan', 'read'):
        if not (args.single_servo and args.power_and_wiring_checked):
            parser.error('scan/read requires --single-servo --power-and-wiring-checked; '
                         'mode=0 queries are commands, not passive reads')
        if args.action == 'read' and args.id is None:
            parser.error('read requires --id')
        if not (1 <= args.samples <= 200 and 1 <= args.hz <= 50):
            parser.error('samples must be 1..200 and hz 1..50')
    if args.output and args.output.exists():
        parser.error('output already exists; choose a new evidence filename')
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'action': args.action,
              'host': platform.node(), 'python': platform.python_version(),
              'commands_attempted': 0, 'commands_sent': 0, 'bytes_written': 0,
              'motion_commands_sent': 0, 'status': 'BLOCKED',
              'usb_baud_acceptance': 'NOT_TESTED', 'servo_link': 'NOT_TESTED'}
    try:
        import serial
        records = port_records()
        result['pyserial'] = serial.VERSION
        result['unitree_ports'] = [p for p in records if (p['vid'], p['pid']) == UNITREE]
        result['cam_ports'] = [p for p in records if (p['vid'], p['pid']) == (0x303A, 0x1001)]
        if args.action == 'check':
            result['status'] = 'PASS' if result['unitree_ports'] else 'BLOCKED'
            emit(result, args.output)
            return 0 if result['status'] == 'PASS' else 2
        if platform.system() != 'Linux':
            raise ValueError('Serial operations are prepared only for the Linux Pi host')
        record = select_port(records, args.port)
        result['selected_port'] = record
        with open_port(record) as port:
            result['serial_settings'] = port.get_settings()
            if port.baudrate != BAUD:
                raise OSError('Serial configuration is not 6000000 baud')
            result['usb_baud_acceptance'] = 'PASS'
            if args.action == 'port-check':
                result['status'] = 'PASS'
            else:
                result['replies'] = []
                ids = range(15) if args.action == 'scan' else [args.id] * args.samples
                for motor_id in ids:
                    # There is only one packet builder, with no arbitrary mode/gain input.
                    row = query(port, motor_id, result)
                    result['replies'].append(row)
                    if 'raw_hex' in row:
                        result['servo_link'] = 'PASS'
                        if row['findings'] or args.action == 'scan':
                            break
                    elif args.action == 'read':
                        break
                    time.sleep(1 / args.hz)
                good = [r for r in result['replies'] if 'raw_hex' in r]
                result['status'] = 'PASS' if good and not good[-1]['findings'] else 'FAIL'
                if args.action == 'read' and len(good) != args.samples:
                    result['status'] = 'FAIL'
    except KeyboardInterrupt:
        result['status'] = 'FAIL'
        result['reason'] = 'operator_interrupted; no motion command was issued'
    except (OSError, ValueError, ImportError) as exc:
        result['status'] = 'BLOCKED' if not result['commands_sent'] else 'FAIL'
        result['reason'] = str(exc)
    emit(result, args.output)
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
