import math
import unittest
from controller import Controller, PLAN
from live_tuning import TuningChannel
from live_tuning_policy import gains
from remote_drive_keys import Keys
from two_deck_remote_drive import RemoteDriveController, RemoteVelocityReference
from responsive_remote import ResponsiveVelocityReference
from test_live_tuning import sample, checked_pair


class ResponsiveRemoteTests(unittest.TestCase):
    def exercise(self, code, cls=Controller):
        keys=Keys();keys.attach(0., [])
        clock=[0.]
        c=(Controller(keys,now=lambda:clock[0]) if cls is Controller else
           cls(TuningChannel(gains(PLAN),now=lambda:clock[0]),keys))
        rows=[]
        for i in range(1,701):
            clock[0]=i*.005
            if i==2:keys.event(code,1,clock[0])
            if i==160:keys.event(code,0,clock[0])
            keys.publish(clock[0],keys.held)
            a=sample(clock[0]);commands=c(a,{0:0.,1:0.},PLAN)
            c.observe_pair(checked_pair(a))
            self.assertLessEqual(max(abs(v) for v in commands.values()),.12+1e-10)
            self.assertLessEqual(abs(a['velocity_hold']['pitch_reference_deg']),3.+1e-10)
            rows.append((i,c.remote_v,c.remote_turn,a))
        return rows

    def test_four_directions_keep_caps_and_release(self):
        for code,sign in ((103,1),(108,-1),(106,1),(105,-1)):
            rows=self.exercise(code)
            field=1 if code in (103,108) else 2
            self.assertGreater(sign*rows[100][field],0.)
            self.assertAlmostEqual(rows[-1][field],0.,delta=.002)
            self.assertTrue(all(abs(r[1])<=.16+1e-10 and abs(r[2])<=5.+1e-10 for r in rows))

    def test_both_turn_references_reach_target_twice_as_fast_and_keep_release_slew(self):
        for code in (105,106):
            new,old=self.exercise(code),self.exercise(code,RemoteDriveController)
            tn=next(r[0] for r in new if abs(r[2])>=3.6)
            to=next(r[0] for r in old if abs(r[2])>=3.6)
            self.assertLessEqual(tn,to*.55)
            for i in range(159,len(new)):
                self.assertLessEqual(abs(new[i][2]-new[i-1][2]),6.*.005+1e-12)
                self.assertLessEqual(abs(new[i][2]),abs(new[i-1][2])+1e-12)

    def test_forward_reverse_use_stronger_following_only_while_held(self):
        for code in (103,108):
            rows=self.exercise(code)
            a=rows[80][3]
            self.assertTrue(a['velocity_hold']['responsive_drive_active'])
            self.assertEqual(a['velocity_hold']['selected_speed_gain'],.50)
            self.assertEqual(a['velocity_hold']['selected_pitch_slew_dps'],12.)
            for _,_,_,a in rows[159:]:
                self.assertFalse(a['velocity_hold']['responsive_drive_active'])
                self.assertEqual(a['velocity_hold']['selected_speed_gain'],PLAN['speed_kp_rad_per_m_s'])
                self.assertEqual(a['velocity_hold']['selected_pitch_slew_dps'],PLAN['speed_pitch_reference_slew_dps'])

    def test_neutral_reference_matches_frozen_controller(self):
        new,old=ResponsiveVelocityReference(),RemoteVelocityReference()
        for i in range(1,200):
            a,b=sample(i*.005),sample(i*.005)
            self.assertEqual(new(a,{0:0.,1:0.},PLAN),old(b,{0:0.,1:0.},PLAN))
            self.assertEqual(new.pitch_reference_deg,old.pitch_reference_deg)

    def test_reversal_does_not_boost_old_direction(self):
        r=ResponsiveVelocityReference();r.velocity_proxy=lambda a,s,p:.05
        for i in range(1,40):
            a=sample(i*.005)
            a.update(remote_desired_velocity_m_s=-.12,remote_velocity_target_m_s=.05)
            r(a,{0:0.,1:0.},PLAN)
            self.assertFalse(a['velocity_hold']['responsive_drive_active'])

    def test_extended_target_and_copied_reference_match_frozen_within_old_range(self):
        new,old=ResponsiveVelocityReference(),RemoteVelocityReference()
        for i in range(1,501):
            a,b=sample(i*.005),sample(i*.005)
            for item in (a,b):
                item.update(remote_velocity_target_m_s=.12 if i<250 else 0.,
                            remote_stopping=i>=250,
                            remote_reference_transition=i<30,
                            remote_body_limited=100<i<150)
            self.assertEqual(new._bounded_remote_call(a,{0:0.,1:0.},PLAN),
                             old(b,{0:0.,1:0.},PLAN))
            self.assertEqual(a['velocity_hold'],b['velocity_hold'])
        a=sample(2.505);a['remote_velocity_target_m_s']=.16
        new._bounded_remote_call(a,{0:0.,1:0.},PLAN)
        self.assertEqual(a['velocity_hold']['target_velocity_m_s'],.16)
        from attitude import Fault
        a=sample(2.510);a['remote_velocity_target_m_s']=.161
        with self.assertRaises(Fault):new._bounded_remote_call(a,{0:0.,1:0.},PLAN)

    def test_combined_keys_axis_changes_and_release_keep_wheel_reference_budget(self):
        keys=Keys();keys.attach(0.,[]);clock=[0.]
        c=Controller(keys,now=lambda:clock[0])
        previous=(0.,0.)
        actions={2:((103,1),(106,1)),250:((103,0),),400:((108,1),),
                 600:((106,0),(105,1)),800:((108,0),(105,0))}
        for i in range(1,1601):
            clock[0]=i*.005
            for code,value in actions.get(i,()):keys.event(code,value,clock[0])
            keys.publish(clock[0],keys.held)
            a=sample(clock[0]);commands=c(a,{0:0.,1:0.},PLAN)
            c.observe_pair(checked_pair(a))
            self.assertLessEqual(abs(c.remote_v)/.04+abs(c.remote_turn)/2,5.+1e-10)
            self.assertLessEqual(abs(c.remote_v-previous[0]),.40*.005+1e-10)
            self.assertLessEqual(abs(c.remote_turn-previous[1]),16.*.005+1e-10)
            self.assertEqual(c.drive_profile.velocity,c.remote_v)
            self.assertLessEqual(max(map(abs,commands.values())),.12+1e-10)
            previous=c.remote_v,c.remote_turn
        self.assertEqual(previous,(0.,0.))
