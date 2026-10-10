"""Exercise the actual page generator and Blender guide expression without bpy."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2]/'mechanical/scripts'
sys.path.insert(0, str(SCRIPTS))
import animation_page


class AnimationR2PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.root = self.project/'mechanical'
        self.out = self.root/'animation'
        self.out.mkdir(parents=True)
        self.config = {'revision': 'V1.2-M1.55', 'reaction_clamp_entry': {'enabled': True},
                       'reaction_nut_alignment': {'enabled': True}}
        self.write('config/geometry.json', self.config)
        for name in ['mori_v1_2.blend', 'mori_assembly_animation.blend', 'animation/MORI_assembly.mp4']:
            (self.root/name).write_bytes(name.encode())
        digest = lambda name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
        self.manifest = dict(revision='V1.2-M1.55', animation_revision='V1.2-M1.55-A1',
            rendered_video=True, source_blend_sha256=digest('mori_v1_2.blend'),
            animation_blend_sha256=digest('mori_assembly_animation.blend'),
            video=dict(file='MORI_assembly.mp4', sha256=digest('animation/MORI_assembly.mp4')),
            fps=24, duration_seconds=87.5, resolution=[1280,720], stage_count=1,
            stages=[dict(index=1, title='R2', start=1)], body_sequence_kind='front_rear',
            body_sequence_readback={'status':'PASS'})
        self.write('mechanical/animation/manifest.json', self.manifest)
        self.write('mechanical/animation/validation.json', dict(status='PASS', video=self.manifest['video']))
        self.evidence = dict(status='PASS', source_blend_sha256=self.manifest['source_blend_sha256'],
                             animation_blend_sha256=self.manifest['animation_blend_sha256'])
        self.evidence_paths = ['reports/reaction_clamp_entry_validation.json',
            'studies/reaction_clamp_R2_adoption/animation_reaction_entry.json',
            'studies/reaction_clamp_R2_adoption/bench_followup.json']
        for name in self.evidence_paths:
            self.write('mechanical/'+name, self.evidence)

    def write(self, name, data):
        path = self.project/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_r2_supersedes_legacy_initial_assembly_notices_but_not_real_blockers(self):
        section = animation_page.generate(self.root)
        page = (self.out/'index.html').read_text()
        for text in [page, section]:
            self.assertIn('R2 裸反力轴装入已通过', text)
            self.assertIn('最终锁紧叠层、完整带线装配及实物强度仍未验证', text)
            self.assertNotIn('反力夹初装仍待完成', text)
            self.assertNotIn('上部舵盘夹口仍按预装总成演示', text)

    def test_stale_or_missing_evidence_cannot_emit_verified_r2(self):
        for name in self.evidence_paths:
            with self.subTest(name=name):
                self.write('mechanical/'+name, dict(self.evidence, source_blend_sha256='stale'))
                animation_page.generate(self.root)
                text = (self.out/'index.html').read_text()
                self.assertIn('须恢复匹配资料或重新回读', text)
                self.assertNotIn('R2 裸反力轴装入已通过', text)
                self.write('mechanical/'+name, self.evidence)
        (self.root/self.evidence_paths[-1]).unlink()
        self.assertFalse(animation_page.reaction_entry_verified(self.root, self.manifest))

    def test_generated_blender_guide_selects_current_or_legacy_scope(self):
        tree = ast.parse((SCRIPTS/'assembly_animation.py').read_text())
        guide = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'guide' for t in n.targets))
        code = compile(ast.Expression(guide), '<actual assembly guide>', 'eval')
        context = dict(ANIMATION_REVISION='V1.2-M1.55-A1', SCENE_NAME='MORI_Assembly_Animation',
                       scene=SimpleNamespace(frame_end=2100), FPS=24, stages=[0]*22, P=self.config)
        current = eval(code, context)
        self.assertIn('R2 已应用裸反力轴从下方装入', current)
        self.assertNotIn('上部舵盘夹口初次装配和最终五金选型仍未完成', current)
        self.assertIn('完整线束尚未应用', current)
        self.config['reaction_clamp_entry']['enabled'] = False
        legacy = eval(code, context)
        self.assertIn('上部舵盘夹口初次装配和最终五金选型仍未完成', legacy)


if __name__ == '__main__':
    unittest.main()
