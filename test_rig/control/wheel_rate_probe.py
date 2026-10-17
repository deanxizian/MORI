#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite suspended-wheel rate-loop characterization, never ground balancing.

Compares the checked ArduPilot host wheel-rate PI path with the official
Unitree native velocity term. Four phases, one wheel enabled, each <=2s.
Desired speed ramps to 0.20rad/s and back to zero. Gains are local test
hypotheses, not vendor or identified motor parameters. No position loop,
stacked host/native PI, gain learning or automatic fault restart.

v112 changes only active native velocity Kd from 0.80 to 1.20 against v111_1.
It uses zero FF/position/Kp, quantized speed targets, and bounded native Kd.
The v109 readiness and finite-stop harness remain.
The sampled torque estimate is not an instantaneous hardware torque clamp.
"""
import argparse
from contextlib import ExitStack
from dataclasses import dataclass,replace
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import struct
import sys
import time

from preflight import HERE,PORT,CycleGC
from protocol import RATIO,crc32_words,locked_query,valid_id
from attitude import Fault,finite,validate_calibration
from air_trial import exchange_for
from wheel_check import stop_both,stopped
from breakaway import health,output_delta
from offline_two_deck_review_20261016.motor_stage import RateGains,WheelRateStage,allocate_net_torque


PLAN=dict(name='suspended_native_velocity_probe_v112',maximum_planned_phases=4,
    control_method='native_velocity_p',native_velocity_kd=1.20,native_zero_kd=.40,
    max_phase_s=2.,target_speed_rad_s=.20,target_ramp_s=.4,target_down_start_s=1.2,
    max_feedforward_nm=.08,max_predicted_net_nm=.08,native_kd=.10,
    max_speed_rad_s=.6,max_output_displacement_deg=20.,
    max_rotor_equivalent_displacement_deg=20.,max_temperature_c=70,
    max_estimated_torque_nm=.12,frequency_hz=100,loop_gap_s=.025,
    max_feedback_age_s=.015,zero_settle_s=.4,
    zero_settle_timeout_s=.8,zero_quiet_dwell_s=.2,
    zero_quiet_speed_rad_s=.04,max_zero_settle_speed_rad_s=.20,
    max_zero_settle_output_deg=3.,max_zero_settle_rotor_deg=1.,
    kp_nm_per_rad_s=.05,ki_nm_per_rad=.20,integral_limit_nm=.06)


def desired_rate(elapsed):
    finite(elapsed)
    if elapsed<0:raise Fault('negative_probe_time')
    fraction=min(1.,elapsed/PLAN['target_ramp_s'],
                 max(0.,(PLAN['target_down_start_s']+PLAN['target_ramp_s']-elapsed)/PLAN['target_ramp_s']))
    return PLAN['target_speed_rad_s']*fraction


class RateCommand:
    """Fresh state per phase; actual inputs/outputs use protocol direction."""
    def __init__(self):
        scale=100./PLAN['max_predicted_net_nm']
        self.stage=WheelRateStage(RateGains(
            max_rate_rad_s=PLAN['target_speed_rad_s'],
            kp_pct_per_rad_s=PLAN['kp_nm_per_rad_s']*scale,
            ki_pct_per_rad=PLAN['ki_nm_per_rad']*scale,
            kd_pct_per_rad_s2=0.,ff_pct_per_rad_s=0.,
            integral_limit_pct=PLAN['integral_limit_nm']*scale))
        self.allocated_limited=False

    def update(self,target,actual,dt):
        finite(target,actual,dt)
        if abs(target)>PLAN['target_speed_rad_s']+1e-12:
            raise Fault('wheel_rate_target_cap')
        if abs(actual)>PLAN['max_speed_rad_s']:
            raise Fault('wheel_speed_stop')
        info=self.stage.update(target/PLAN['target_speed_rad_s']*100.,actual,dt,
                              downstream_limited=self.allocated_limited)
        requested=info['bounded_output_normalized']*PLAN['max_predicted_net_nm']
        a=allocate_net_torque(requested,actual,native_kd_nm_per_rad_s=PLAN['native_kd'],
            feedforward_limit_nm=PLAN['max_feedforward_nm'],
            net_budget_nm=PLAN['max_predicted_net_nm'],gear_ratio=RATIO)
        self.allocated_limited=a.limited
        return a,dict(info,requested_net_nm=requested,predicted_net_nm=a.predicted_net_nm,
                      command_ff_nm=a.feedforward_nm,allocation_limited=a.limited)


@dataclass(frozen=True)
class NativeVelocityAllocation:
    feedforward_raw:int
    native_kd_raw:int
    feedforward_nm:float
    predicted_net_nm:float
    velocity_raw:int


class NativeVelocityCommand:
    """Unitree hybrid-control velocity term; no host P/I stacked beneath it.

    Official output-side conversions are pinned in the earlier S288 bench
    vendor/specs/protocol.md. Local Kd and safety envelope are experimental.
    Quantization is applied before evaluating Kd*(target-actual).
    """
    def update(self,target,actual,dt):
        finite(target,actual,dt)
        if abs(target)>PLAN['target_speed_rad_s']+1e-12:
            raise Fault('wheel_rate_target_cap')
        if abs(actual)>PLAN['max_speed_rad_s']:
            raise Fault('wheel_speed_stop')
        if not .001<=dt<=PLAN['loop_gap_s']:
            raise Fault('wheel_rate_loop_gap')
        speed_lsb=math.tau/(RATIO*2.56)
        velocity_raw=math.trunc(target/speed_lsb)
        quantized_target=velocity_raw*speed_lsb
        kd_lsb=RATIO**2/128000000.
        full_kd_raw=math.floor(PLAN['native_velocity_kd']/kd_lsb)
        error=quantized_target-actual
        kd_raw=full_kd_raw
        if error:
            kd_raw=min(kd_raw,math.floor(PLAN['max_predicted_net_nm']/abs(error)/kd_lsb))
        predicted=kd_raw*kd_lsb*error
        allocation=NativeVelocityAllocation(0,kd_raw,0.,predicted,velocity_raw)
        return allocation,dict(controller='native_velocity_p',
            quantized_target_protocol_rad_s=quantized_target,
            effective_native_kd=kd_raw*kd_lsb,
            requested_net_nm=full_kd_raw*kd_lsb*error,
            predicted_net_nm=predicted,command_ff_nm=0.,
            allocation_limited=kd_raw<full_kd_raw,
            host_integral_enabled=False)


def packet(mid,allocation):
    valid_id(mid)
    finite(allocation.feedforward_nm,allocation.predicted_net_nm)
    if (abs(allocation.feedforward_nm)>PLAN['max_feedforward_nm']+1e-12 or
            abs(allocation.predicted_net_nm)>PLAN['max_predicted_net_nm']+1e-12):
        raise Fault('wheel_rate_packet_budget')
    velocity_raw=getattr(allocation,'velocity_raw',0)
    if abs(velocity_raw*math.tau/(RATIO*2.56))>PLAN['target_speed_rad_s']+1e-12:
        raise Fault('wheel_rate_packet_speed_cap')
    body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',
        allocation.feedforward_raw,velocity_raw,0,0,allocation.native_kd_raw)
    return body+struct.pack('<I',crc32_words(body))


def run(exchanges,cal,report,ack,now=time.monotonic,sleep=time.sleep,display=print):
    from jog_once import manual_timeout_clear_packet
    report.update(status='FAIL',plan=PLAN.copy(),phases=[],arming=[],timeout_cleared_ids=[],
                  final_disabled_verified=False,balanced_operation='NOT_APPLICABLE',
                  rate_tracking_qualified='NOT_TESTED')
    signs={int(k):v for k,v in cal['wheel_signs'].items()}
    current={}
    def checked(mid,body,phase,mode,allow_timeout=False):
        row=exchanges[mid](body,phase)
        health(row,mode,allow_timeout)
        finite(row['position_rad'],row['absolute_output_rad'],row['feedback_received_monotonic'])
        if not 0<=now()-row['feedback_received_monotonic']<=PLAN['max_feedback_age_s']:
            raise Fault('wheel_rate_stale_feedback')
        current[mid]=row
        return row
    try:
        method=PLAN.get('control_method','ap_wheel_rate_pi')
        if method=='native_velocity_p':controller_type=NativeVelocityCommand
        elif method=='ap_wheel_rate_pi':controller_type=RateCommand
        else:raise Fault('unknown_wheel_rate_controller')
        report['control_method']=method
        for mid in (0,1):
            row=checked(mid,locked_query(mid),'initial_disabled',0,True);stopped(row)
            if row['timeout_active']:
                if not ack:raise Fault('explicit_initial_timeout_ack_required')
                row=checked(mid,manual_timeout_clear_packet(mid),'manual_timeout_clear',0,True)
                stopped(row);sleep(.02)
                stopped(checked(mid,locked_query(mid),'timeout_clear_confirm',0))
                report['timeout_cleared_ids'].append(mid)
        for mid,direction in ((0,1),(0,-1),(1,1),(1,-1)):
            protocol_direction=direction*signs[mid]
            for peer in (0,1):stopped(checked(peer,locked_query(peer),'phase_disabled',0))
            origins={m:current[m]['absolute_output_rad'] for m in (0,1)}
            arm_rotor_origins={m:current[m]['position_rad'] for m in (0,1)}
            zero,_=controller_type().update(0.,0.,1/PLAN['frequency_hz'])
            if method=='native_velocity_p':
                # Keep the already exercised v110 zero-arm damping. Only
                # active ramp tracking changes in this comparison. At the
                # hard arm-speed bound, this is <= the sampled NET budget.
                zero_kd=min(PLAN['native_zero_kd'],
                            PLAN['max_predicted_net_nm']/PLAN['max_zero_settle_speed_rad_s'])
                zero=replace(zero,native_kd_raw=min(zero.native_kd_raw,
                    math.floor(zero_kd/RATIO**2*128000000)))
            arm=dict(id=mid,vehicle_direction=direction,status='NOT_TESTED',
                     max_speed_rad_s=0.,max_rotor_delta_deg=0.,max_output_delta_deg=0.)
            report['arming'].append(arm)
            arm_begin=now()
            row=exchanges[mid](packet(mid,zero),'arm_zero_transition')
            if row['mode'] not in (0,1):raise Fault('arm_transition_mode')
            health(row,row['mode'])
            quiet_since=None;arm_previous=now()
            while True:
                sleep(.01)
                tick=now()
                if tick-arm_previous>PLAN['loop_gap_s']:raise Fault('zero_arm_loop_gap')
                arm_previous=tick
                if tick-arm_begin>PLAN['zero_settle_timeout_s']:raise Fault('zero_arm_settle_timeout')
                quiet=True
                for peer in (0,1):
                    if now()-tick>PLAN['loop_gap_s']:raise Fault('zero_arm_pair_deadline')
                    row=checked(peer,packet(peer,zero) if peer==mid else locked_query(peer),
                                'arm_zero_settle',1 if peer==mid else 0)
                    rotor=abs(math.degrees(row['position_rad']-arm_rotor_origins[peer]))
                    output=abs(math.degrees(output_delta(row,origins[peer])))
                    speed=abs(row['speed_rad_s'])
                    arm.update(max_speed_rad_s=max(arm['max_speed_rad_s'],speed),
                               max_rotor_delta_deg=max(arm['max_rotor_delta_deg'],rotor),
                               max_output_delta_deg=max(arm['max_output_delta_deg'],output))
                    if rotor>PLAN['max_zero_settle_rotor_deg'] or output>PLAN['max_zero_settle_output_deg']:
                        raise Fault('unexpected_zero_arm_displacement')
                    if peer==mid and speed>PLAN['max_zero_settle_speed_rad_s']:
                        raise Fault('unexpected_zero_arm_motion')
                    if peer!=mid:stopped(row)
                    if speed>PLAN['zero_quiet_speed_rad_s']:quiet=False
                end=now();arm['elapsed_s']=end-arm_begin
                if end-tick>PLAN['loop_gap_s']:raise Fault('zero_arm_pair_deadline')
                if arm['elapsed_s']>PLAN['zero_settle_timeout_s']:raise Fault('zero_arm_settle_timeout')
                if not quiet:quiet_since=None
                elif quiet_since is None:quiet_since=end
                if (arm['elapsed_s']>=PLAN['zero_settle_s'] and quiet_since is not None and
                        end-quiet_since>=PLAN['zero_quiet_dwell_s']):
                    arm.update(status='PASS',quiet_dwell_s=end-quiet_since)
                    break
            origins={m:current[m]['absolute_output_rad'] for m in (0,1)}
            rotor_origins={m:current[m]['position_rad'] for m in (0,1)}
            phase=dict(id=mid,vehicle_direction=direction,protocol_direction=protocol_direction,
                       status='NOT_TESTED',samples=[],motion_seen=False,settled_output_origins=origins,
                       settled_rotor_origins=rotor_origins)
            report['phases'].append(phase)
            controller=controller_type();begin=previous=now();count=0
            display(f'WHEEL_RATE_ACTIVE: ID{mid} '+('前进' if direction==1 else '后退')+'，目标最高0.20rad/s，2秒后停止；另一个轮子保持关闭。')
            while now()-begin<PLAN['max_phase_s']:
                tick=now();elapsed=tick-begin;dt=1/PLAN['frequency_hz'] if count==0 else tick-previous
                if not .001<=dt<=PLAN['loop_gap_s']:raise Fault('wheel_rate_loop_gap')
                previous=tick;count+=1
                for peer in (0,1):
                    if not 0<=tick-current[peer]['feedback_received_monotonic']<=PLAN['max_feedback_age_s']:
                        raise Fault('wheel_rate_stale_feedback')
                target=protocol_direction*desired_rate(elapsed)
                allocation,info=controller.update(target,current[mid]['speed_rad_s'],dt)
                item=dict(elapsed_s=elapsed,dt=dt,target_protocol_rad_s=target,
                          input_protocol_rad_s=current[mid]['speed_rad_s'],control=info,feedback={})
                phase['samples'].append(item)
                for peer in (0,1):
                    if now()-tick>PLAN['loop_gap_s']:raise Fault('wheel_rate_pair_deadline')
                    row=exchanges[peer](packet(peer,allocation) if peer==mid else locked_query(peer),'rate_probe')
                    # Retain even the rejected feedback before fault handling.
                    item['feedback'][peer]=row
                    health(row,1 if peer==mid else 0)
                    finite(row['position_rad'],row['absolute_output_rad'],row['feedback_received_monotonic'])
                    if not 0<=now()-row['feedback_received_monotonic']<=PLAN['max_feedback_age_s']:
                        raise Fault('wheel_rate_stale_feedback')
                    delta=output_delta(row,origins[peer]);rotor=row['position_rad']-rotor_origins[peer]
                    if (abs(math.degrees(delta))>PLAN['max_output_displacement_deg'] or
                            abs(math.degrees(rotor))>PLAN['max_rotor_equivalent_displacement_deg']):
                        raise Fault('wheel_rate_displacement_stop')
                    if peer!=mid:stopped(row)
                    elif rotor*protocol_direction<math.radians(-1) and row['speed_rad_s']*protocol_direction<-.05:
                        raise Fault('unexpected_rotation_direction')
                    elif abs(rotor)>math.radians(.5) and abs(row['speed_rad_s'])>.05:
                        phase['motion_seen']=True
                    current[peer]=row
                sleep(max(0,1/PLAN['frequency_hz']-(now()-tick)))
            if not phase['motion_seen']:raise Fault('no_low_speed_response_within_fixed_window')
            phase.update(status='PASS',elapsed_s=now()-begin,cycles=count,
                         outcome_scope='Finite bounded diagnostic completed; tracking quality requires log analysis')
            stop_both(exchanges,report,now,sleep)
            if not report['final_disabled_verified']:raise Fault('stop_not_verified')
            display(f'WHEEL_RATE_STOPPED: ID{mid} 本方向完成，两轮已停止。')
            for _ in range(50):
                for peer in (0,1):stopped(checked(peer,locked_query(peer),'between_phases_disabled',0))
                sleep(.01)
        report['status']='PASS'
    except (Exception,KeyboardInterrupt) as exc:
        report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
    finally:
        stop_both(exchanges,report,now,sleep)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-wheel-rate-probe',action='store_true')
    p.add_argument('--operator-ready',action='store_true')
    p.add_argument('--ack-query-timeout',action='store_true')
    p.add_argument('--port');p.add_argument('--calibration',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    if not args.run_wheel_rate_probe:
        print(json.dumps(dict(status='NOT_TESTED',hardware_opened=False,plan=PLAN),indent=2));return 0
    if not args.operator_ready or args.port!=PORT or not args.calibration or not args.output or sys.platform!='linux':
        p.error('suspended-wheel readiness, exact port, calibration, new output and Pi required')
    import bench
    raw=args.calibration.read_bytes();cal=json.loads(raw);validate_calibration(cal)
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    for name,h in manifest['sha256'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=h:raise Fault('source_manifest_mismatch_'+name)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='FAIL',gc={},source_manifest=manifest,
        calibration_sha256=hashlib.sha256(raw).hexdigest(),per_id={m:dict(transactions=[]) for m in (0,1)})
    interrupted=False
    def stop(sig,_):
        nonlocal interrupted
        if not interrupted:interrupted=True;raise KeyboardInterrupt('signal_'+str(sig))
    handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
    saved=False
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
            try:
                print(json.dumps(dict(kind='MOTION_RESULT',**{k:report.get(k) for k in
                    ('status','reason','final_disabled_verified','physical_power_cut_required')})),flush=True)
                from durable_report import persist_report
                print(json.dumps(persist_report(report,output)),flush=True);saved=True
            finally:
                for sig,handler in handlers.items():signal.signal(sig,handler)
    return 0 if report['status']=='PASS' and saved else 2


if __name__=='__main__':raise SystemExit(main())
