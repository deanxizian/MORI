#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MORI Pi boot/stand/remote runtime. No arguments: no hardware access."""
import argparse
from collections import deque
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

HERE = Path(__file__).resolve().parent


def verify_tree(root, manifest):
    for name, expected in manifest['sha256'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('source_manifest_mismatch: ' + name)


def load_config(path):
    config = json.loads(path.read_text())
    required = {'source', 'calibration', 'calibration_sha256', 'source_manifest_sha256',
                'runtime_manifest_sha256', 'state_directory', 'run_directory'}
    if set(config) != required:
        raise ValueError('unexpected_or_missing_config_fields')
    source = Path(config['source']).resolve()
    raw = (source / 'source_manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != config['source_manifest_sha256']:
        raise ValueError('base_manifest_mismatch')
    verify_tree(source, json.loads(raw))
    runtime_raw = (HERE / 'manifest.json').read_bytes()
    if hashlib.sha256(runtime_raw).hexdigest() != config['runtime_manifest_sha256']:
        raise ValueError('runtime_manifest_mismatch')
    verify_tree(HERE, json.loads(runtime_raw))
    calibration = Path(config['calibration']).read_bytes()
    if hashlib.sha256(calibration).hexdigest() != config['calibration_sha256']:
        raise ValueError('calibration_mismatch')
    return config, json.loads(calibration)


def execute(config, calibration):
    from support import StatusOutput, begin_session, finish_session
    from preflight import RawIMU, CycleGC, PORT
    from air_trial import exchange_for, imu_configuration, display_indicator
    from attitude import validate_calibration
    from remote_drive_keys import Keys, KeyWorker
    from two_deck_remote_drive import RemoteTravel
    from accepted_write import AcceptedPortOpener
    from controller import Controller, PLAN
    import bench
    from engine import run
    from fall_recovery import run_stand_cycles, archive_motion_stop, initial_timeout_ack_allowed

    validate_calibration(calibration)
    state, runtime = Path(config['state_directory']), Path(config['run_directory'])
    state.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)
    # Across services/manual launches. The underlying motor/CAM/IMU locks
    # additionally exclude the old trial tools and other device owners.
    with (runtime / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        startup = begin_session(state)
        report = dict(utc=datetime.now(timezone.utc).isoformat(), status='FAIL',
                      runtime_version='0.1.12', continuous=True, config=config, startup=startup,
                      evidence_scope='bounded tail, not a complete high-rate recording',
                      imu={}, gc={}, per_id={m:dict(transactions=deque(maxlen=1000)) for m in (0, 1)})
        interrupted = False

        def stop(sig, _):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt('signal_' + str(sig))

        handlers = {s:signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        previous_interval = sys.getswitchinterval()
        sys.setswitchinterval(.001)
        writer = AcceptedPortOpener(bench.open_port)
        try:
            with StatusOutput(runtime) as output, ExitStack() as stack:
                if startup['recovered_interrupted_boot']:
                    output('BOOT_RECOVERED: 检测到上次运行中断后的新一轮上电，重新进行禁能检查和完整扶正等待。')
                # Wait for USB enumeration without accessing actuators.
                output('WAIT_DEVICES: 等待电机与显示模块枚举。')
                from cam_indicator import PORT as CAM_PORT
                deadline = time.monotonic() + 60.
                while not all(Path(p).exists() for p in (PORT, CAM_PORT)):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('device_enumeration_timeout')
                    time.sleep(.2)
                keys = Keys()
                stack.enter_context(KeyWorker(keys, report.setdefault('remote', {})))
                indicator = stack.enter_context(display_indicator(report.setdefault('cam_indicator', {}), PLAN))
                stack.enter_context(CycleGC(report['gc'], 'defer'))
                imu = stack.enter_context(RawIMU(report['imu'], **imu_configuration(PLAN)))
                record = bench.select_port(bench.port_records(), PORT)
                with writer.open(record) as port:
                    port.timeout, port.write_timeout = .001, .008
                    def attempt(report, *, require_reposition):
                        controller = Controller(keys, output_check=output.check)
                        original_observe = controller.observe_pair

                        def observe(sample):
                            original_observe(sample)
                            output.telemetry = dict(controller.last_telemetry, stand_cycle=report.get('stand_cycle', 0))

                        last_wait_update = -float('inf')

                        def observe_wait(attitude, speeds, stable_s, qualifying, pitch_span):
                            nonlocal last_wait_update
                            if attitude['t'] - last_wait_update < .5:
                                return
                            last_wait_update = attitude['t']
                            state = dict(pitch_deg=attitude['pitch_deg'], roll_deg=attitude['roll_deg'],
                                         pitch_rate_dps=attitude['pitch_rate_dps'],
                                         max_wheel_speed_rad_s=max(abs(v) for v in speeds.values()),
                                         qualifying=qualifying, stable_s=round(stable_s, 2), required_s=1.5,
                                         pitch_span_deg=pitch_span, allowed_span_deg=1.)
                            state.update(stand_cycle=report.get('stand_cycle', 0),
                                         previous_motion_stop=report.get('previous_motion_stop'),
                                         reposition_seen=report.get('reposition_seen', False))
                            output.telemetry = state
                            phase = 'WAIT_REPOSITION' if require_reposition and not report['reposition_seen'] else 'WAIT_UPRIGHT'
                            output(phase + ': ' + json.dumps(state))

                        def observe_stopping(rows):
                            output.telemetry = dict(stand_cycle=report.get('stand_cycle', 0),
                                previous_motion_stop=report.get('reason'),
                                motor_modes=[rows[m]['mode'] for m in (0, 1)],
                                max_wheel_speed_rad_s=max(abs(rows[m]['speed_rad_s']) for m in (0, 1)))
                            output('WAIT_STOPPING: 双轮已禁能；请扶稳车身，等待轮子停稳。')

                        output.telemetry = dict(stand_cycle=report.get('stand_cycle', 0),
                                                previous_motion_stop=report.get('previous_motion_stop'))
                        exchanges = {m:exchange_for(port, m, report['per_id'][m], plan=PLAN) for m in (0, 1)}
                        # A verified mode-0 stop may acquire the firmware idle
                        # timeout while passive observation/evidence is saved.
                        # Permit only the initial disabled handshake to ack it;
                        # wait/arm/active timeout guards remain unchanged.
                        controller.observe_pair = observe
                        try:
                            run(exchanges, imu, calibration, report, initial_timeout_ack_allowed(report), plan=PLAN,
                                controller=controller, indicator=indicator, display=output,
                                travel_factory=lambda rows, signs, plan:RemoteTravel(rows, signs, plan, controller),
                                continuous=True, waiting_observer=observe_wait,
                                require_reposition=require_reposition,
                                reposition_preconfirmed=report.get('reposition_preconfirmed', False),
                                stopping_observer=observe_stopping)
                        finally:
                            # GC is deferred throughout the supervisor. Delete
                            # the instance override to break controller ->
                            # closure -> controller/report on every exit path.
                            del controller.observe_pair
                        report['serial_write'] = writer.audit()
                    def save_motion_stop(completed):
                        output.telemetry = dict(stand_cycle=completed.get('stand_cycle', 0),
                                                previous_motion_stop=completed['reason'])
                        output('WAIT_RECOVERY: 双轮已停稳，正在准备重新进入扶正等待。')
                        return archive_motion_stop(state, completed)
                    report = run_stand_cycles(report, attempt, save_motion_stop, PLAN, calibration)
                output('STOPPED: 平衡已退出，请扶住车身；具体原因见 last-result.json。')
        except (Exception, KeyboardInterrupt) as exc:
            report.update(status='FAIL', reason=str(exc) or type(exc).__name__)
        finally:
            report['serial_write'] = writer.audit()
            clean = finish_session(state, report)
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
            sys.setswitchinterval(previous_interval)
            from support import atomic_json
            result = {k:report.get(k) for k in ('reason', 'elapsed_s', 'control_cycles', 'final_disabled_verified')}
            result.update(state='STOPPED' if clean else 'FAULT_LATCHED', monotonic=time.monotonic())
            atomic_json(runtime / 'status.json', result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if clean else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--check', action='store_true', help='verify files and configuration without opening devices')
    args = parser.parse_args(argv)
    if not args.run and not args.check:
        print('NOT_STARTED: no hardware access. --check validates; --run starts the explicit boot policy.')
        return 0
    if not args.config:
        parser.error('--config is required')
    config, calibration = load_config(args.config)
    sys.path.insert(0, config['source'])
    from attitude import validate_calibration
    validate_calibration(calibration)
    if args.check:
        print('PASS: base source, runtime source and local calibration hashes verified; hardware not opened.')
        return 0
    if sys.platform != 'linux':
        parser.error('Linux device host required')
    return execute(config, calibration)


if __name__ == '__main__':
    raise SystemExit(main())
