# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded-memory runner derived from frozen v184 air_trial.run.

Only lifecycle changes: optional indefinite wait/run, 1.5 s plan dwell,
neutral-input and last-moment arming checks, bounded tail evidence.
The original torque, feedback, timing, IMU, temperature and stop guards
remain. Only transient data failures before any enable packet may reset
the disabled waiting dwell; arming and active faults never retry.
"""
from collections import deque
import json
import math
import time
from air_trial import (control_rate_hz, health, torque_packet, velocity_packet,
                       AIR_PLAN, air_command, Fault, PitchEstimator, locked_query,
                       stopped, StopIMURecorder)


def run(exchanges,imu,cal,report,ack,now=time.monotonic,sleep=time.sleep,display=print,
        plan=AIR_PLAN,controller=air_command,travel_factory=None,indicator=None,
        continuous=False, waiting_observer=None, require_reposition=False, reposition_preconfirmed=False, stopping_observer=None):
    from jog_once import manual_timeout_clear_packet
    nominal_hz=control_rate_hz(plan)
    report.update(status='FAIL',requested_control_hz=nominal_hz,plan=plan.copy(),samples=deque(maxlen=400),waiting_samples=deque(maxlen=100),timeout_cleared_ids=[],
                  final_disabled_verified=False,balanced_operation='NOT_TESTED')
    from fall_recovery import RepositionGate
    reposition = RepositionGate(plan['arm_pitch_limit_deg'], plan['arm_roll_limit_deg']) if require_reposition else None
    if reposition:reposition.seen = bool(reposition_preconfirmed)
    report.update(reposition_required=require_reposition, reposition_seen=bool(reposition and reposition.seen))
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
            observer.data['samples']=deque(maxlen=1000)
            observer.data['retained_sample_limit']=1000
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
                previous_sample_t=estimator.previous,
                sample_interval_s=(raw['t_read_complete']-estimator.previous
                    if raw is not None and estimator.previous is not None else None),
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
        display('WAIT_REPOSITION: 双轮已禁能。等待车身倾斜后重新扶正，松键稳住 1.5 秒。'
                if reposition else plan.get('wait_upright_message','WAIT_UPRIGHT: 两轮保持停止；请扶正并静止半秒。'))
        begin=now(); stable=None; ready_window=[]; waiting_failures=0
        report['waiting_recoveries']=deque(maxlen=32)
        report['waiting_recovery_count']=0
        dwell=plan.get('arm_stable_s',.5)
        if not .2<=dwell<=2.:raise Fault('invalid_arm_stable_duration')
        while continuous or now()-begin<30:
            external_stop_check()
            if indicator:indicator.check()
            try:
                raw,a=snapshot('wait_pose'); disabled('wait_upright_disabled')
            except Fault as exc:
                # No enable packet has been sent anywhere above this loop.
                # Discard a late/missing frame only in this disabled phase.
                # A fresh healthy pair and a completely new dwell are needed.
                # Active control and the arming transition never retry faults.
                if str(exc) not in ('servo_feedback_deadline_8ms','late_servo_feedback','stale_imu','imu_sample_gap'):
                    raise
                waiting_failures+=1
                report['waiting_recovery_count']+=1
                report['waiting_recoveries'].append(dict(t=now(),reason=str(exc),consecutive=waiting_failures))
                if waiting_failures>=5:
                    raise Fault('disabled_wait_feedback_unavailable') from exc
                display('WAIT_RECOVERING: 电机禁能；等待新鲜反馈，扶正计时已重置。')
                stable=None;ready_window=[]
                if reposition:reposition.interrupt()
                estimator=PitchEstimator(cal,fuse_roll=plan.get('fuse_roll',False))
                sleep(.02)
                continue
            waiting_failures=0
            if a is None:
                stable=None;ready_window=[]
                if reposition:reposition.interrupt()
                continue
            wait_observation('upright',a)
            okay=(plan.get('arm_pitch_min_deg',0.)<=abs(a['pitch_deg'])<=plan['arm_pitch_limit_deg'] and
                  abs(a['roll_deg'])<=plan['arm_roll_limit_deg'] and
                  abs(a['pitch_rate_dps'])<plan.get('arm_rate_limit_dps',1.5) and
                  all(abs(row['speed_rad_s'])<=plan.get('arm_wheel_speed_limit_rad_s',.04) for row in current.values()))
            if reposition:
                report['reposition_seen']=reposition.update(a)
                okay=okay and report['reposition_seen']
            if plan.get('handheld_wait',False):
                okay=okay and .85<=a['accel_norm_g']<=1.15
            if hasattr(controller, 'ready_to_arm'):
                okay = okay and controller.ready_to_arm(now())
            stable=(stable if stable is not None else now()) if okay else None
            ready_window=([v for v in ready_window if a['t']-v['t']<=dwell]+[a]) if okay else []
            if waiting_observer is not None:
                waiting_observer(a,{m:current[m]['speed_rad_s'] for m in (0,1)},
                                 0. if stable is None else now()-stable,okay,
                                 (max(v['pitch_deg'] for v in ready_window)-min(v['pitch_deg'] for v in ready_window)) if ready_window else None)
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
        # Recheck the pose after the final disabled bus exchanges, before
        # the first enabling packet. Never use an earlier dwell sample here.
        raw,a=snapshot('arm_zero_confirm')
        # Do not advance PID/reference estimators before the zero-arm stage:
        # that would make their first wheel/IMU bracket inconsistent.
        if (abs(a['pitch_deg']) > plan['arm_pitch_limit_deg'] or
                abs(a['roll_deg']) > plan['arm_roll_limit_deg'] or
                abs(a['pitch_rate_dps']) > plan['arm_rate_limit_dps'] or
                not .85 <= a['accel_norm_g'] <= 1.15):
            raise Fault('upright_pose_lost_before_arm')
        if hasattr(controller, 'ready_to_arm') and not controller.ready_to_arm(now()):
            raise Fault('remote_not_neutral_before_arm')
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
        while continuous or now()-begin<plan['duration_s']:
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
            report['elapsed_s']=now()-begin
            report['control_cycles']=ticks
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
        from stop_runtime import stop_for_runtime
        stop_for_runtime(exchanges, report, plan, now, sleep,
                         observer=observer.poll if observer else None,
                         status=stopping_observer)
        if observer is not None:
            try:
                observer.finish()
            except (Exception,KeyboardInterrupt) as exc:
                observer.data.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        if hasattr(controller,'summary'):
            report['controller_summary']=controller.summary()

