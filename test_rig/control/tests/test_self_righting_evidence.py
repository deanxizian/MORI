"""Offline verdict checks using prescribed traces, never real-robot proof."""
import copy
import unittest

from analyze_self_righting import assess
from test_attitude_air import CAL
import test_self_righting


def fixture(**kwargs):
    bus,report=test_self_righting.SelfRightingTests().run_trace(**kwargs)
    report['calibration']=copy.deepcopy(CAL)
    report['imu']={'configuration_restored':True}
    report['per_id']={str(mid):{'transactions':[
        {'tx_hex':packet.hex(),'phase':phase} for m,packet,phase in bus.log if m==mid]}
        for mid in (0,1)}
    return report


class SensorEvidenceTests(unittest.TestCase):
    def test_sensor_window_can_pass_without_a_human_action_judgment(self):
        report=fixture()
        result=assess(report)
        self.assertEqual(result['sensor_self_righting_status'],'PASS')
        self.assertGreater(result['ending_stable_window_s'],2)
        self.assertFalse(result['onsite_action_judgment_required'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')

    def test_prearm_exit_is_not_tested_and_active_failure_is_fail(self):
        self.assertEqual(assess(fixture(start_angle=0))['sensor_self_righting_status'],'NOT_TESTED')
        result=assess(fixture(stuck=True))
        self.assertEqual(result['sensor_self_righting_status'],'FAIL')
        self.assertEqual(result['phases'],['RISING'])

    def test_supervised_scope_is_supported_but_abort_and_diagnostic_are_not_success(self):
        report=fixture();report['plan']['control_phase']='supervised_self_righting'
        self.assertEqual(assess(report)['sensor_self_righting_status'],'PASS')
        report['samples'][-1]['attitude']['self_righting']={'phase':'ABORT_BRAKE'}
        self.assertEqual(assess(report)['sensor_self_righting_status'],'FAIL')
        report['plan']['control_phase']='low_speed_stop_probe'
        with self.assertRaisesRegex(ValueError,'not_a_self_righting_trial'):assess(report)

    def test_short_stale_rejected_and_unconfirmed_stop_cannot_pass(self):
        original=fixture()
        variants=[]
        r=copy.deepcopy(original);r['elapsed_s']=1.;variants.append(r)
        r=copy.deepcopy(original);r['final_disabled_verified']=False;variants.append(r)
        r=copy.deepcopy(original);r['imu']['configuration_restored']=False;variants.append(r)
        r=copy.deepcopy(original);r['samples'][-1]['attitude']['t']+=.1;variants.append(r)
        r=copy.deepcopy(original);r['rejected_imu_sample']=dict(
            phase='active_control',reason='acceleration_outside_test_window',
            imu={'accel_g':[0,0,1.6]});variants.append(r)
        for report in variants:
            self.assertEqual(assess(report)['sensor_self_righting_status'],'FAIL')
        self.assertEqual(assess(variants[-1])['rejected_sensor_sample']['accel_norm_g'],1.6)


if __name__=='__main__':
    unittest.main()
