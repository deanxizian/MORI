#!/usr/bin/env python3
"""Bounded, sequential suspended-wheel direction check; zero I/O by default.

This is not balancing. No boot service, broadcast, or automatic fault re-arm.
An onsite operator must keep both wheels suspended and be able to cut power.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import struct
import sys
import time

from preflight import CycleGC, PORT, HERE
from protocol import RATIO, crc32_words, locked_query, valid_id

PLAN=dict(duration_per_wheel_s=3.0, ramp_s=.5, command_speed_dps=30.0,
          kd_nm_per_rad_s=.25, kp=0, torque_feedforward_nm=0,
          max_temperature_c=70, max_feedback_torque_nm=.12,
          max_feedback_speed_rad_s=1.0, max_displacement_deg=100,
          voltage_min_v=7.0, voltage_max_v=12.5, loop_gap_s=.05,
          frequency_hz=100, feedback_deadline_s=.015)


def packet(mid,speed):
    valid_id(mid)
    if not math.isfinite(speed) or not 0<=speed<=math.radians(PLAN['command_speed_dps']):
        raise ValueError('outside_fixed_wheel_check_speed')
    body=bytes([0xfe,0xee,mid|0x90,0])
    body+=struct.pack('<hhihh',0,round(speed*RATIO*2.56/math.tau),0,0,
                      round(PLAN['kd_nm_per_rad_s']/RATIO**2*128000000))
    return body+struct.pack('<I',crc32_words(body))


def health(row,mode,allow_timeout=False):
    if row['mode']!=mode or row['errors_raw'] or row['warning_raw']:
        raise RuntimeError('servo_mode_error_or_warning')
    if row['timeout_active'] and not allow_timeout:
        raise RuntimeError('servo_timeout_no_automatic_rearm')
    if not -10<=row['temperature_c']<PLAN['max_temperature_c']:
        raise RuntimeError('servo_temperature_stop')
    if not PLAN['voltage_min_v']<=row['voltage_v']<=PLAN['voltage_max_v']:
        raise RuntimeError('servo_voltage_stop')
    if not math.isfinite(row['speed_rad_s']) or abs(row['speed_rad_s'])>PLAN['max_feedback_speed_rad_s']:
        raise RuntimeError('servo_speed_stop')
    if not math.isfinite(row['torque_estimate_nm']) or abs(row['torque_estimate_nm'])>PLAN['max_feedback_torque_nm']:
        raise RuntimeError('estimated_torque_stop')


def stopped(row):
    if row['mode']!=0 or not math.isfinite(row['speed_rad_s']) or abs(row['speed_rad_s'])>.04:
        raise RuntimeError('not_stopped')


def stop_both(exchanges,report,now=time.monotonic,sleep=time.sleep,*,observer=None):
    # Always attempt both even if one is unreachable. Stop verification is
    # independent of temperature/other health faults and never sends mode 1.
    report['stop_request_monotonic']=now()
    for mid in (0,1):
        try:
            exchanges[mid](locked_query(mid),'stop_transition')
        except (Exception,KeyboardInterrupt) as exc:
            report.setdefault('stop_transition_findings',[]).append(dict(id=mid,error=str(exc)))
    # Observation must never precede either initial lock attempt. A failing
    # observer cannot suppress stop confirmation or send a motor command.
    def observe(phase):
        if observer is not None:
            try:
                observer(phase)
            except (Exception,KeyboardInterrupt) as exc:
                report.setdefault('stop_observer_findings',[]).append(str(exc))
    observe('after_both_lock_attempts')
    counts={0:0,1:0}; last={}; errors={}
    deadline=now()+1
    rounds=0
    while now()<deadline and rounds<50 and not all(n>=3 for n in counts.values()):
        sleep(.02); rounds+=1
        for mid in (0,1):
            try:
                row=exchanges[mid](locked_query(mid),'stop_confirm')
                stopped(row); counts[mid]+=1; last[mid]=row
            except (Exception,KeyboardInterrupt) as exc:
                counts[mid]=0; errors[mid]=str(exc)
        observe('lock_confirmation')
    report['final_disabled_verified']=all(n>=3 for n in counts.values())
    report['final_rows']=last
    if not report['final_disabled_verified']:
        report.update(status='FAIL',physical_power_cut_required=True,stop_errors=errors)
    report['stop_confirmation_complete_monotonic']=now()


def run(exchanges,report,ack,now=time.monotonic,sleep=time.sleep):
    from jog_once import manual_timeout_clear_packet
    report.update(status='FAIL',plan=PLAN.copy(),timeout_cleared_ids=[],phases=[])
    try:
        for mid in (0,1):
            row=exchanges[mid](locked_query(mid),'initial_disabled')
            health(row,0,True); stopped(row)
            if row['timeout_active']:
                if not ack:
                    raise RuntimeError('initial_timeout_requires_operator_ack')
                row=exchanges[mid](manual_timeout_clear_packet(mid),'manual_timeout_clear')
                health(row,0,True); stopped(row)
                sleep(.02)
                health(exchanges[mid](locked_query(mid),'timeout_clear_confirm'),0)
                report['timeout_cleared_ids'].append(mid)
        for mid in (0,1):
            # Each wheel gets its own stopped origin and finite trial. The
            # other wheel receives only mode 0 throughout this phase.
            origins={}
            for peer in (0,1):
                row=exchanges[peer](locked_query(peer),'phase_disabled')
                health(row,0); stopped(row); origins[peer]=row['position_rad']
            row=exchanges[mid](packet(mid,0),'arm_zero_transition')
            if row['mode'] not in (0,1):
                raise RuntimeError('invalid_arm_transition')
            health(row,row['mode'])
            arm_start=now()
            while now()-arm_start<.2:
                sleep(.01)
                for peer in (0,1):
                    row=exchanges[peer](packet(peer,0) if peer==mid else locked_query(peer),'arm_zero_settle')
                    health(row,1 if peer==mid else 0)
                    if abs(row['speed_rad_s'])>.2 or abs(row['position_rad']-origins[peer])>.025:
                        raise RuntimeError('unexpected_arm_motion')
            print(f'WHEEL_{mid}_START: 现在仅 ID{mid} 转动，另一轮保持停止，3 秒后停止。',flush=True)
            begin=previous=now(); ticks=0; phase=dict(id=mid,origin_rad=origins[mid],samples=[])
            report['phases'].append(phase)
            while now()-begin<PLAN['duration_per_wheel_s']:
                tick=now(); elapsed=tick-begin
                if tick-previous>PLAN['loop_gap_s']:
                    raise RuntimeError('control_loop_gap')
                previous=tick
                scale=max(0,min(1,elapsed/PLAN['ramp_s'],(PLAN['duration_per_wheel_s']-elapsed)/PLAN['ramp_s']))
                command=math.radians(PLAN['command_speed_dps'])*scale
                for peer in (0,1):
                    if now()-tick>PLAN['loop_gap_s']:
                        raise RuntimeError('control_pair_deadline')
                    row=exchanges[peer](packet(peer,command) if peer==mid else locked_query(peer),'direction_check')
                    health(row,1 if peer==mid else 0)
                    if abs(math.degrees(row['position_rad']-origins[peer]))>PLAN['max_displacement_deg']:
                        raise RuntimeError('wheel_displacement_stop')
                    if peer!=mid:
                        stopped(row)
                    else:
                        phase['samples'].append(dict(elapsed_s=elapsed,command_dps=math.degrees(command),feedback=row))
                ticks+=1
                sleep(max(0,.01-(now()-tick)))
            if now()-previous>PLAN['loop_gap_s'] or ticks<240:
                raise RuntimeError('control_timing_incomplete')
            stop_both(exchanges,report,now,sleep)
            if not report['final_disabled_verified']:
                raise RuntimeError('stop_not_verified')
            end=report['final_rows'][mid]
            phase.update(elapsed_s=now()-begin,displacement_deg=math.degrees(end['position_rad']-origins[mid]))
            if abs(phase['displacement_deg'])<15:
                raise RuntimeError('wheel_motion_not_demonstrated')
            print(f'WHEEL_{mid}_STOP: 已停止。',flush=True)
            # Maintain disabled traffic during a clear visual separation.
            for _ in range(100):
                for peer in (0,1):
                    row=exchanges[peer](locked_query(peer),'between_wheels_disabled')
                    health(row,0); stopped(row)
                sleep(.01)
        report['status']='PASS'
    except (Exception,KeyboardInterrupt) as exc:
        report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
    finally:
        stop_both(exchanges,report,now,sleep)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-suspended-check',action='store_true')
    p.add_argument('--operator-ready',action='store_true')
    p.add_argument('--ack-query-timeout',action='store_true')
    p.add_argument('--port')
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    if not args.run_suspended_check:
        print(json.dumps(dict(status='NOT_TESTED',hardware_opened=False,plan=PLAN),indent=2))
        return 0
    if not args.operator_ready or args.port!=PORT or not args.output or sys.platform!='linux':
        p.error('operator-ready, exact port, new output and Linux required')
    import bench
    import jog_once
    manifest=json.loads((HERE/'bench_support/manifest.json').read_text())
    for name,h in manifest['sha256'].items():
        if hashlib.sha256((HERE/'bench_support'/name).read_bytes()).hexdigest()!=h:
            raise RuntimeError('pinned_support_source_mismatch')
    jog_once.PLAN['feedback_deadline_s']=PLAN['feedback_deadline_s']
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='FAIL',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                per_id={mid:dict(transactions=[]) for mid in (0,1)},gc={})
    interrupted=False
    def stop(sig,_):
        nonlocal interrupted
        if not interrupted:
            interrupted=True
            raise KeyboardInterrupt('signal_'+str(sig))
    handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
    with args.output.open('x') as output:
        try:
            with ExitStack() as stack:
                stack.enter_context(CycleGC(report['gc'],'defer'))
                record=bench.select_port(bench.port_records(),args.port)
                report['selected_port']=record
                port=stack.enter_context(bench.open_port(record))
                port.timeout,port.write_timeout=.001,.01
                exchanges={mid:jog_once.serial_exchange(port,mid,report['per_id'][mid]) for mid in (0,1)}
                run(exchanges,report,args.ack_query_timeout)
        except (Exception,KeyboardInterrupt) as exc:
            report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        finally:
            json.dump(report,output,indent=2)
            for sig,handler in handlers.items():
                signal.signal(sig,handler)
    print(json.dumps({k:v for k,v in report.items() if k not in ('per_id','phases','gc')},indent=2),flush=True)
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':
    raise SystemExit(main())
