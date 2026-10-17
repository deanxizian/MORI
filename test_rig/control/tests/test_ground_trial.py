"""Control signs, finite-run orchestration and fault stops, not a plant model."""
from contextlib import redirect_stdout
import copy
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run, torque_packet
from attitude import Fault
from ground_trial import GROUND_PLAN, WheelTravel, ground_command, main
from ground_observe import OBSERVE_PLAN, main as observation_main
from ground_observe_long import LONG_OBSERVE_PLAN, main as long_observation_main
from ground_recovery_trial import RECOVERY_PLAN, main as recovery_main
from ground_early_response import EARLY_PLAN, main as early_main
from ground_hold_trial import HOLD_PLAN, HoldTravel, main as hold_main
from ground_fixed_reference import FIXED_PLAN, main as fixed_main
from ground_reduced_damping import REDUCED_DAMPING_PLAN, main as reduced_damping_main
from ground_travel_window import TRAVEL_WINDOW_PLAN, main as travel_window_main
from protocol import RATIO, crc32_words
from test_attitude_air import CAL, IMU
from test_wheel_check import Bus


class GroundTests(unittest.TestCase):
    def run_case(self,transform=None,imu_kwargs=None,imu_factory=None,plan=GROUND_PLAN,
                 travel_factory=WheelTravel):
        bus=Bus(timeout=True);report={}
        exchanges={m:bus.exchange(m) for m in (0,1)}
        if transform:
            exchanges=transform(exchanges,bus)
        imu=imu_factory(bus) if imu_factory else IMU(bus,**(imu_kwargs or {}))
        run(exchanges,imu,copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda s:None,
            plan=plan,controller=ground_command,travel_factory=travel_factory)
        return bus,report

    def assert_stopped_without_rearm(self,bus,report):
        self.assertEqual(report['status'],'FAIL')
        self.assertTrue(report['final_disabled_verified'])
        first_stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[first_stop:]))
        self.assertEqual({m for m,_,phase in bus.log if phase=='stop_confirm'},{0,1})

    def test_default_zero_io_and_no_air_start_flag(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
            self.assertEqual(observation_main([]),0)
            self.assertEqual(long_observation_main([]),0)
            self.assertEqual(recovery_main([]),0)
            self.assertEqual(early_main([]),0)
            self.assertEqual(hold_main([]),0)
            self.assertEqual(fixed_main([]),0)
            self.assertEqual(reduced_damping_main([]),0)
            self.assertEqual(travel_window_main([]),0)
        with redirect_stdout(io.StringIO()),patch('sys.stderr',io.StringIO()),self.assertRaises(SystemExit):
            main(['--run-air-trial'])

    def test_ground_packet_has_no_position_target_and_bounded_native_damping(self):
        for value in (-.08,0,.08):
            p=torque_packet(0,value,GROUND_PLAN)
            torque,speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            self.assertEqual((speed,pos,kp),(0,0,0))
            self.assertGreater(kd,0)
            self.assertLessEqual(kd/128000000*RATIO**2,.05)
            self.assertLessEqual(abs(torque/256000*RATIO),.08)
            self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))

    def test_zero_feedforward_arm_has_damping_until_active_pd(self):
        bus,report=self.run_case()
        self.assertEqual(report['status'],'PASS')
        arm=[p for _,p,phase in bus.log if phase.startswith('arm_')]
        active=[p for _,p,phase in bus.log if phase=='ground_pd']
        self.assertTrue(arm and active)
        for p in arm:
            torque,speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            self.assertEqual((torque,speed,pos,kp),(0,0,0,0))
            self.assertGreater(kd,0)
            self.assertLessEqual(kd/128000000*RATIO**2,.15)
        self.assertTrue(all(0<struct.unpack_from('<h',p,14)[0]<struct.unpack_from('<h',arm[0],14)[0] for p in active))

    def test_body_pd_sign_derivative_and_saturation(self):
        attitude=dict(pitch_deg=0,pitch_rate_dps=0,roll_deg=0)
        for key in ('pitch_deg','pitch_rate_dps'):
            for v in (-5,5):
                result=ground_command(dict(attitude,**{key:v}),{0:0,1:0})
                self.assertTrue(all(t*v>0 for t in result.values()))
        saturated=ground_command(dict(attitude,pitch_deg=10,pitch_rate_dps=50),{0:0,1:0})
        self.assertTrue(all(.075<v<=.08 for v in saturated.values()))
        # No extra host speed damper changes torque when delayed wheel speeds differ.
        self.assertEqual(ground_command(attitude,{0:1,1:-1}),{0:0,1:0})

    def test_wire_quantized_predicted_net_torque_is_bounded_during_reversal(self):
        for pitch in (-10,0,10):
            for rate in (-50,0,50):
                for speed in (-2,-1,0,1,2):
                    cmd=ground_command(dict(pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0),{0:speed,1:-speed})
                    for mid,v in {0:speed,1:-speed}.items():
                        packet=torque_packet(mid,cmd[mid],GROUND_PLAN)
                        torque,_,_,_,kd=struct.unpack_from('<hhihh',packet,4)
                        predicted=torque/256000*RATIO-kd/128000000*RATIO**2*v
                        self.assertLessEqual(abs(predicted),.080000001)
                        self.assertLessEqual(abs(cmd[mid]),.08)

    def test_recovery_changes_only_command_envelope_and_keeps_existing_stops(self):
        self.assertEqual(set(RECOVERY_PLAN),set(LONG_OBSERVE_PLAN))
        self.assertEqual({k for k in LONG_OBSERVE_PLAN if RECOVERY_PLAN[k]!=LONG_OBSERVE_PLAN[k]},
                         {'name','feedforward_torque_limit_nm','predicted_net_torque_limit_nm','active_message'})
        for field,value,reason in [('temperature_c',70,'servo_temperature_stop'),
                                   ('torque_estimate_nm',.121,'estimated_torque_stop'),
                                   ('speed_rad_s',2.01,'wheel_speed_stop')]:
            def transform(exchanges,bus):
                original=exchanges[0]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    return dict(row,**{field:value}) if phase=='ground_pd' else row
                return {**exchanges,0:feedback}
            bus,report=self.run_case(transform=transform,plan=RECOVERY_PLAN)
            self.assertEqual(report['reason'],reason)
            self.assert_stopped_without_rearm(bus,report)

    def test_recovery_quantized_net_envelope_at_both_wheel_signs(self):
        for pitch in (-10,0,10):
            for rate in (-50,0,50):
                for speed in (-2,-1,0,1,2):
                    cmd=ground_command(dict(pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0),
                                       {0:speed,1:-speed},RECOVERY_PLAN)
                    for mid,sign,v in ((0,1,speed),(1,-1,-speed)):
                        packet=torque_packet(mid,sign*cmd[mid],RECOVERY_PLAN)
                        torque,wire_speed,wire_pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
                        predicted_forward=sign*torque/256000*RATIO-kd/128000000*RATIO**2*v
                        self.assertEqual((wire_speed,wire_pos,kp),(0,0,0))
                        self.assertLessEqual(abs(predicted_forward),.120000001)
                        self.assertLessEqual(abs(cmd[mid]),.12)
                        self.assertLessEqual(abs(torque/256000*RATIO),.12)
        saturated=ground_command(dict(pitch_deg=10,pitch_rate_dps=50,roll_deg=0),
                                 {0:0,1:0},RECOVERY_PLAN)
        self.assertTrue(all(.11<v<=.12 for v in saturated.values()))

    def test_earlier_response_changes_only_p_and_preserves_command_envelope(self):
        self.assertEqual(set(EARLY_PLAN),set(RECOVERY_PLAN))
        self.assertEqual({k for k in RECOVERY_PLAN if EARLY_PLAN[k]!=RECOVERY_PLAN[k]},
                         {'name','kp_nm_per_rad','active_message'})
        for pitch in (-2,2):
            a=dict(pitch_deg=pitch,pitch_rate_dps=0,roll_deg=0)
            old=ground_command(a,{0:0,1:0},RECOVERY_PLAN)
            new=ground_command(a,{0:0,1:0},EARLY_PLAN)
            for mid in (0,1):
                self.assertAlmostEqual(new[mid],2*old[mid])
                self.assertLessEqual(abs(new[mid]),.12)
        a=dict(pitch_deg=0,pitch_rate_dps=5,roll_deg=0)
        self.assertEqual(ground_command(a,{0:0,1:0},RECOVERY_PLAN),
                         ground_command(a,{0:0,1:0},EARLY_PLAN))
        for speed in (-2,0,2):
            saturated=ground_command(dict(pitch_deg=10,pitch_rate_dps=50,roll_deg=0),
                                     {0:speed,1:-speed},EARLY_PLAN)
            for mid,v in ((0,speed),(1,-speed)):
                packet=torque_packet(mid,saturated[mid],EARLY_PLAN)
                ff,_,_,_,kd=struct.unpack_from('<hhihh',packet,4)
                net=ff/256000*RATIO-kd/128000000*RATIO**2*v
                self.assertLessEqual(abs(net),.120000001)

    def test_attitude_speed_and_nonfinite_rejected(self):
        normal=dict(pitch_deg=0,pitch_rate_dps=0,roll_deg=0)
        for key,v in [('pitch_deg',12.1),('roll_deg',8.1),('pitch_rate_dps',101),('pitch_deg',float('nan'))]:
            with self.assertRaises(Fault):ground_command(dict(normal,**{key:v}),{0:0,1:0})
        with self.assertRaisesRegex(Fault,'wheel_speed'):
            ground_command(normal,{0:0,1:2.01})

    def test_reduced_rate_damping_keeps_fixed_zero_and_only_reduces_rate_term(self):
        self.assertEqual(set(REDUCED_DAMPING_PLAN),set(FIXED_PLAN))
        self.assertEqual({k for k in FIXED_PLAN if FIXED_PLAN[k]!=REDUCED_DAMPING_PLAN[k]},
                         {'name','kd_nm_per_rad_s','active_message'})
        self.assertFalse(REDUCED_DAMPING_PLAN['capture_start_reference'])
        for direction in (-1,1):
            a=dict(pitch_deg=direction,pitch_rate_dps=0,roll_deg=0)
            self.assertEqual(ground_command(a,{0:0,1:0},REDUCED_DAMPING_PLAN),
                             ground_command(a,{0:0,1:0},FIXED_PLAN))
            a=dict(pitch_deg=0,pitch_rate_dps=direction*20,roll_deg=0)
            old=ground_command(a,{0:0,1:0},FIXED_PLAN)
            new=ground_command(a,{0:0,1:0},REDUCED_DAMPING_PLAN)
            for mid in (0,1):
                self.assertGreater(new[mid]*direction,0)
                self.assertAlmostEqual(new[mid]/old[mid],.05/.08)
        bus,report=self.run_case(plan=REDUCED_DAMPING_PLAN,travel_factory=HoldTravel)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['run_neutral_pitch_deg'],0)
        self.assertTrue(30<=report['elapsed_s']<30.02)
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')

    def test_trial14_feedback_overrun_still_stops_both_with_reduced_damping(self):
        for offending_id in (0,1):
            def transform(exchanges,bus):
                original=exchanges[offending_id]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    return dict(row,torque_estimate_nm=-.13066036522633745) if phase=='ground_pd' else row
                return {**exchanges,offending_id:feedback}
            bus,report=self.run_case(transform=transform,plan=REDUCED_DAMPING_PLAN,
                                     travel_factory=HoldTravel)
            self.assertEqual(report['reason'],'estimated_torque_stop')
            self.assert_stopped_without_rearm(bus,report)
            self.assertEqual(report['samples'][-1]['wheels'][offending_id]['feedback']['torque_estimate_nm'],
                             -.13066036522633745)

    def test_reversing_does_not_erase_cumulative_travel(self):
        guard=WheelTravel({0:{'position_rad':0},1:{'position_rad':0}},{0:1,1:-1})
        # Each little turn is below the differential limit; net ends at zero.
        for _ in range(3):
            guard.update(0,{'position_rad':.25});guard.update(0,{'position_rad':0})
        guard.update(0,{'position_rad':.3})
        with self.assertRaisesRegex(Fault,'rolling_path'):
            guard.update(0,{'position_rad':0})

    def test_wheel_signs_in_differential_travel(self):
        guard=WheelTravel({0:{'position_rad':5},1:{'position_rad':-5}},{0:1,1:-1})
        guard.update(0,{'position_rad':5.5});guard.update(1,{'position_rad':-5.5})
        self.assertEqual(guard.snapshot()['differential_offset_m'],0)
        with self.assertRaisesRegex(Fault,'differential'):
            guard.update(1,{'position_rad':-4.5})

    def test_hold_changes_only_body_damping_duration_and_travel_windows(self):
        self.assertEqual(set(HOLD_PLAN)-set(EARLY_PLAN),{'net_rolling_limit_m'})
        self.assertEqual({k for k in EARLY_PLAN if EARLY_PLAN[k]!=HOLD_PLAN[k]},
                         {'name','duration_s','kd_nm_per_rad_s','rolling_path_limit_m','active_message'})
        self.assertEqual(HOLD_PLAN['duration_s'],30)
        self.assertEqual(HOLD_PLAN['net_rolling_limit_m'],.04)
        self.assertEqual(HOLD_PLAN['rolling_path_limit_m'],.40)
        self.assertEqual(HOLD_PLAN['kd_nm_per_rad_s'],.08)

    def test_hold_reversals_preserve_cumulative_budget_and_net_guard(self):
        guard=HoldTravel({0:{'position_rad':0},1:{'position_rad':0}},{0:1,1:-1})
        def cycle():
            guard.update(0,{'position_rad':.2});guard.update(1,{'position_rad':-.2})
            guard.update(0,{'position_rad':0});guard.update(1,{'position_rad':0})
        for _ in range(10):cycle()
        self.assertGreater(guard.path[0],.08)
        self.assertLess(guard.path[0],.40)
        self.assertEqual(guard.offset,{0:0,1:0})
        with self.assertRaisesRegex(Fault,'rolling_path'):
            for _ in range(20):cycle()
        guard=HoldTravel({0:{'position_rad':0},1:{'position_rad':0}},{0:1,1:-1})
        for position in (.25,.5,.75):
            guard.update(0,{'position_rad':position})
            guard.update(1,{'position_rad':-position})
        with self.assertRaisesRegex(Fault,'wheel_net_travel'):
            guard.update(0,{'position_rad':1.0})
        self.assertLess(guard.path[0],.40)

    def test_hold_net_travel_fault_stops_both_without_rearm(self):
        def transform(exchanges,bus):
            counts={0:0,1:0}
            def wrap(mid):
                original=exchanges[mid]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    if phase=='ground_pd':
                        counts[mid]+=1
                        row=dict(row,position_rad=counts[mid]*.01*(1 if mid==0 else -1))
                    return row
                return feedback
            return {m:wrap(m) for m in (0,1)}
        bus,report=self.run_case(transform=transform,plan=HOLD_PLAN,travel_factory=HoldTravel)
        self.assertEqual(report['reason'],'wheel_net_travel_stop')
        self.assert_stopped_without_rearm(bus,report)

    def test_larger_net_window_keeps_other_guards_and_stops_both_at_new_boundary(self):
        self.assertEqual(set(TRAVEL_WINDOW_PLAN),set(REDUCED_DAMPING_PLAN))
        self.assertEqual({k for k in REDUCED_DAMPING_PLAN if REDUCED_DAMPING_PLAN[k]!=TRAVEL_WINDOW_PLAN[k]},
                         {'name','net_rolling_limit_m','active_message'})
        def transform(exchanges,bus):
            counts={0:0,1:0}
            def wrap(mid):
                original=exchanges[mid]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    if phase=='ground_pd':
                        counts[mid]+=1
                        row=dict(row,position_rad=counts[mid]*.01*(1 if mid==0 else -1))
                    return row
                return feedback
            return {m:wrap(m) for m in (0,1)}
        bus,report=self.run_case(transform=transform,plan=TRAVEL_WINDOW_PLAN,travel_factory=HoldTravel)
        self.assertEqual(report['reason'],'wheel_net_travel_stop')
        self.assert_stopped_without_rearm(bus,report)
        offsets=[s['rolling_equivalent']['forward_offset_m'][0] for s in report['samples']]
        self.assertTrue(any(.04<v<.10 for v in offsets))
        self.assertGreaterEqual(offsets[-1],.10)
        self.assertLess(offsets[-1],.101)

    def test_three_second_trial_stops_and_does_not_claim_balance(self):
        bus,report=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertTrue(3<=report['elapsed_s']<3.02)
        self.assertGreater(len(report['samples']),290)
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')
        self.assertFalse(any(phase=='wait_tilt_disabled' for _,_,phase in bus.log))
        self.assertLess(report['samples'][0]['t'],1.)
        wheels=report['samples'][-1]['wheels']
        self.assertGreater(wheels[0]['command_protocol_nm'],0)
        self.assertLess(wheels[1]['command_protocol_nm'],0)

    def test_ten_second_observation_is_bounded_with_same_motion_profile(self):
        changed={k for k in GROUND_PLAN if GROUND_PLAN[k]!=OBSERVE_PLAN[k]}
        self.assertEqual(changed,{'name','duration_s','active_message'})
        bus,report=self.run_case(plan=OBSERVE_PLAN)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(10<=report['elapsed_s']<10.02)
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')

    def test_long_observation_keeps_stops_and_captures_delayed_operator_motion(self):
        self.assertEqual(set(LONG_OBSERVE_PLAN),set(GROUND_PLAN))
        self.assertEqual({k for k in GROUND_PLAN if GROUND_PLAN[k]!=LONG_OBSERVE_PLAN[k]},
                         {'name','duration_s','active_message'})
        class DelayedMotionIMU:
            def __init__(self,bus):self.bus=bus
            def sample(self):
                self.bus.sleep(.01);t=self.bus.t
                p=min(3,max(0,t-16))
                return dict(t_read_complete=t,
                            accel_g=[math.sin(math.radians(p)),0,math.cos(math.radians(p))],
                            gyro_dps=[0,-1 if 16<t<19 else 0,0])
        bus,report=self.run_case(imu_factory=DelayedMotionIMU,plan=LONG_OBSERVE_PLAN)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(60<=report['elapsed_s']<60.02)
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')
        before=[s for s in report['samples'] if s['elapsed_s']<10]
        after=[s for s in report['samples'] if s['elapsed_s']>20]
        self.assertTrue(before and after)
        self.assertTrue(all(abs(s['wheels'][0]['command_forward_nm'])<1e-9 for s in before))
        self.assertTrue(all(s['wheels'][0]['command_forward_nm']>.07 for s in after))
        def hot_feedback(exchanges,bus):
            original=exchanges[0]
            def feedback(packet,phase):
                row=original(packet,phase)
                return dict(row,temperature_c=70) if phase=='ground_pd' and bus.t>20 else row
            return {**exchanges,0:feedback}
        bus,report=self.run_case(transform=hot_feedback,imu_factory=DelayedMotionIMU,
                                 plan=LONG_OBSERVE_PLAN)
        self.assertEqual(report['reason'],'servo_temperature_stop')
        self.assert_stopped_without_rearm(bus,report)

    def test_manual_ground_tilt_keeps_waiting_packets_disabled(self):
        def transform(exchanges,bus):
            def wrap(original):
                def feedback(packet,phase):
                    row=original(packet,phase)
                    if phase=='wait_tilt_disabled' and 1<bus.t<2:
                        row['speed_rad_s']=.1
                    return row
                return feedback
            return {m:wrap(exchanges[m]) for m in (0,1)}
        bus,report=self.run_case(transform)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(all(p[2]&0x70==0 for _,p,phase in bus.log if phase.startswith('wait_')))

    def test_handheld_offset_and_small_tremor_need_no_precise_pose(self):
        class HandheldIMU:
            def __init__(self,bus):self.bus=bus
            def sample(self):
                self.bus.sleep(.01);t=self.bus.t
                p=6+.3*math.sin(8*t)+min(4,max(0,4*(t-2)))
                rate=2.4*math.cos(8*t)+(4 if 2<t<3 else 0)
                return dict(t_read_complete=t,accel_g=[math.sin(math.radians(p)),0,math.cos(math.radians(p))],gyro_dps=[0,-rate,0])
        bus,report=self.run_case(imu_factory=HandheldIMU)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(5.7<report['run_neutral_pitch_deg']<6.3)
        self.assertTrue(report['final_disabled_verified'])

    def test_fixed_reference_corrects_both_held_offsets_without_moving_target(self):
        self.assertEqual(set(FIXED_PLAN),set(HOLD_PLAN))
        self.assertEqual({k for k in HOLD_PLAN if HOLD_PLAN[k]!=FIXED_PLAN[k]},
                         {'name','capture_start_reference','wait_upright_message','active_message'})
        for held_pitch in (-3,3):
            class OffsetIMU:
                def __init__(self,bus):self.bus=bus
                def sample(self):
                    self.bus.sleep(.01)
                    return dict(t_read_complete=self.bus.t,
                                accel_g=[math.sin(math.radians(held_pitch)),0,math.cos(math.radians(held_pitch))],
                                gyro_dps=[0,0,0])
            bus,report=self.run_case(imu_factory=OffsetIMU,plan=FIXED_PLAN,travel_factory=HoldTravel)
            self.assertEqual(report['status'],'PASS')
            self.assertTrue(30<=report['elapsed_s']<30.02)
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['run_neutral_pitch_deg'],0)
            self.assertAlmostEqual(report['operator_held_pitch_mean_deg'],held_pitch)
            for s in report['samples']:
                self.assertAlmostEqual(s['attitude']['pitch_error_deg'],held_pitch)
                for mid in (0,1):
                    self.assertGreater(s['wheels'][mid]['command_forward_nm']*held_pitch,0)
                    self.assertLessEqual(abs(s['wheels'][mid]['command_forward_nm']),.12)

    def test_temporary_target_does_not_shift_absolute_tilt_stop(self):
        a=dict(pitch_deg=6,pitch_error_deg=0,pitch_rate_dps=0,roll_deg=0)
        self.assertEqual(ground_command(a,{0:0,1:0}),{0:0,1:0})
        with self.assertRaisesRegex(Fault,'body_tilt'):
            ground_command(dict(a,pitch_deg=12.1,pitch_error_deg=.1),{0:0,1:0})

    def test_feedback_faults_stop_before_second_active_command(self):
        for change,reason in [({'speed_rad_s':2.1},'wheel_speed_stop'),
                              ({'temperature_c':70},'servo_temperature_stop'),
                              ({'position_rad':1.0},'differential_wheel_travel_stop'),
                              ({'position_rad':2.1},'wheel_rolling_path_stop'),
                              ({'position_rad':float('nan')},'nonfinite_control_value')]:
            def transform(exchanges,bus):
                original=exchanges[0]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    return dict(row,**change) if phase=='ground_pd' else row
                return {**exchanges,0:feedback}
            bus,report=self.run_case(transform)
            self.assert_stopped_without_rearm(bus,report)
            self.assertEqual(report['reason'],reason)
            self.assertEqual([m for m,_,phase in bus.log if phase=='ground_pd'],[0])

    def test_imu_fault_or_delay_stops_both(self):
        for case in ({'fail':True},{'delay':True}):
            bus,report=self.run_case(imu_kwargs=case)
            self.assert_stopped_without_rearm(bus,report)

    def test_rejected_tilt_frame_is_logged_before_any_motor_write(self):
        class TiltStopIMU:
            def __init__(self,bus):self.bus=bus
            def sample(self):
                self.bus.sleep(.01);t=self.bus.t
                p=min(20,max(0,20*(t-2)))
                return dict(t_read_complete=t,
                            accel_g=[math.sin(math.radians(p)),0,math.cos(math.radians(p))],
                            gyro_dps=[0,-20 if 2<t<3 else 0,0])
        bus,report=self.run_case(imu_factory=TiltStopIMU)
        self.assertEqual(report['reason'],'body_tilt_stop')
        self.assert_stopped_without_rearm(bus,report)
        last=report['samples'][-1]
        self.assertGreater(last['attitude']['pitch_deg'],12)
        self.assertEqual(last['control_rejected'],'body_tilt_stop')
        self.assertEqual(last['wheels'],{})
        self.assertTrue(last['imu'])
        self.assertTrue(0<report['elapsed_s']<3)
        self.assertEqual(report['control_cycles'],len(report['samples'])-1)
        self.assertEqual(sum(phase=='ground_pd' for _,_,phase in bus.log),2*report['control_cycles'])

    def test_bus_fault_and_stale_peer_stop_both(self):
        for failure in ('bus','stale'):
            def transform(exchanges,bus):
                original=exchanges[0]
                def feedback(packet,phase):
                    row=original(packet,phase)
                    if phase=='ground_pd':
                        if failure=='bus':raise TimeoutError('injected_bus_fault')
                        bus.sleep(.011)
                    return row
                return {**exchanges,0:feedback}
            bus,report=self.run_case(transform)
            self.assert_stopped_without_rearm(bus,report)
            self.assertEqual([m for m,_,phase in bus.log if phase=='ground_pd'],[0])


if __name__=='__main__':unittest.main()
