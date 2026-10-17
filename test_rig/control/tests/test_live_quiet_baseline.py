import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch

from attitude import Fault
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains
from test_live_tuning import sample
from two_deck_live_position_pitch_frame import PLAN as BASE,PitchFramePositionReturnLiveController
from two_deck_live_quiet_baseline import PLAN,main


class QuietBaselineTests(unittest.TestCase):
    def test_only_exercised_initial_pd_changes_and_default_has_no_io(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
                         {'name','ap_kp','ap_kd','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=2.75,pitch_i=.6,pitch_d=.05,speed_p=.25))
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_existing_controller_packet_parity_with_same_gains_and_budgets(self):
        equivalent=with_gains(BASE,gains(PLAN))
        a=PitchFramePositionReturnLiveController(TuningChannel(gains(PLAN)))
        b=PitchFramePositionReturnLiveController(TuningChannel(gains(equivalent)))
        for i in range(1,1201):
            x=sample(i*.005);x.update(pitch_deg=.8*math.sin(i*.05),
                pitch_rate_dps=20.*math.cos(i*.05),
                wheel_position_forward_rad={0:.2*math.sin(i*.01),1:.2*math.sin(i*.01)})
            y=copy.deepcopy(x);speeds={0:.3*math.sin(i*.04),1:.2*math.cos(i*.03)}
            ca=a(x,speeds,PLAN);cb=b(y,speeds,equivalent)
            self.assertEqual(ca,cb);self.assertEqual(a.position_origin,b.position_origin)
            for m,sign in ((0,1),(1,-1)):
                self.assertEqual(a.allocated_torque_packet(m,sign,ca[m],PLAN),
                                 b.allocated_torque_packet(m,sign,cb[m],equivalent))
                self.assertLessEqual(abs(a.allocations[m].feedforward_nm),.12+1e-12)
                self.assertLessEqual(abs(a.allocations[m].predicted_net_nm),.12+1e-12)

    def test_original_raw_speed_and_stale_feedback_faults_are_unchanged(self):
        for speeds,timestamps in [({0:6.1,1:0.},None),({0:0.,1:0.},{0:.8,1:.8})]:
            c=PitchFramePositionReturnLiveController(TuningChannel(gains(PLAN)))
            c(sample(1.),{0:0.,1:0.},PLAN);x=sample(1.005)
            if timestamps is not None:x['wheel_feedback_received_monotonic']=timestamps
            with self.assertRaises(Fault):c(x,speeds,PLAN)


if __name__=='__main__':unittest.main()
