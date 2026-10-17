#!/usr/bin/env python3
"""Finite suspended-wheel breakaway characterization; no I/O by default.

Four planned phases, one wheel at a time: left forward/reverse, then right
forward/reverse. Stop on detected output motion; this is not a torque rating.
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

from preflight import HERE, PORT, CycleGC
from protocol import RATIO, crc32_words, locked_query, valid_id
from wheel_check import stop_both, stopped
from air_trial import exchange_for
from attitude import finite, Fault, validate_calibration

PLAN=dict(max_phase_s=2.,ramp_nm_per_s=.04,max_feedforward_nm=.08,
          native_kd=.25,max_speed_rad_s=.6,max_output_displacement_deg=10.,
          max_temperature_c=70,max_estimated_torque_nm=.12,
          loop_gap_s=.025,frequency_hz=100,
          motion_threshold_output_deg=.5,motion_threshold_speed_rad_s=.05,
          motion_threshold_rotor_deg=.5,zero_settle_s=.4,
          maximum_planned_phases=4)


def packet(mid,torque):
    valid_id(mid);finite(torque)
    if abs(torque)>PLAN['max_feedforward_nm']:
        raise Fault('breakaway_torque_cap')
    raw=math.trunc(torque/RATIO*256000)
    kd=math.floor(PLAN['native_kd']/RATIO**2*128000000)
    body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',raw,0,0,0,kd)
    return body+struct.pack('<I',crc32_words(body))


def health(row,mode,allow_timeout=False):
    finite(row['speed_rad_s'],row['torque_estimate_nm'],row['temperature_c'],row['voltage_v'])
    if row['mode']!=mode or row['errors_raw'] or row['warning_raw']:
        raise Fault('servo_mode_error_or_warning')
    if row['timeout_active'] and not allow_timeout:
        raise Fault('servo_timeout_no_rearm')
    if not -10<=row['temperature_c']<PLAN['max_temperature_c']:
        raise Fault('temperature_stop')
    if not 7<=row['voltage_v']<=12.5:
        raise Fault('voltage_stop')
    if abs(row['speed_rad_s'])>PLAN['max_speed_rad_s']:
        raise Fault('wheel_speed_stop')
    if abs(row['torque_estimate_nm'])>PLAN['max_estimated_torque_nm']:
        raise Fault('estimated_torque_stop')


def output_delta(row,origin):
    return (row['absolute_output_rad']-origin+math.pi)%(2*math.pi)-math.pi


def run(exchanges,cal,report,ack,now=time.monotonic,sleep=time.sleep,display=print):
    from jog_once import manual_timeout_clear_packet
    report.update(status='FAIL',phases=[],timeout_cleared_ids=[],plan=PLAN.copy())
    signs={int(k):v for k,v in cal['wheel_signs'].items()}
    try:
        for mid in (0,1):
            row=exchanges[mid](locked_query(mid),'initial_disabled')
            health(row,0,True);stopped(row)
            if row['timeout_active']:
                if not ack:raise Fault('explicit_initial_timeout_ack_required')
                row=exchanges[mid](manual_timeout_clear_packet(mid),'manual_timeout_clear')
                health(row,0,True);stopped(row);sleep(.02)
                health(exchanges[mid](locked_query(mid),'timeout_clear_confirm'),0)
                report['timeout_cleared_ids'].append(mid)
        for mid,direction in ((0,1),(0,-1),(1,1),(1,-1)):
            origins={};rotor_origins={}
            for peer in (0,1):
                row=exchanges[peer](locked_query(peer),'phase_disabled')
                health(row,0);stopped(row);origins[peer]=row['absolute_output_rad']
            row=exchanges[mid](packet(mid,0),'arm_zero_transition')
            if row['mode'] not in (0,1):raise Fault('arm_transition_mode')
            health(row,row['mode'])
            settled={}
            for _ in range(40):
                sleep(.01)
                for peer in (0,1):
                    row=exchanges[peer](packet(peer,0) if peer==mid else locked_query(peer),'arm_zero_settle')
                    health(row,1 if peer==mid else 0)
                    if abs(row['speed_rad_s'])>.04 or abs(output_delta(row,origins[peer]))>math.radians(3):
                        raise Fault('unexpected_zero_arm_motion')
                    settled[peer]=row
            # Mode 0 -> torque mode can change gear preload and the absolute
            # encoder reading. The ramp starts from the settled mode-1 pose,
            # not the earlier disabled-mode position.
            for peer in (0,1):
                origins[peer]=settled[peer]['absolute_output_rad']
                rotor_origins[peer]=settled[peer]['position_rad']
            phase=dict(id=mid,vehicle_direction=direction,protocol_direction=direction*signs[mid],samples=[],status='NOT_TESTED')
            phase['settled_origins']={peer:dict(output_rad=origins[peer],rotor_equivalent_rad=rotor_origins[peer]) for peer in (0,1)}
            report['phases'].append(phase)
            display(f'BREAKAWAY: ID{mid}, '+('前进' if direction==1 else '后退')+'，缓慢增加力矩，检测到起转就停止。')
            begin=previous=now();detected=0
            while now()-begin<PLAN['max_phase_s']:
                tick=now();elapsed=tick-begin
                if tick-previous>PLAN['loop_gap_s']:raise Fault('loop_gap')
                previous=tick
                torque=min(PLAN['max_feedforward_nm'],elapsed*PLAN['ramp_nm_per_s'])*phase['protocol_direction']
                for peer in (0,1):
                    if now()-tick>PLAN['loop_gap_s']:raise Fault('pair_deadline')
                    row=exchanges[peer](packet(peer,torque) if peer==mid else locked_query(peer),'torque_ramp')
                    health(row,1 if peer==mid else 0)
                    delta=output_delta(row,origins[peer])
                    if abs(math.degrees(delta))>PLAN['max_output_displacement_deg']:
                        raise Fault('output_displacement_stop')
                    if peer!=mid:
                        stopped(row)
                    else:
                        rotor_delta=row['position_rad']-rotor_origins[peer]
                        phase['samples'].append(dict(elapsed_s=elapsed,command_protocol_nm=torque,
                            output_delta_deg=math.degrees(delta),rotor_delta_deg=math.degrees(rotor_delta),feedback=row))
                        forward_speed=row['speed_rad_s']*phase['protocol_direction']
                        directed_delta=delta*phase['protocol_direction']
                        directed_rotor=rotor_delta*phase['protocol_direction']
                        # A small absolute-sensor drift alone is not proof of
                        # reverse motion. Rotor displacement and speed must
                        # also demonstrate a sustained opposite direction.
                        if directed_rotor<math.radians(-1) and forward_speed<-.05:
                            raise Fault('unexpected_rotation_direction')
                        moving=(forward_speed>=PLAN['motion_threshold_speed_rad_s'] and
                                directed_delta>=math.radians(PLAN['motion_threshold_output_deg']) and
                                directed_rotor>=math.radians(PLAN['motion_threshold_rotor_deg']))
                        detected=detected+1 if moving else 0
                if detected>=3:
                    phase.update(status='PASS',motion_seen=True,detected_at_s=elapsed,
                                 feedforward_at_detection_nm=abs(torque))
                    break
                sleep(max(0,.01-(now()-tick)))
            else:
                raise Fault('no_breakaway_within_fixed_cap')
            stop_both(exchanges,report,now,sleep)
            if not report['final_disabled_verified']:raise Fault('stop_not_verified')
            display(json.dumps({k:v for k,v in phase.items() if k!='samples'}))
            for _ in range(50):
                for peer in (0,1):
                    row=exchanges[peer](locked_query(peer),'between_phases_disabled')
                    health(row,0);stopped(row)
                sleep(.01)
        report['status']='PASS'
    except (Exception,KeyboardInterrupt) as exc:
        report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
    finally:
        stop_both(exchanges,report,now,sleep)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-breakaway-test',action='store_true')
    p.add_argument('--operator-ready',action='store_true')
    p.add_argument('--ack-query-timeout',action='store_true')
    p.add_argument('--port');p.add_argument('--calibration',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    if not args.run_breakaway_test:
        print(json.dumps(dict(status='NOT_TESTED',hardware_opened=False,plan=PLAN),indent=2));return 0
    if not args.operator_ready or args.port!=PORT or not args.calibration or not args.output or sys.platform!='linux':
        p.error('operator readiness, exact port, calibration, new output and Pi required')
    import bench
    raw=args.calibration.read_bytes();cal=json.loads(raw);validate_calibration(cal)
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    for name,h in manifest['sha256'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=h:raise Fault('source_manifest_mismatch_'+name)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='FAIL',gc={},
        source_manifest=manifest,calibration_sha256=hashlib.sha256(raw).hexdigest(),
        per_id={m:dict(transactions=[]) for m in (0,1)})
    interrupted=False
    def stop(sig,_):
        nonlocal interrupted
        if not interrupted:
            interrupted=True;raise KeyboardInterrupt('signal_'+str(sig))
    handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
    with args.output.open('x') as output:
        try:
            with ExitStack() as stack:
                stack.enter_context(CycleGC(report['gc'],'defer'))
                record=bench.select_port(bench.port_records(),args.port);report['selected_port']=record
                port=stack.enter_context(bench.open_port(record));port.timeout,port.write_timeout=.001,.008
                exchanges={m:exchange_for(port,m,report['per_id'][m]) for m in (0,1)}
                run(exchanges,cal,report,args.ack_query_timeout,display=lambda s:print(s,flush=True))
        except (Exception,KeyboardInterrupt) as exc:
            report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        finally:
            json.dump(report,output,indent=2)
            for sig,handler in handlers.items():signal.signal(sig,handler)
    print(json.dumps({k:report.get(k) for k in ('status','reason','final_disabled_verified','physical_power_cut_required')},indent=2))
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
