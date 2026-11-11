# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator repositioning after a verified motion stop, never fault retry."""
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import uuid
import math
from air_trial import health
from attitude import PitchEstimator, Fault
from support import atomic_json

MOTION_STOPS = frozenset(('body_tilt_stop', 'body_rotation_rate_stop', 'wheel_speed_stop'))


class RepositionGate:
    """Observe a fresh tilted pose while disabled before accepting upright dwell."""
    def __init__(self, pitch_limit=10., roll_limit=5.):
        self.pitch_limit, self.roll_limit = pitch_limit, roll_limit
        self.since = None
        self.seen = False

    def interrupt(self):
        self.since = None

    def update(self, attitude):
        tilted = abs(attitude['pitch_deg']) > self.pitch_limit or abs(attitude['roll_deg']) > self.roll_limit
        self.since = (self.since if self.since is not None else attitude['t']) if tilted else None
        if self.since is not None and attitude['t'] - self.since >= .25:
            self.seen = True
        return self.seen


def motion_stop_candidate(report, plan):
    if not report.get('control_cycles', 0):
        return False
    if report.get('reason') in MOTION_STOPS:
        return True
    # A transient torque trip during an observed tip is still an immediate
    # stop. A stationary overload or sustained torque fault stays latched.
    if report.get('reason') != 'estimated_torque_stop' or not report.get('samples'):
        return False
    sample = report['samples'][-1]
    a = sample.get('attitude', {})
    try:
        pitch, roll, accel = (a[k] for k in ('pitch_deg', 'roll_deg', 'accel_norm_g'))
        if not all(math.isfinite(v) for v in (pitch, roll, accel)) or not .85 <= accel <= 1.15:
            return False
        if abs(pitch) <= plan['arm_pitch_limit_deg'] and abs(roll) <= plan['arm_roll_limit_deg']:
            return False
        feedback = [v['feedback'] for v in sample['wheels'].values()]
        limit = plan['torque_feedback_hard_nm'] if plan.get('active_torque_feedback_guard') else plan['estimated_torque_limit_nm']
        if not feedback or not all(math.isfinite(row['torque_estimate_nm']) for row in feedback):
            return False
        if not any(abs(row['torque_estimate_nm']) > limit for row in feedback):
            return False
        return all(
            row['mode'] == 1 and not row['errors_raw'] and not row['warning_raw']
            and not row['timeout_active'] for row in feedback)
    except (KeyError, TypeError, ValueError):
        return False


def recoverable_motion_stop(report, plan):
    if (not motion_stop_candidate(report, plan)
            or report.get('final_disabled_verified') is not True
            or not report.get('control_cycles', 0)
            or report.get('physical_power_cut_required')
            or report.get('stop_fault_count') or report.get('stop_faults')
            or any(report.get(k) for k in ('stop_transition_findings', 'stop_errors',
                                           'stop_observer_findings', 'stop_observer_setup_error'))
            or report.get('stop_imu_observation', {}).get('status') == 'FAIL'):
        return False
    rows = report.get('final_rows', {})
    try:
        for mid in (0, 1):
            row = rows[mid] if mid in rows else rows[str(mid)]
            health(row, 0, plan=plan)  # Do not ignore timeout, temperature or error bits.
            if abs(row['speed_rad_s']) > .04:
                return False
    except (RuntimeError, KeyError, TypeError, ValueError):
        return False
    return True


def disabled_reposition_seen(report, calibration, plan):
    """Use only healthy IMU evidence recorded after both wheels were stopped.

    This credits a car already seen lying down during the existing passive
    stop observation, so a prompt pickup need not repeat a tipping gesture.
    Every subsequent arm still needs a new full upright/neutral dwell.
    """
    if calibration is None or report.get('stop_imu_observation', {}).get('status') != 'PASS':
        return False
    confirmed = report.get('stop_confirmation_complete_monotonic')
    if confirmed is None:
        return False
    gate = RepositionGate(plan['arm_pitch_limit_deg'], plan['arm_roll_limit_deg'])
    estimator = PitchEstimator(calibration, fuse_roll=plan.get('fuse_roll', False))
    for entry in report['stop_imu_observation']['samples']:
        raw = entry['imu']
        if raw['t_read_complete'] < confirmed:
            continue
        try:
            attitude = estimator.update(raw)
        except Fault:
            gate.interrupt()
            estimator = PitchEstimator(calibration, fuse_roll=plan.get('fuse_roll', False))
            continue
        if .85 <= attitude['accel_norm_g'] <= 1.15:
            if gate.update(attitude):return True
        else:
            gate.interrupt()
    return False


def next_cycle_report(previous, archive):
    # Reuse only device audit dictionaries, not PID/input/reference/pose state.
    keep = ('runtime_version', 'continuous', 'config', 'startup', 'evidence_scope',
            'imu', 'gc', 'remote', 'cam_indicator')
    report = {k:previous[k] for k in keep if k in previous}
    report.update(utc=datetime.now(timezone.utc).isoformat(), status='FAIL',
                  stand_cycle=previous.get('stand_cycle', 0) + 1,
                  previous_motion_stop=previous['reason'], previous_stop_archive=archive,
                  disabled_idle_timeout_ack_authorized=True,
                  timeout_ack_scope='verified_disabled_motion_stop_handoff_only',
                  reposition_preconfirmed=previous.get('reposition_seen_after_stop', False),
                  final_disabled_verified=False,
                  per_id={m:dict(transactions=deque(maxlen=1000)) for m in (0, 1)})
    return report


def initial_timeout_ack_allowed(report):
    if report.get('stand_cycle', 0) == 0:
        return True  # Explicitly installed cold-start policy.
    return (report.get('disabled_idle_timeout_ack_authorized') is True
            and report.get('previous_motion_stop') in MOTION_STOPS | {'estimated_torque_stop'}
            and bool(report.get('previous_stop_archive')))


def archive_motion_stop(directory, report):
    directory = Path(directory)
    folder = directory / 'motion-stops'
    folder.mkdir(exist_ok=True)
    archive = folder / ('stop-' + str(uuid.uuid4()) + '.json')
    atomic_json(archive, report, durable=True)
    atomic_json(directory / 'last-result.json', report, durable=True)
    return str(archive.relative_to(directory))


def run_stand_cycles(report, attempt, save_stop, plan, calibration=None):
    """Same process/lock; every subsequent attempt requires physical repositioning."""
    report.setdefault('stand_cycle', 0)
    while True:
        try:
            attempt(report, require_reposition=report['stand_cycle'] > 0)
            if not recoverable_motion_stop(report, plan):
                return report
            report['reposition_seen_after_stop'] = disabled_reposition_seen(report, calibration, plan)
            archive = save_stop(report)  # A persistence failure must not rearm.
            report = next_cycle_report(report, archive)
        except (Exception, KeyboardInterrupt) as exc:
            report.update(status='FAIL', reason=str(exc) or type(exc).__name__)
            return report
