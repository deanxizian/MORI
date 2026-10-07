"""HW-SW-0.4 acceptance: physical count-to-distance examples, not copied code."""
import hashlib
import json
import math
import pathlib
import subprocess
import tempfile
import unittest

SW = pathlib.Path(__file__).resolve().parents[1]
CORE = SW / 'firmware_work/firmware/components/mori_core'


class Handoff04(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=SW/'reports')
        path = pathlib.Path(cls.temp.name)
        (path/'probe.c').write_text(r'''
#include "mori_io.h"
#include <stdio.h>
int main(void) {
    mori_encoder_t e = {0}; float v[2] = {0}; int signs[2] = {1,-1};
    /* One raw quadrature edge, followed by seven quiet control frames. */
    int32_t counts[2] = {1,-1};
    for (int i=0;i<8;i++)
        if (!mori_encoder_update(&e,counts,.002404f,signs,v)) return 1;
    printf("%.12f %.12f %.12f %.12f %s %s\n",
           (double)MORI_WHEEL_COUNTS_PER_TURN,(double)MORI_WHEEL_M_PER_COUNT,
           (double)v[0],(double)v[1],MORI_REQUIREMENTS_BASELINE,MORI_SOURCE_SNAPSHOT);
    if (!mori_encoder_update(&e,counts,.002404f,signs,v)) return 1;
    printf("%.12f %.12f\n",(double)v[0],(double)v[1]);
    /* A known 48 decoded edges is ONE motor revolution, not four. */
    mori_encoder_t f = {0}; counts[0]=counts[1]=0;
    for (int i=0;i<8;i++) {
        counts[0]+=6; counts[1]-=6;
        if (!mori_encoder_update(&f,counts,.002404f,signs,v)) return 1;
    }
    printf("%.12f %.12f\n",(double)v[0],(double)v[1]);
    printf("INFO 0 MORI/1 " MORI_SCALE_INFO_FORMAT " source=SIMULATED physical=NOT_TESTED\n", MORI_SCALE_INFO_ARGS);
    return 0;
}
''')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                        '-I'+str(CORE/'include'),str(path/'probe.c'),
                        str(CORE/'mori_io.c'),'-lm','-o',str(path/'probe')],check=True)
        cls.probe = subprocess.check_output([str(path/'probe')],text=True).splitlines()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_count_scale_and_version(self):
        count,distance,_,_,requirements,snapshot = self.probe[0].split()
        self.assertAlmostEqual(float(count),979.616,places=5)
        self.assertAlmostEqual(float(distance),math.pi*.095/979.616,places=11)
        self.assertEqual(requirements,'HW-SW-0.4')
        self.assertEqual(snapshot,'HW-SW-0.4')

    def test_one_edge_survives_eight_frame_window(self):
        expected = (math.pi*.095/979.616)/(.002404*8)
        for value in self.probe[0].split()[2:4]:
            self.assertAlmostEqual(float(value),expected,places=7)
        self.assertEqual([float(v) for v in self.probe[1].split()],[0.,0.])

    def test_motor_revolution_does_not_multiply_x4_again(self):
        # Mechanically: one motor revolution travels circumference / exact gearing.
        gear = (22**3*23)/(12*1000)
        expected = (math.pi*.095/gear)/(.002404*8)
        for value in self.probe[2].split():
            self.assertAlmostEqual(float(value),expected,places=6)

    def test_wiring_mirrors_authorized_snapshot(self):
        manifest=json.loads((SW/'reference_sources/HW-SW-0.4_baseline_manifest.json').read_text())
        for name in ['pinmap.csv','wiring.csv']:
            with self.subTest(name=name):
                actual=hashlib.sha256((SW/'firmware_work'/name).read_bytes()).hexdigest()
                self.assertEqual(actual,manifest['sha256'][name])

    def test_device_info_and_recording_preserve_scale_precision(self):
        from test_tools import cli
        line=self.probe[3]
        self.assertIn('wheel_counts_per_turn=979.616 ',line)
        path=pathlib.Path(self.temp.name)/'SIMULATED_hw04_metadata.csv'
        recorder=cli.Recorder(path,'SIMULATED',1)
        recorder.feed(line)
        meta=recorder.close()
        fields=meta['device_metadata']
        self.assertEqual(fields['firmware'],'SW-0.4')
        self.assertEqual(fields['requirements'],'HW-SW-0.4')
        self.assertEqual(fields['origin'],'HW-SW-0.3')
        self.assertEqual(fields['wheel_counts_per_turn'],'979.616')
        self.assertAlmostEqual(float(fields['wheel_m_per_count']),math.pi*.095/979.616,places=11)


if __name__ == '__main__':
    unittest.main()
