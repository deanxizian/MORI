import unittest
from attitude import Fault
from self_righting_trial import position_rates
from self_righting_charged_supply import PLAN
from self_righting_supervised import SupervisedRecovery
from air_trial import run
from test_self_righting import TraceIMU
from test_attitude_air import CAL
from test_wheel_check import Bus

class FeedbackTimeRatesTests(unittest.TestCase):
    def frame(self):
        return dict(t=1.013,dt=.009,wheel_position_forward_rad={0:.12,1:.12},
                    wheel_feedback_received_monotonic={0:1.012,1:1.012})

    def test_encoder_interval_not_imu_interval(self):
        a=self.frame();r,t=position_rates(a,{0:10.,1:10.},{0:0.,1:0.},{0:1.,1:1.},.009,PLAN)
        for v in r.values():self.assertAlmostEqual(v,10.)
        legacy,_=position_rates(a,{0:10.,1:10.},{0:0.,1:0.},None,.009,dict(PLAN,use_wheel_feedback_timestamps=False))
        self.assertAlmostEqual(legacy[0],13.3333333333333)

    def test_each_wheel_has_its_own_interval_and_first_frame_uses_feedback(self):
        a=self.frame();a['wheel_feedback_received_monotonic'][1]=1.010
        r,_=position_rates(a,{0:3.,1:4.},None,None,.009,PLAN);self.assertEqual(r,{0:3.,1:4.})
        r,_=position_rates(a,{0:10.,1:10.},{0:0.,1:0.},{0:1.,1:1.},.009,PLAN)
        self.assertAlmostEqual(r[0],10.);self.assertAlmostEqual(r[1],12.)

    def test_missing_stale_future_and_nonmonotonic_time_reject(self):
        a=self.frame();del a['wheel_feedback_received_monotonic']
        with self.assertRaisesRegex(Fault,'timestamp_required'):position_rates(a,{0:0.,1:0.},None,None,.009,PLAN)
        for stamp in (0.9,1.02):
            a=self.frame();a['wheel_feedback_received_monotonic'][0]=stamp
            with self.assertRaisesRegex(Fault,'stale_or_future'):position_rates(a,{0:0.,1:0.},None,None,.009,PLAN)
        a=self.frame()
        with self.assertRaisesRegex(Fault,'time_gap'):
            position_rates(a,{0:0.,1:0.},{0:0.,1:0.},{0:1.013,1:1.013},.009,PLAN)

    def test_countdown_does_not_pair_old_imu_with_newer_encoder_feedback(self):
        bus=Bus();exchanges={}
        for mid in (0,1):
            base=bus.exchange(mid)
            def stamped(packet,phase,base=base):
                bus.sleep(.0003);row=base(packet,phase)
                row['feedback_received_monotonic']=bus.now();return row
            exchanges[mid]=stamped
        report={};plan=dict(PLAN,duration_s=.05,prearm_countdown_s=.05,post_stop_observation_s=0.)
        run(exchanges,TraceIMU(bus,stuck=True),CAL,report,True,now=bus.now,sleep=bus.sleep,
            display=lambda _:None,plan=plan,controller=SupervisedRecovery())
        self.assertGreater(report.get('control_cycles',0),0,report.get('reason'))
        self.assertTrue(report['final_disabled_verified'])

if __name__=='__main__':unittest.main()

