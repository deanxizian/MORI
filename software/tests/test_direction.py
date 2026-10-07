import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mount=module('check_mount');signs=module('check_control_signs')
class Direction(unittest.TestCase):
    def fixture(self):
        return dict(source='SIMULATED',rotation_raw_to_control=[[1,0,0],[0,1,0],[0,0,1]],
                    encoder_sign=[1,-1],motor_sign=[1,-1],forward_handwheel_raw_count_delta=[10,-10],
                    positive_output_causes_forward_rotation=[True,True],forward_lean_raw_gyro_rad_s=[0,.2,0],
                    six_faces_raw_accel_m_s2={axis:[(1 if axis[0]=='+' else -1)*9.80665 if i=='xyz'.index(axis[1]) else 0 for i in range(3)] for axis in ('+x','-x','+y','-y','+z','-z')})
    def test_valid_consistency(self):self.assertEqual(mount.check(self.fixture())['numeric_consistency'],'PASS')
    def test_reflection_rejected(self):
        r=self.fixture();r['rotation_raw_to_control'][2][2]=-1
        with self.assertRaises(ValueError):mount.check(r)
    def test_reversed_pitch_rejected(self):
        r=self.fixture();r['forward_lean_raw_gyro_rad_s'][1]=-.2
        with self.assertRaises(ValueError):mount.check(r)
    def test_encoder_reversal_rejected(self):
        r=self.fixture();r['encoder_sign'][1]=1
        with self.assertRaises(ValueError):mount.check(r)
    def test_output_unconfirmed_rejected(self):
        r=self.fixture();r['positive_output_causes_forward_rotation'][0]=None
        with self.assertRaises(ValueError):mount.check(r)
    def test_physical_sign_equation(self):self.assertEqual(signs.probe()['status'],'PASS')
if __name__=='__main__':unittest.main()
