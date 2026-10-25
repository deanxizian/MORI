#!/usr/bin/env python3
"""Ten-second suspended attitude-compensation check, NOT ground balancing.

Default invocation does no I/O. One local start authorizes one finite run.
No automatic restart, fault clear during motion, or background boot service.
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

from preflight import RawIMU, CycleGC, HERE, PORT
from protocol import RATIO, crc32_words, locked_query, valid_id, FeedbackStream
from wheel_check import stop_both, stopped
from attitude import AIR_PLAN, Fault, PitchEstimator, air_command, finite, validate_calibration
from stop_observer import StopIMURecorder


def torque_packet(mid,value,plan=AIR_PLAN):
    valid_id(mid); finite(value)
    if abs(value)>plan['feedforward_torque_limit_nm']:
        raise Fault('torque_command_outside_trial_plan')
    # Truncate towards zero so quantization cannot exceed the stated cap.
    raw=math.trunc(value/RATIO*256000)
    native_kd=math.floor(plan['native_wheel_damping_nm_per_rad_s']/RATIO**2*128000000)
    body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',raw,0,0,0,native_kd)
    return body+struct.pack('<I',crc32_words(body))


def velocity_packet(mid,speed,plan):
    """Native speed target with zero torque FF and zero position stiffness."""
    valid_id(mid);finite(speed)
    if not plan.get('native_velocity_control') or abs(speed)>plan['velocity_target_limit_rad_s']:
        raise Fault('velocity_command_outside_trial_plan')
    kd=math.floor(plan['native_wheel_damping_nm_per_rad_s']/RATIO**2*128000000)
    raw=math.trunc(speed*RATIO*2.56/math.tau)
    body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',0,raw,0,0,kd)
    return body+struct.pack('<I',crc32_words(body))


def health(row,mode,allow_timeout=False,plan=AIR_PLAN):
    finite(row['speed_rad_s'],row['torque_estimate_nm'],row['voltage_v'],row['temperature_c'],row['position_rad'])
    if row['mode']!=mode or row['errors_raw'] or row['warning_raw']:
        raise Fault('servo_mode_error_or_warning')
    if row['timeout_active'] and not allow_timeout:
        raise Fault('servo_timeout_no_automatic_rearm')
    if not -10<=row['temperature_c']<plan['temperature_limit_c']:
        raise Fault('servo_temperature_stop')
    if not 7<=row['voltage_v']<=12.5:
        raise Fault('servo_voltage_stop')
    if abs(row['speed_rad_s'])>plan['wheel_speed_limit_rad_s']:
        raise Fault('wheel_speed_stop')
    if abs(row['torque_estimate_nm'])>plan['estimated_torque_limit_nm']:
        raise Fault('estimated_torque_stop')


def exchange_for(port,mid,report,now=time.monotonic,plan=AIR_PLAN):
    def exchange(packet,phase):
        port.reset_input_buffer()
        start=now()
        item=dict(monotonic=start,tx_hex=packet.hex(),phase=phase)
        report['transactions'].append(item)
        try:
            item['bytes_written']=port.write(packet)
        except Exception as exc:
            failed=now()
            item.update(write_failed_monotonic=failed,
                        write_attempt_ms=(failed-start)*1000,
                        write_error_type=type(exc).__name__,write_error=str(exc))
            # A timeout may follow a partial/complete kernel write. Preserve
            # that uncertainty and propagate the original fault; never retry.
            raise
        completed=now()
        item.update(write_completed_monotonic=completed,
                    write_attempt_ms=(completed-start)*1000)
        if item['bytes_written']!=len(packet):
            raise Fault('incomplete_serial_write')
        stream=FeedbackStream(mid)
        deadline=start+plan['feedback_deadline_s']
        while now()<deadline:
            rows=stream.feed(port.read(min(256,max(1,port.in_waiting))))
            if rows:
                received=now()
                rows[0]['feedback_received_monotonic']=received
                item.update(feedback=rows[0],response_ms=(received-start)*1000)
                if stream.bad_frames or stream.discarded_bytes or len(rows)!=1:
                    raise Fault('noisy_or_ambiguous_bus')
                if now()>deadline:
                    raise Fault('late_servo_feedback')
                return rows[0]
        raise Fault('servo_feedback_deadline_8ms')
    return exchange


def control_rate_hz(plan):
    rate=plan.get('imu_odr_hz',100)
    if type(rate) is not int or rate not in (100,200):
        raise Fault('unsupported_control_imu_odr')
    return rate


def imu_configuration(plan):
    rate=control_rate_hz(plan)
    options=dict(bandwidth_divisor=plan.get('imu_bandwidth_divisor',2))
    if rate!=100:options['odr_hz']=rate
    return options


def run(exchanges,imu,cal,report,ack,now=time.monotonic,sleep=time.sleep,display=print,
        plan=AIR_PLAN,controller=air_command,travel_factory=None,indicator=None):
    from jog_once import manual_timeout_clear_packet
    nominal_hz=control_rate_hz(plan)
    report.update(status='FAIL',requested_control_hz=nominal_hz,plan=plan.copy(),samples=[],waiting_samples=[],timeout_cleared_ids=[],
                  final_disabled_verified=False,balanced_operation='NOT_TESTED')
    estimator=PitchEstimator(cal,fuse_roll=plan.get('fuse_roll',False))
    signs={int(k):v for k,v in cal['wheel_signs'].items()}
    current={}
    neutral_pitch=0.
    active_begin=None
    ticks=0
    observer=None
    duration=plan.get('post_stop_observation_s',0.)
    if duration:
        try:
            observer=StopIMURecorder(imu,report,duration,now,sleep)
        except Exception as exc:
            report['stop_observer_setup_error']=str(exc)
    def control_attitude(attitude):
        result=dict(attitude,pitch_error_deg=attitude['pitch_deg']-neutral_pitch)
        if plan.get('include_wheel_position_feedback',False):
            result['wheel_position_forward_rad']={m:signs[m]*current[m]['position_rad'] for m in (0,1)}
            if plan.get('use_wheel_feedback_timestamps',False):
                if any('feedback_received_monotonic' not in current[m] for m in (0,1)):
                    raise Fault('wheel_feedback_timestamp_required')
                result['wheel_feedback_received_monotonic']={m:current[m]['feedback_received_monotonic'] for m in (0,1)}
        return result
    def check(row,mode,allow_timeout=False):
        health(row,mode,allow_timeout,plan)
    def external_stop_check():
        # Optional local DISARM input. No parameter I/O in this loop.
        if hasattr(controller,'check_external_stop'):controller.check_external_stop()
    def disabled(phase):
        for mid in (0,1):
            row=exchanges[mid](locked_query(mid),phase)
            check(row,0)
            # With tyres on the floor, manually tilting the body also rotates
            # the encoder relative to the chassis. Still send only mode 0;
            # require a stationary pose separately before enabling torque.
            waiting_by_hand=(plan.get('handheld_wait',False) and phase=='wait_upright_disabled')
            if not waiting_by_hand and abs(row['speed_rad_s'])>plan.get('manual_prearm_motion_rad_s',.04):
                raise Fault('excessive_disabled_wheel_motion')
            current[mid]=row
    def snapshot(phase):
        nonlocal estimator
        raw=None
        try:
            raw=imu.sample()
            dynamic=(plan.get('rise_dynamic_imu',False) and phase=='active_control'
                     and getattr(controller,'phase',None) in plan.get('dynamic_imu_phases',('READY','PRE_ROLL','RISING')))
            if plan.get('active_imu_acceleration_transients',False) and phase=='active_control':
                # Reuse the estimator's bounded dynamic window only for a
                # disturbed acceleration frame. Normal frames must resume
                # gravity correction; do not run gyro-only for the full trial.
                dynamic=dynamic or not .5<math.hypot(*raw['accel_g'])<1.5
            attitude=estimator.update(raw,dynamic=dynamic,
                allow_rotating_low_g=plan.get('allow_rotating_low_g',False),
                rotating_low_g_history_s=(plan.get('rotating_low_g_history_s',0.)
                    if getattr(controller,'phase',None)=='RISING' else 0.))
            if now()-attitude['t']>plan['imu_age_limit_s']:
                raise Fault('stale_imu')
            return raw,attitude
        except Exception as exc:
            if (plan.get('handheld_wait',False) and phase=='wait_pose' and
                    isinstance(exc,Fault) and str(exc)=='acceleration_outside_test_window'):
                # Valid finite IMU data while the operator repositions a fully
                # disabled car is NOT a motor fault/re-arm. Discard this pose,
                # restart the estimator, and require a new ready dwell. Sensor
                # errors/stale data and every armed-phase guard still fail.
                if now()-raw['t_read_complete']>plan['imu_age_limit_s']:
                    raise Fault('stale_imu')
                report['waiting_motion_frames']=report.get('waiting_motion_frames',0)+1
                report['last_waiting_motion_sample']=raw
                estimator=PitchEstimator(cal,fuse_roll=plan.get('fuse_roll',False))
                return raw,None
            # Save the rejected raw frame before the outer finally stops both
            # wheels. An estimator rejection used to discard the only sample
            # explaining the fault. This does not relax any sensor guard.
            report['rejected_imu_sample']=dict(
                phase=phase,imu=raw,reason=str(exc) or type(exc).__name__,
                elapsed_s=None if active_begin is None else now()-active_begin,
                controller_phase=getattr(controller,'phase',None))
            raise
    def verify_arm(raw,attitude,phase):
        a=control_attitude(attitude)
        speeds={m:signs[m]*current[m]['speed_rad_s'] for m in (0,1)}
        try:
            getattr(controller,'validate_arm',controller)(a,speeds,plan)
        except Exception as exc:
            report['rejected_arm_sample']=dict(
                phase=phase,imu=raw,attitude=a,forward_wheel_speed_rad_s=speeds,
                reason=str(exc) or type(exc).__name__)
            raise
    def wait_observation(phase,attitude):
        entries=report['waiting_samples']
        if not entries or entries[-1]['phase']!=phase or attitude['t']-entries[-1]['attitude']['t']>=.1:
            entries.append(dict(phase=phase,attitude=attitude.copy(),
                                wheel_speed_rad_s={m:current[m]['speed_rad_s'] for m in (0,1)}))
    try:
        external_stop_check()
        if plan.get('require_cam_indicator') and indicator is None:
            raise Fault('cam_indicator_required_before_enable')
        active_torque_guard=None
        if plan.get('active_torque_feedback_guard',False):
            from torque_feedback_guard import TorqueFeedbackGuard
            active_torque_guard=TorqueFeedbackGuard(plan)
            report['active_torque_feedback_guard']=active_torque_guard.audit
        for mid in (0,1):
            row=exchanges[mid](locked_query(mid),'initial_disabled')
            check(row,0,True)
            if not plan.get('handheld_wait',False):stopped(row)
            if row['timeout_active']:
                if not ack:
                    raise Fault('initial_timeout_needs_explicit_ack')
                row=exchanges[mid](manual_timeout_clear_packet(mid),'manual_timeout_clear')
                check(row,0,True)
                if not plan.get('handheld_wait',False):stopped(row)
                sleep(.02)
                check(exchanges[mid](locked_query(mid),'timeout_clear_verify'),0)
                report['timeout_cleared_ids'].append(mid)
        display(plan.get('wait_upright_message','WAIT_UPRIGHT: 两轮保持停止；请扶正并静止半秒。'))
        begin=now(); stable=None; ready_window=[]
        dwell=plan.get('arm_stable_s',.5)
        if not .2<=dwell<=2.:raise Fault('invalid_arm_stable_duration')
        while now()-begin<30:
            external_stop_check()
            if indicator:indicator.check()
            raw,a=snapshot('wait_pose'); disabled('wait_upright_disabled')
            if a is None:
                stable=None;ready_window=[]
                continue
            wait_observation('upright',a)
            okay=(plan.get('arm_pitch_min_deg',0.)<=abs(a['pitch_deg'])<=plan['arm_pitch_limit_deg'] and
                  abs(a['roll_deg'])<=plan['arm_roll_limit_deg'] and
                  abs(a['pitch_rate_dps'])<plan.get('arm_rate_limit_dps',1.5) and
                  all(abs(row['speed_rad_s'])<=plan.get('arm_wheel_speed_limit_rad_s',.04) for row in current.values()))
            if plan.get('handheld_wait',False):
                okay=okay and .85<=a['accel_norm_g']<=1.15
            stable=(stable if stable is not None else now()) if okay else None
            ready_window=([v for v in ready_window if a['t']-v['t']<=dwell]+[a]) if okay else []
            if stable is not None and now()-stable>=dwell:
                if max(v['pitch_deg'] for v in ready_window)-min(v['pitch_deg'] for v in ready_window)<=plan.get('arm_pitch_span_deg',float('inf')):
                    break
        else:
            raise Fault('upright_still_pose_not_seen_within_30s')
        report['start_pose']=a
        report['operator_held_pitch_mean_deg']=sum(v['pitch_deg'] for v in ready_window)/len(ready_window)
        if plan.get('capture_start_reference',False):
            neutral_pitch=report['operator_held_pitch_mean_deg']
            report['run_neutral_scope']='Operator-held pose for this finite trial only; not a measured COM zero. Absolute tilt guards are unchanged.'
        else:
            report['run_neutral_scope']='Fixed zero from supplied attitude calibration. Operator-held starting pose does not redefine the target. This is not a measured COM zero.'
        report['run_neutral_pitch_deg']=neutral_pitch
        if plan.get('start_on_pose',False):
            display(plan.get('pose_ready_message','POSE_READY: 大致直立姿态已记录，即将进入本次有限补偿。'))
        else:
            display(plan.get('wait_tilt_message','WAIT_TILT: 已就绪，两轮仍停止。请慢慢前倾约 5 度；检测到动作后开始 10 秒补偿。'))
            begin=now(); trigger_stable=None
            while now()-begin<30:
                external_stop_check()
                raw,a=snapshot('wait_tilt'); disabled('wait_tilt_disabled')
                wait_observation('tilt',a)
                if (abs(a['roll_deg'])>plan.get('prearm_roll_limit_deg',10) or
                        abs(a['pitch_deg'])>plan.get('prearm_pitch_limit_deg',15) or
                        abs(a['pitch_rate_dps'])>50):
                    raise Fault('excessive_motion_before_arm')
                triggered=abs(a['pitch_deg']-neutral_pitch)>=plan.get('trigger_pitch_deg',2)
                if plan.get('trigger_still_s',0):
                    triggered=(triggered and abs(a['pitch_rate_dps'])<1.5 and
                               all(abs(row['speed_rad_s'])<=.04 for row in current.values()))
                trigger_stable=(trigger_stable if trigger_stable is not None else now()) if triggered else None
                if trigger_stable is not None and now()-trigger_stable>=plan.get('trigger_still_s',0):
                    break
            else:
                raise Fault('no_tilt_during_30s_wait')
        report['trigger_pose']=a
        if plan.get('prearm_countdown_s',0):
            display('PREARM_COUNTDOWN: 躺姿已确认，倒计时期间保持静止；电机仍为 mode 0。')
            begin=now()
            while now()-begin<plan['prearm_countdown_s']:
                external_stop_check()
                if plan.get('use_wheel_feedback_timestamps',False):
                    # Encoder reception must precede the IMU attitude used to
                    # validate their age; an old IMU paired with a newer query
                    # would correctly trip the future-feedback guard.
                    disabled('prearm_countdown_disabled');raw,a=snapshot('prearm_countdown')
                else:
                    raw,a=snapshot('prearm_countdown');disabled('prearm_countdown_disabled')
                verify_arm(raw,a,'prearm_countdown')
                wait_observation('countdown',a)
        # Enter with zero feedforward first. A separately declared native
        # zero-speed damper can hold the ground wheels during confirmation;
        # its automatic damping torque is not a zero-output-torque guarantee.
        arm_plan=dict(plan,native_wheel_damping_nm_per_rad_s=
                      plan.get('arm_native_wheel_damping_nm_per_rad_s',plan['native_wheel_damping_nm_per_rad_s']))
        report['arm_native_wheel_damping_nm_per_rad_s']=arm_plan['native_wheel_damping_nm_per_rad_s']
        origins={m:current[m]['position_rad'] for m in (0,1)}
        external_stop_check()
        if indicator:indicator.check()
        for mid in (0,1):
            row=exchanges[mid](torque_packet(mid,0,arm_plan),'arm_zero_transition')
            if row['mode'] not in (0,1):
                raise Fault('invalid_arm_transition')
            check(row,row['mode'])
        begin=now()
        while now()-begin<.2:
            external_stop_check()
            if indicator:indicator.check()
            raw,a=snapshot('arm_zero_confirm')
            # Reject an unsafe body pose even while sending only zero torque.
            verify_arm(raw,a,'arm_zero_confirm')
            for mid in (0,1):
                row=exchanges[mid](torque_packet(mid,0,arm_plan),'arm_zero_confirm')
                check(row,1)
                if (abs(row['speed_rad_s'])>plan.get('zero_arm_speed_limit_rad_s',.04) or
                        abs(row['position_rad']-origins[mid])>plan.get('zero_arm_displacement_limit_rad',.025)):
                    raise Fault('unexpected_motion_during_zero_torque_arm')
                current[mid]=row
        # Use post-transition origins so mode changes cannot masquerade as
        # travel. Any unexpected actual motion during arming already faults.
        travel=travel_factory(current,signs,plan) if travel_factory else None
        if travel:
            report['travel_origin']=travel.snapshot()
        # A stateful controller may be evaluated for guards during the
        # zero-command arm phase. Discard that un-applied state before active
        # control so its integral cannot build up while motors receive zero.
        if hasattr(controller,'reset'):
            controller.reset()
            report['controller_reset_before_active']=True
        display(plan.get('active_message','AIR_COMPENSATION_ACTIVE: 两轮开始补偿，10 秒后自动停止；请轻微前后倾斜。'))
        begin=previous=now(); active_begin=begin; ticks=0
        while now()-begin<plan['duration_s']:
            external_stop_check()
            if indicator:indicator.check()
            tick=now()
            if tick-previous>plan['loop_gap_s']:
                raise Fault('control_loop_gap')
            previous=tick
            raw,a=snapshot('active_control')
            # Acceleration and angular-rate limits are evaluated before each
            # pair; freshness is rechecked immediately before each write.
            a=control_attitude(a)
            # Retain the exact attitude that rejects a cycle before any motor
            # write. Otherwise a tilt stop only leaves the prior safe frame.
            sample=dict(t=tick,elapsed_s=tick-begin,imu=raw,attitude=a,wheels={})
            report['samples'].append(sample)
            try:
                commands=controller(a,{m:signs[m]*current[m]['speed_rad_s'] for m in (0,1)},plan)
            except Exception as exc:
                sample['control_rejected']=str(exc) or type(exc).__name__
                raise
            motor_plan=controller.motor_plan(plan) if hasattr(controller,'motor_plan') else plan
            health_plan=(active_torque_guard.motor_health_plan(motor_plan)
                         if active_torque_guard else motor_plan)
            for mid in (0,1):
                if now()-a['t']>plan['imu_age_limit_s'] or now()-tick>plan['loop_gap_s']:
                    raise Fault('stale_sample_or_pair_deadline')
                value=commands[mid]*signs[mid]
                targets=motor_plan.get('velocity_targets_forward_rad_s')
                if targets is not None:
                    packet=velocity_packet(mid,targets[mid]*signs[mid],motor_plan)
                elif hasattr(controller,'allocated_torque_packet'):
                    # Opt-in allocator retains exact protocol integer values;
                    # avoid decoding and truncating its FF value a second time.
                    packet=controller.allocated_torque_packet(mid,signs[mid],commands[mid],motor_plan)
                else:
                    packet=torque_packet(mid,value,motor_plan)
                row=exchanges[mid](packet,plan.get('control_phase','air_pd'))
                sample['wheels'][mid]=dict(command_forward_nm=commands[mid],command_protocol_nm=value,feedback=row)
                if targets is not None:
                    sample['wheels'][mid]['command_speed_forward_rad_s']=targets[mid]
                health(row,1,plan=health_plan)
                if active_torque_guard:
                    active_torque_guard.observe(mid,row['torque_estimate_nm'],now())
                current[mid]=row
                if travel:
                    try:
                        travel.update(mid,row)
                    finally:
                        sample['rolling_equivalent']=travel.snapshot()
            # Only a successfully issued/checked pair starts the red cue.
            # tick() does no serial I/O and never waits for the display.
            if indicator:indicator.tick()
            # Opt-in bounded in-memory telemetry after a checked motor pair.
            if hasattr(controller,'observe_pair'):controller.observe_pair(sample)
            sample['cycle_work_ms']=(now()-tick)*1000
            if ticks%100==0:
                display(json.dumps(dict(elapsed_s=round(tick-begin,1),pitch_deg=round(a['pitch_deg'],1),
                    wheel_forward_dps=[round(math.degrees(signs[m]*current[m]['speed_rad_s']),1) for m in (0,1)],
                    controller_phase=a.get('self_righting',{}).get('phase'))))
            ticks+=1
        if now()-previous>plan['loop_gap_s'] or ticks<plan['duration_s']*nominal_hz*.9:
            raise Fault('control_timing_incomplete')
        if hasattr(controller,'finish'):
            controller.finish()
        report.update(status='PASS',elapsed_s=now()-begin,control_cycles=ticks)
    except (Exception,KeyboardInterrupt) as exc:
        report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        if active_begin is not None:
            report.update(elapsed_s=now()-active_begin,control_cycles=ticks)
    finally:
        if indicator:indicator.deactivate()
        stop_both(exchanges,report,now,sleep,observer=observer.poll if observer else None)
        if observer is not None:
            try:
                observer.finish()
            except (Exception,KeyboardInterrupt) as exc:
                observer.data.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        if hasattr(controller,'summary'):
            report['controller_summary']=controller.summary()


def display_indicator(report,plan):
    """Keep red/release cues exclusive to balance, with unchanged ACK guards."""
    held=plan.get('operator_held_diagnostic',False)
    if type(held) is not bool:raise Fault('invalid_operator_held_diagnostic_flag')
    from cam_indicator import CamIndicator
    return CamIndicator(report,active_red=not held)


def main(argv=None,*,plan=AIR_PLAN,start_flag='--run-air-trial',controller=air_command,
         travel_factory=None,description=__doc__):
    p=argparse.ArgumentParser(description=description)
    p.add_argument(start_flag,dest='run_trial',action='store_true')
    p.add_argument('--operator-ready',action='store_true')
    p.add_argument('--ack-query-timeout',action='store_true')
    p.add_argument('--port');p.add_argument('--output',type=Path)
    p.add_argument('--calibration',type=Path)
    args=p.parse_args(argv)
    if not args.run_trial:
        print(json.dumps(dict(status='NOT_TESTED',hardware_opened=False,plan=plan),indent=2))
        return 0
    if plan.get('motion_hold_reason'):
        p.error('motion_trial_on_hold: '+plan['motion_hold_reason'])
    if not args.operator_ready or args.port!=PORT or not args.output or not args.calibration or sys.platform!='linux':
        p.error('operator readiness, exact port, calibration, new output and Pi required')
    import bench
    raw_cal=args.calibration.read_bytes();cal=json.loads(raw_cal);validate_calibration(cal)
    source=json.loads((HERE/'source_manifest.json').read_text())
    for name,h in source['sha256'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=h:
            raise Fault('source_manifest_mismatch_'+name)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='FAIL',imu={},gc={},
                source_manifest=source,calibration=cal,calibration_sha256=hashlib.sha256(raw_cal).hexdigest(),
                per_id={m:dict(transactions=[]) for m in (0,1)})
    interrupted=False
    def stop(sig,_):
        nonlocal interrupted
        if not interrupted:
            interrupted=True
            raise KeyboardInterrupt('signal_'+str(sig))
    handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
    report_saved=False
    with args.output.open('x') as output:
        try:
            with ExitStack() as stack:
                indicator=None
                if plan.get('require_cam_indicator'):
                    indicator=stack.enter_context(display_indicator(report.setdefault('cam_indicator',{}),plan))
                stack.enter_context(CycleGC(report['gc'],'defer'))
                imu=stack.enter_context(RawIMU(report['imu'],**imu_configuration(plan)))
                record=bench.select_port(bench.port_records(),args.port)
                report['selected_port']=record
                port=stack.enter_context(bench.open_port(record))
                port.timeout,port.write_timeout=.001,.008
                exchanges={m:exchange_for(port,m,report['per_id'][m],plan=plan) for m in (0,1)}
                run(exchanges,imu,cal,report,args.ack_query_timeout,display=lambda s:print(s,flush=True),
                    plan=plan,controller=controller,travel_factory=travel_factory,indicator=indicator)
        except (Exception,KeyboardInterrupt) as exc:
            report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        finally:
            # ExitStack and run's finally have already stopped/closed motor
            # I/O. Publish the motion result before slow report persistence,
            # then explicitly distinguish a durable-file receipt from it.
            result={k:report.get(k) for k in ('status','reason','elapsed_s','control_cycles',
                        'final_disabled_verified','physical_power_cut_required')}
            result['kind']='MOTION_RESULT'
            try:
                print(json.dumps(result,ensure_ascii=False),flush=True)
                from durable_report import persist_report
                receipt=persist_report(report,output)
                report_saved=True
                print(json.dumps(receipt,ensure_ascii=False),flush=True)
            except Exception as exc:
                print(json.dumps(dict(kind='REPORT_SAVE_FAILED',status='FAIL',
                    error=str(exc) or type(exc).__name__,motion_result=result),
                    ensure_ascii=False),flush=True)
            finally:
                for sig,handler in handlers.items():
                    signal.signal(sig,handler)
    return 0 if report['status']=='PASS' and report_saved else 2


if __name__=='__main__':
    raise SystemExit(main())
