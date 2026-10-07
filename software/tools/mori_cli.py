#!/usr/bin/env python3
"""MORI/1 local serial capture, explicit commands, offline replay and simulation.
No port discovery, automatic unlock, retries, flash, or network operations.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import re
import select
import secrets
import struct
import subprocess
import sys
import termios
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = 'MORI/1'
STATES = {'DISARMED', 'CALIBRATING', 'READY', 'BENCH', 'BALANCE', 'FAULT'}
FLOAT_RE = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')
FAULTS = {
    0: 'NONE', 1: 'SENSOR: IMU/monitor invalid, stale or nonfinite',
    2: 'ESTOP: physical emergency-stop chain not OK', 3: 'DRIVER: nFAULT asserted',
    4: 'LOW_VOLTAGE: below 6.0 V; support and disable', 5: 'OVERVOLTAGE: above 8.65 V',
    6: 'CURRENT: signed motor bus magnitude above 1.30 A (not winding current)',
    7: 'TEMPERATURE: motor NTC outside 0..65 C', 8: 'TILT: magnitude above 20 degrees',
    9: 'ENCODER: jump/read failure or driven counter freeze', 10: 'SATURATION: above duty limit over 200 ms',
    11: 'TIMING: frame deadline/period failure', 12: 'QUEUE: command/reply overflow',
    13: 'CONFIG: invalid mounting/configuration',
}
LIMITS = {'duty': [(-.12, .12), (-.12, .12)], 'move': [(-.3, .3), (-.1, .1)],
          'gains': [(0, 10), (0, 2), (0, 1), (0, .2)], 'head': [(-50, 50)]}
ZERO = {'info', 'status', 'calibrate', 'ack', 'confirm_signs', 'stop', 'disarm'}
HEADER = ('seq,device_us,state,fault,pitch_rad,v_m_s,bat_V,bus_A,TL_C,TR_C,uL,uR,enabled,run_us,wake_us,'
          'imu_io_us,monitor_io_us,encoder_us,fusion_us,feedback_us,pwm_submit_us,jitter_us,max_run_us,'
          'max_wake_us,max_jitter_us,sample_missed,log_dropped,command_overflows,reply_dropped,cal_count,'
          'head_enabled,p50_run_upper_us,p95_run_upper_us,p99_run_upper_us,p99_wake_upper_us,p99_jitter_upper_us,'
          'ax_m_s2,ay_m_s2,az_m_s2,gy_rad_s,vL_m_s,vR_m_s,raw_ax_m_s2,raw_ay_m_s2,raw_az_m_s2,'
          'raw_gx_rad_s,raw_gy_rad_s,raw_gz_rad_s,health_fault,driver_ok,estop_ok,imu_ok,monitor_ok,'
          'encoders_ok,low_battery,request_support,encoder_count_L,encoder_count_R').split(',')
LEGACY_HEADER = 'us,state,fault,pitch_rad,v_m_s,bat_V,motor_bus_A,TL_C,TR_C,uL,uR,run_us,wake_us,max_run_us,max_wake_us,jitter_us,max_jitter_us,dropped,rejected,cal_count'.split(',')
FLOAT_COLUMNS = {'pitch_rad', 'v_m_s', 'bat_V', 'bus_A', 'TL_C', 'TR_C', 'uL', 'uR', 'motor_bus_A'}
FLOAT_COLUMNS.update({'ax_m_s2','ay_m_s2','az_m_s2','gy_rad_s','vL_m_s','vR_m_s','raw_ax_m_s2','raw_ay_m_s2','raw_az_m_s2','raw_gx_rad_s','raw_gy_rad_s','raw_gz_rad_s'})
TIMINGS = ['run_us', 'wake_us', 'imu_io_us', 'monitor_io_us', 'encoder_us', 'fusion_us', 'feedback_us', 'pwm_submit_us', 'jitter_us']


def validate_command(command):
    if not command or any(ord(c) < 32 or ord(c) > 126 for c in command):
        raise ValueError('command must be one printable ASCII line')
    if len(command) > 100:  # leave room for @uint32 and one space
        raise ValueError('command too long')
    tokens = command.split(' ')
    tokens = [t for t in tokens if t]
    if not tokens:
        raise ValueError('empty command')
    name = tokens[0]
    if name in ZERO and len(tokens) == 1:
        return command
    if tokens in [['arm', 'bench'], ['arm', 'balance']]:
        return command
    if name not in LIMITS or len(tokens) != 1 + len(LIMITS[name]):
        raise ValueError('unknown command or extra/missing fields')
    for i, (token, (lo, hi)) in enumerate(zip(tokens[1:], LIMITS[name])):
        if not FLOAT_RE.fullmatch(token):
            raise ValueError('strict finite decimal required')
        value = float(token)
        if not math.isfinite(value):
            raise ValueError('nonfinite or overflow')
        try:
            rounded = struct.unpack('f', struct.pack('f', value))[0]
        except (OverflowError, struct.error) as e:
            raise ValueError('float32 overflow') from e
        # strtof ERANGE includes subnormal underflow. Also reject textual nonzero -> 0.
        mantissa = re.split('[eE]', token)[0]
        textual_nonzero = any(c in '123456789' for c in mantissa)
        if textual_nonzero and (rounded == 0 or abs(rounded) < 1.1754943508222875e-38):
            raise ValueError('float32 underflow')
        if not lo <= value <= hi or (name == 'gains' and i < 2 and value <= 0):
            raise ValueError(f'{name} parameter {i+1} out of range')
    return command


def request_bytes(command, request_id):
    validate_command(command)
    if not 1 <= request_id <= 0xffffffff:
        raise ValueError('request id must be 1..4294967295')
    payload = f'@{request_id} {command}\n'.encode('ascii')
    if len(payload) > 120:
        raise ValueError('wire command exceeds firmware limit')
    return payload


def quantiles(values):
    values = sorted(values)
    if not values:
        return {'status': 'NOT_TESTED', 'samples': 0}
    return {'status': 'PASS', 'samples': len(values),
            **{f'p{p}': values[max(0, math.ceil(len(values)*p/100)-1)] for p in (50, 95, 99)},
            'max': values[-1]}


def validate_row(row, header):
    if len(row) != len(header):
        raise ValueError('truncated or extra CSV fields')
    data = dict(zip(header, row))
    for key, value in data.items():
        if key == 'state':
            if value not in STATES:
                raise ValueError('invalid state')
        elif key in FLOAT_COLUMNS:
            if not FLOAT_RE.fullmatch(value) or not math.isfinite(float(value)):
                raise ValueError('nonfinite telemetry')
            data[key] = float(value)
        elif key in {'encoder_count_L', 'encoder_count_R'}:
            if not re.fullmatch(r'-?\d+', value) or not -0x80000000 <= int(value) <= 0x7fffffff:
                raise ValueError('signed encoder count overflow')
            data[key] = int(value)
        else:
            if not re.fullmatch(r'\d+', value):
                raise ValueError(f'invalid unsigned field {key}')
            number = int(value)
            if number > (0xffffffffffffffff if key in {'device_us', 'us'} else 0xffffffff):
                raise ValueError('integer overflow')
            data[key] = number
    if data['fault'] not in FAULTS:
        raise ValueError('unknown fault version')
    return data


class Recorder:
    """Preserves all raw input plus a strict CSV and source-labelled metadata."""
    def __init__(self, path, source, stride=None):
        self.path = pathlib.Path(path)
        if source == 'SIMULATED' and 'SIMULATED' not in self.path.name:
            raise ValueError('simulated recording filename must contain SIMULATED')
        if source != 'SIMULATED' and 'SIMULATED' in self.path.name:
            raise ValueError('device recording must not use a SIMULATED name')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = self.path.open('x', newline='')
        self.raw_file = self.path.with_suffix('.raw.jsonl').open('x')
        self.writer = csv.writer(self.csv_file)
        self.header = None
        self.rows = []
        self.info = []
        self.replies = []
        self.rtts = []
        self.invalid = 0
        self.source = source
        self.stride = stride
        self.started = dt.datetime.now(dt.timezone.utc).isoformat()

    def feed(self, line, direction='RX'):
        utc = dt.datetime.now(dt.timezone.utc).isoformat()
        mono = time.monotonic_ns()
        self.raw_file.write(json.dumps({'host_utc': utc, 'host_monotonic_ns': mono,
                                      'source': self.source, 'direction': direction, 'line': line})+'\n')
        self.raw_file.flush()
        if line.startswith('INVALID '):
            self.invalid += 1
        if direction == 'TX':
            return
        if line.startswith('MOUNT '):
            self.info.append(line)
            return
        if line.startswith('INFO '):
            self.info.append(line)
            match = re.search(r'\btelemetry_stride=(\d+)\b', line)
            if match:
                self.stride = int(match[1])
            return
        if line.startswith(('ACK ', 'REJECT ')):
            self.replies.append(line)
            return
        if line.startswith('HEADER '):
            parts = line.split(' ', 2)
            if len(parts) != 3 or parts[1] != VERSION or parts[2].split(',') != HEADER:
                self.invalid += 1
                self.header = None
                return
            new_header = HEADER
        elif line.split(',') == LEGACY_HEADER:
            new_header = LEGACY_HEADER
        else:
            new_header = None
        if new_header:
            if self.header and self.header != new_header:
                self.invalid += 1
                return
            if not self.header:
                self.header = new_header
                self.writer.writerow(['host_utc', 'host_monotonic_ns', 'source']+self.header)
            return
        payload = line[5:] if line.startswith('DATA ') else line
        if not (line.startswith('DATA ') or (self.header == LEGACY_HEADER and line[:1].isdigit())):
            return  # boot chatter is retained as raw input
        try:
            if not self.header:
                raise ValueError('telemetry without known header')
            data = validate_row(next(csv.reader([payload])), self.header)
            self.rows.append(data)
            self.writer.writerow([utc, mono, self.source]+payload.split(','))
            self.csv_file.flush()
        except (ValueError, csv.Error):
            self.invalid += 1

    def close(self):
        self.csv_file.close()
        self.raw_file.close()
        result = summarize(self.rows, self.source, self.stride)
        result['command_rtt_us'] = quantiles(self.rtts)
        result['device_metadata'] = {key:value for line in self.info if line.startswith('INFO ') for key,value in (token.split('=',1) for token in line.split()[3:] if '=' in token)}
        result.update(protocol=VERSION, source=self.source, start_utc=self.started,
                      physical_validation='NOT_TESTED', invalid_rows=self.invalid,
                      info=self.info, replies=self.replies,
                      csv_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                      raw_sha256=hashlib.sha256(self.path.with_suffix('.raw.jsonl').read_bytes()).hexdigest())
        self.path.with_suffix('.meta.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
        return result


def summarize(rows, source, stride=None):
    resets = 0
    missing = 0
    for a, b in zip(rows, rows[1:]):
        if b.get('device_us', b.get('us', 0)) <= a.get('device_us', a.get('us', 0)) or b.get('seq', 0) < a.get('seq', 0):
            resets += 1
        elif stride and 'seq' in a:
            missing += max(0, (b['seq']-a['seq'])//stride-1)
    return {'status': 'PASS' if rows else 'NOT_TESTED', 'source': source, 'rows': len(rows),
            'timing_evidence': 'INJECTED_SIMULATION' if source == 'SIMULATED' else 'DEVICE_REPORTED_NOT_EXTERNAL_MEASUREMENT',
            'timing_sample_quantiles_us': {k: quantiles([r[k] for r in rows if k in r]) for k in TIMINGS},
            'device_all_frame_max_us': {k: max((r[k] for r in rows if k in r), default=None)
                                        for k in ('max_run_us', 'max_wake_us', 'max_jitter_us')},
            'resets_or_clock_discontinuities': resets,
            'telemetry_stride': stride, 'estimated_missing_telemetry_rows': missing if stride else None,
            'device_counters_max': {k: max((r[k] for r in rows if k in r), default=None)
                                    for k in ('sample_missed', 'log_dropped', 'command_overflows', 'reply_dropped', 'dropped')},
            'faults': sorted({FAULTS[r['fault']] for r in rows if r['fault']}),
            'command_rtt_us': {'status': 'NOT_TESTED'},
            'warning': 'Quantiles cover recorded rows; all-frame histograms are 100us buckets, UINT32_MAX means >3200us. Maxima and counters restart on reset. No hardware PASS is inferred.'}


def replay(path):
    path = pathlib.Path(path)
    with path.open(newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        enriched = header[:3] == ['host_utc', 'host_monotonic_ns', 'source']
        actual = header[3:] if enriched else header
        if actual not in (HEADER, LEGACY_HEADER):
            raise ValueError('unsupported CSV schema')
        rows = []
        sources = set()
        for row in reader:
            if enriched:
                if len(row) != len(header):
                    raise ValueError('truncated captured row')
                sources.add(row[2]); row = row[3:]
            rows.append(validate_row(row, actual))
    source = next(iter(sources)) if len(sources) == 1 else 'LEGACY_UNVERIFIED'
    if source == 'SIMULATED' and 'SIMULATED' not in path.name:
        raise ValueError('SIMULATED source requires SIMULATED filename')
    stride = None
    meta_path = path.with_suffix('.meta.json')
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get('csv_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('CSV hash does not match metadata')
        stride = meta.get('telemetry_stride')
    result = summarize(rows, source, stride)
    if meta_path.exists():
        result['device_metadata'] = meta.get('device_metadata', {})
    return result


class SerialPort:
    """POSIX UART; explicit path, no discovery, no modem-control toggles/reconnect."""
    def __init__(self, path):
        if not path.startswith('/'):
            raise ValueError('explicit absolute known serial port is required')
        self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.buffer = bytearray()
        self.discard = False
        try:
            import fcntl
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.original = termios.tcgetattr(self.fd)
            attrs = termios.tcgetattr(self.fd)
            attrs[0] = 0; attrs[1] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] = 0; attrs[4] = termios.B115200; attrs[5] = termios.B115200
            attrs[6][termios.VMIN] = 0; attrs[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        except Exception:
            os.close(self.fd)
            raise

    def write(self, data):
        # No partial retry that might accidentally form a different valid command.
        if os.write(self.fd, data) != len(data):
            raise OSError('partial command write; outcome unknown; do not retry')

    def lines(self, timeout):
        if not select.select([self.fd], [], [], timeout)[0]:
            return []
        data = os.read(self.fd, 4096)
        if not data:
            raise OSError('serial disconnected; no automatic reconnect')
        result = []
        for byte in data:
            if byte in (10, 13):
                if self.discard:
                    result.append('INVALID serial line overflow')
                elif self.buffer:
                    result.append(self.buffer.decode('ascii', errors='replace'))
                self.buffer.clear(); self.discard = False
            elif len(self.buffer) >= 4096:
                self.discard = True
            elif not self.discard:
                self.buffer.append(byte)
        return result

    def close(self):
        try:
            termios.tcsetattr(self.fd, termios.TCSANOW, self.original)
        finally:
            os.close(self.fd)


def transaction(port, command, request_id, recorder, timeout):
    payload = request_bytes(command, request_id)
    recorder.feed(payload.decode().rstrip(), 'TX')
    start = time.monotonic_ns(); port.write(payload)
    deadline = time.monotonic() + timeout
    information = None
    while time.monotonic() < deadline:
        for line in port.lines(min(.1, max(0, deadline-time.monotonic()))):
            recorder.feed(line)
            if line.startswith(f'INFO {request_id} {VERSION} '):
                information = line
            if line.startswith((f'ACK {request_id} {VERSION} ', f'REJECT {request_id} {VERSION} ')):
                rtt = (time.monotonic_ns()-start)/1000
                recorder.rtts.append(rtt)
                return {'response': line, 'rtt_us': rtt, 'info': information}
    raise TimeoutError('ACK deadline exceeded: command outcome UNKNOWN; no retry or automatic disarm')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='action', required=True)
    sim = subs.add_parser('simulate'); sim.add_argument('--output', required=True, type=pathlib.Path)
    sim.add_argument('--frames', type=int, default=1000)
    sim.add_argument('--scenario', choices=['normal', 'estop', 'imu_missing', 'reset'], default='normal')
    rep = subs.add_parser('replay'); rep.add_argument('csv', type=pathlib.Path)
    val = subs.add_parser('validate'); val.add_argument('command')
    fault = subs.add_parser('fault'); fault.add_argument('code', type=int)
    for verb in ['capture', 'send']:
        serial = subs.add_parser(verb); serial.add_argument('--port', required=True)
        serial.add_argument('--output', required=True, type=pathlib.Path)
        if verb == 'capture':
            serial.add_argument('--seconds', type=float, default=30)
        else:
            serial.add_argument('--command', required=True, action='append'); serial.add_argument('--timeout', type=float, default=3)
    a = p.parse_args(argv)
    if a.action == 'validate':
        validate_command(a.command); print('PASS strict command validation (no device IO)'); return 0
    if a.action == 'fault':
        print(FAULTS.get(a.code, 'UNKNOWN FAULT VERSION')); return 0 if a.code in FAULTS else 2
    if a.action == 'replay':
        result = replay(a.csv)
    elif a.action == 'simulate':
        if not 1 <= a.frames <= 1000000:
            raise ValueError('frames must be 1..1000000')
        executable = ROOT/'reports/bin/SIMULATED_device'
        if not executable.exists():
            raise ValueError('run bash software/scripts/build_simulator.sh first')
        recorder = Recorder(a.output, 'SIMULATED', 1)
        try:
            proc = subprocess.Popen([str(executable), str(a.frames), a.scenario], stdout=subprocess.PIPE, text=True)
            for line in proc.stdout:
                recorder.feed(line.rstrip('\r\n'))
            if proc.wait() != 0:
                raise RuntimeError('simulator failed')
        finally:
            result = recorder.close()
    else:
        if a.action == 'send':
            for command in a.command:
                validate_command(command)  # before opening any port
            if len(a.command) > 8:
                raise ValueError('at most 8 explicitly supplied commands per session')
            if not math.isfinite(a.timeout) or not .1 <= a.timeout <= 60:
                raise ValueError('timeout must be .1..60 seconds')
        elif not math.isfinite(a.seconds) or not .1 <= a.seconds <= 3600:
            raise ValueError('capture duration must be .1..3600 seconds')
        recorder = Recorder(a.output, 'DEVICE', 40)
        port = None
        try:
            port = SerialPort(a.port)
            request_id = secrets.randbelow(0xfffffff0)+1
            hello = transaction(port, 'info', request_id, recorder, getattr(a, 'timeout', 3))
            if not hello['response'].startswith('ACK ') or not hello['info']:
                raise ValueError('MORI/1 device handshake not confirmed')
            if a.action == 'capture':
                deadline = time.monotonic()+a.seconds
                while time.monotonic() < deadline:
                    for line in port.lines(.1):
                        recorder.feed(line)
            else:
                # Queries only. Never infer permission for arm/confirm/gains/ack.
                for offset, command in enumerate(a.command, 1):
                    response = transaction(port, command, request_id+offset, recorder, a.timeout)
                    print(json.dumps(response, ensure_ascii=False))
                    if response['response'].startswith('REJECT '):
                        return 3
        finally:
            if port:
                port.close()
            result = recorder.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, TimeoutError, RuntimeError) as e:
        print(f'FAIL: {e}', file=sys.stderr)
        sys.exit(2)
