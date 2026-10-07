import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from pipeline_evidence import annotate_retries, current_inputs, render_outputs, sha, verify_resume
from report_current import generate
from mesh_components import components

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name in ['mechanical/reports','mechanical/scripts','mechanical/renders','config']:(self.root/name).mkdir(parents=True)
        self.write('config/geometry.json',{'revision':'V1.2-M1.52'})
        self.write('mechanical/reports/build_manifest.json',{'input_sha256':{'config/geometry.json':sha(self.root/'config/geometry.json')}})
    def write(self,name,data):
        p=self.root/name;p.write_text(json.dumps(data));return p
    def test_resume_rejects_changed_input_and_deleted_output(self):
        out=self.write('mechanical/model.json',{'data':1})
        record={'stage':'build','returncode':0,'input_sha256':current_inputs(self.root),'artifact_sha256':{'mechanical/model.json':sha(out)}}
        self.assertEqual(verify_resume(self.root,[record],['build']),[record])
        out.unlink()
        with self.assertRaisesRegex(ValueError,'output'):verify_resume(self.root,[record],['build'])
        self.write('config/geometry.json',{'revision':'changed'})
        with self.assertRaisesRegex(ValueError,'inputs changed'):verify_resume(self.root,[record],['build'])
    def test_render_requires_actual_bytes_and_full_view_set(self):
        image=self.root/'mechanical/renders/front.png';image.write_bytes(b'image-one')
        row={'view':'front','geometry_sha256':'geometry','image_sha256':sha(image),'image_bytes':image.stat().st_size}
        self.assertEqual(render_outputs(self.root/'mechanical',[row],['front'],'geometry')['status'],'PASS')
        for mutate in [lambda:image.write_bytes(b'image-two'),lambda:image.unlink(missing_ok=True)]:
            mutate();self.assertEqual(render_outputs(self.root/'mechanical',[row],['front'],'geometry')['status'],'FAIL')
        self.assertEqual(render_outputs(self.root/'mechanical',[],['front'],'geometry')['status'],'FAIL')
    def test_retry_requires_matching_log_and_current_artifact(self):
        bad={'stage':'paths','returncode':1,'started_utc':'1'}
        good={'stage':'paths','returncode':0,'started_utc':'2'}
        self.assertEqual(annotate_retries([bad,good],self.root)[0]['retry_verification'],'BLOCKED')
        log=self.write('run.log',{'result':0});out=self.write('out.json',{'status':'PASS'})
        good.update(log='run.log',log_sha256=sha(log),artifact_sha256={'out.json':sha(out)})
        self.assertEqual(annotate_retries([bad,good],self.root)[0]['retry_verification'],'PASS')
        out.write_text('stale')
        self.assertEqual(annotate_retries([bad,good],self.root)[0]['retry_verification'],'BLOCKED')
    def test_current_report_never_falls_back_to_historical_pass(self):
        gallery=self.root/'mechanical/index.html';gallery.write_text('retained gallery')
        with self.assertRaisesRegex(RuntimeError,'blocked'):generate(self.root)
        self.assertIn('M1.52',(self.root/'mechanical/current_report.html').read_text())
        self.assertEqual(gallery.read_text(),'retained gallery')
        model=self.write('mechanical/mori_v1_2.blend',{'geometry':1})
        self.write('mechanical/reports/validation.json',{'source_blend_sha256':sha(model),'counts':{'PASS':1,'FAIL':0,'BLOCKED':2}})
        self.write('mechanical/reports/delivery_consistency.json',{'status':'PASS'})
        self.write('mechanical/reports/export_manifest.json',{'candidate_count':1,'exported_count':1})
        self.assertEqual(generate(self.root)['status'],'PASS')
        self.write('config/geometry.json',{'revision':'V1.2-M1.53'})
        with self.assertRaisesRegex(RuntimeError,'Stale build'):generate(self.root)
    def test_distinct_small_island_is_reported(self):
        vertices=[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),(3,0,0),(2,1,0),(2,0,1)]
        tetra=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        groups=components(vertices,tetra+[tuple(v+4 for v in f) for f in tetra])
        self.assertEqual(len(groups),2);self.assertAlmostEqual(groups[0]['volume_mm3_abs'],1/6)

if __name__=='__main__':unittest.main()
