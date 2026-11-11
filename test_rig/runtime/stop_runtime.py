# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep a verified disabled rig disabled while operator-induced motion settles."""
from collections import deque
from air_trial import health, locked_query, stop_both
from attitude import Fault
from fall_recovery import motion_stop_candidate


def stop_for_runtime(exchanges, report, plan, now, sleep, *, observer=None, status=None):
    latest = {}; healthy_disabled_counts = {0:0, 1:0}
    def retain_fault(mid, phase, stage, exc):
        # Stop confirmation may eventually succeed after a bad reply. Keep
        # fault admission separate from that physical disable/stillness fact.
        finding = dict(id=mid, phase=phase, stage=stage, t=now(),
                       error=str(exc) or type(exc).__name__)
        report['stop_fault_count'] = report.get('stop_fault_count', 0) + 1
        report.setdefault('first_stop_fault', finding)
        report.setdefault('stop_faults', deque(maxlen=32)).append(finding)
        healthy_disabled_counts[mid] = 0
    checked = {}
    for mid in (0, 1):
        def exchange(packet, phase, mid=mid):
            try:
                if packet[2] & 0x70:
                    raise Fault('enable_packet_forbidden_during_stop')
                row = exchanges[mid](packet, phase)
            except (Exception, KeyboardInterrupt) as exc:
                retain_fault(mid, phase, 'exchange', exc)
                raise
            latest[mid] = row
            try:
                health(row, 0, plan=plan)
            except Exception as exc:
                retain_fault(mid, phase, 'health', exc)
            else:
                healthy_disabled_counts[mid] += 1
            return row
        checked[mid] = exchange
    stop_both(checked, report, now, sleep, observer=observer)
    if report.get('final_disabled_verified'):
        return
    errors = report.get('stop_errors', {})
    if (not motion_stop_candidate(report, plan) or report.get('stop_fault_count')
            or not errors or any(v != 'not_stopped' for v in errors.values())
            or any(n < 3 for n in healthy_disabled_counts.values())
            or report.get('stop_transition_findings') or report.get('stop_observer_findings')
            or report.get('stop_observer_setup_error')
            or report.get('stop_imu_observation', {}).get('errors')):
        return
    # The finite-trial stop checker conflates mode-0 acknowledgement and wheel
    # stillness. Preserve its result, then wait in mode 0 instead of rearming.
    report['initial_stop_confirmation'] = dict(
        final_disabled_verified=False, stop_errors=dict(errors),
        final_rows=dict(report.get('final_rows', {})))
    report['disabled_mode_confirmed_while_moving'] = True
    report['physical_power_cut_required'] = False
    report.pop('stop_errors', None)
    begin = now(); last_status = -float('inf'); stationary_pairs = 0
    try:
        while True:
            if status is not None and now() - last_status >= .5:
                status(latest); last_status = now()
            sleep(.02)
            for mid in (0, 1):
                row = checked[mid](locked_query(mid), 'disabled_settling')
                health(row, 0, plan=plan)
            if observer is not None:
                observer('disabled_settling')
                if report.get('stop_imu_observation', {}).get('errors'):
                    raise Fault('imu_error_during_disabled_settling')
            stationary_pairs = stationary_pairs + 1 if all(
                abs(latest[m]['speed_rad_s']) <= .04 for m in (0, 1)) else 0
            report['disabled_settling_s'] = now() - begin
            if stationary_pairs >= 3:
                report.update(final_disabled_verified=True, final_rows=dict(latest),
                              stop_confirmation_complete_monotonic=now())
                return
    except (Exception, KeyboardInterrupt) as exc:
        report['motion_stop_before_settling_fault'] = report.get('reason')
        report['reason'] = str(exc) or type(exc).__name__
        report['disabled_settling_fault'] = report['reason']
        stop_both(checked, report, now, sleep, observer=observer)
