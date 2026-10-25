"""Regressions for repeated metadata runs and portable M1.58 inputs."""
import ast
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT/'mechanical/scripts'
sys.path.insert(0, str(SCRIPTS))
from reference_provenance import evaluated_dock_reference, historical_hardware_provenance


class CurrentMechanicalReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads((ROOT/'config/geometry.json').read_text())

    def write(self, name, data):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return path

    def test_metadata_repeated_runs_preserve_one_historical_schedule(self):
        mechanical = self.root/'mechanical'
        model = self.write('mechanical/model.blend', {'fake geometry': 1})
        initial = json.loads((ROOT/'mechanical/reports/module_assembly.json').read_text())
        common = ModuleType('common')
        common.__dict__.update(ROOT=mechanical, P=self.config, PREFIX='MORI_V1__', json=json,
            bpy=SimpleNamespace(context=SimpleNamespace(window=SimpleNamespace()),
                data=SimpleNamespace(scenes={'MORI_V1_Assembly': object()}, filepath=str(model))),
            load_collections=lambda: None, assembled=lambda: None, parts=lambda: [],
            save_json=lambda p, data: p.write_text(json.dumps(data)))
        structure = ModuleType('structural_simplification')
        structure.volume = lambda o: 0
        # Both freshly emitted construction metadata and the committed wrapper
        # must survive a second run without nesting or losing current mounts.
        for plan in [initial['historical_construction_schedule'], initial]:
            self.write('mechanical/reports/module_assembly.json', plan)
            self.write('mechanical/reports/structure_changes.json', {'before': {'retained': True}})
            path = mechanical/'reports/module_assembly.json'
            with patch.dict(sys.modules, {'common': common, 'structural_simplification': structure}):
                runpy.run_path(str(SCRIPTS/'finalize_structure_metadata.py'))
                first = json.loads(path.read_text())
                runpy.run_path(str(SCRIPTS/'finalize_structure_metadata.py'))
            self.assertEqual(first, json.loads(path.read_text()))
            self.assertEqual(first['current_controls'], 'reports/ups_controls_geometry.json')
            old = first['historical_construction_schedule']
            self.assertNotIn('historical_construction_schedule', old)
            drive = {n.removesuffix('_Nut') for n in self.config['assembly_issue_fixes']['drive_nuts']['ids']}
            selected = [j for j in old['joints'] if j['id'] in drive]
            self.assertEqual(len(selected), len(drive))
            self.assertTrue(all(j['head_height_mm'] == 1.4 for j in selected))

    def test_animation_assigns_current_switch_and_retains_legacy_branches(self):
        tree = ast.parse((SCRIPTS/'assembly_animation.py').read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        branch = next(n for n in main.body if isinstance(n, ast.If)
                      and isinstance(n.test, ast.Name) and n.test.id == 'UPS_CONTROLS')
        code = compile(ast.Module(body=[branch], type_ignores=[]), '<actual rear assignments>', 'exec')
        switch_ids = set(self.config['ups_rear_controls']['reference_ids'])
        legacy_ids = {'Rear_Interface_PCB', 'USB_Receptacle', 'Rear_Interface_Screw_0', 'Rear_Interface_Screw_1'}
        for enabled, off_shelf, available in [(True, True, switch_ids),
                (False, True, legacy_ids), (False, False, legacy_ids|{'Power_Switch'})]:
            assigned = {}
            def assign(ids, step, offset=(0,0,0), **kwargs):
                for name in ids:
                    self.assertIn(name, available)
                    self.assertNotIn(name, assigned)
                    assigned[name] = (step, offset, kwargs['parent'])
            def select(*, prefix):
                return sorted(n for n in available if n.startswith(prefix))
            exec(code, dict(P=self.config, UPS_CONTROLS=enabled, OFF_SHELF=off_shelf,
                            assign=assign, select=select))
            self.assertEqual(set(assigned), available)
            self.assertTrue(all(row[0] == 15 and row[2] == 'Rear_Shell' for row in assigned.values()))
            if enabled:
                self.assertTrue(all(row[1] == (0,0,0) for row in assigned.values()))

    def dock_receipt(self, source):
        dock = dict(source_file=str(source), source_file_sha256=hashlib.sha256(b'source').hexdigest(),
                    preserved_main_sha256='main', matrices={'Parking_Cradle': [[1,0,0,0]]})
        path = self.write('mechanical/input_assets/off_shelf_M1_56/evaluated_dock_reference.json', dock)
        self.write('mechanical/input_assets/m1_58_manifest.json', {'files': [dict(
            path=path.relative_to(self.root).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())]})
        return path

    def test_absolute_source_is_not_read_or_claimed_verified(self):
        path = self.dock_receipt('/not-published/author/comparison.blend')
        dock, provenance = evaluated_dock_reference(self.root, path, 'main')
        self.assertIn('Parking_Cradle', dock['matrices'])
        self.assertEqual(provenance['status'], 'BLOCKED')

    def test_available_portable_source_is_checked_and_corruption_rejected(self):
        source = self.root/'comparison.blend'
        source.write_bytes(b'source')
        path = self.dock_receipt('comparison.blend')
        self.assertEqual(evaluated_dock_reference(self.root, path, 'main')[1]['status'], 'PASS')
        source.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'source hash'):
            evaluated_dock_reference(self.root, path, 'main')
        source.unlink()
        self.assertEqual(evaluated_dock_reference(self.root, path, 'main')[1]['status'], 'BLOCKED')

    def test_changed_matrix_receipt_and_wrong_main_are_rejected(self):
        path = self.dock_receipt('/not-published/comparison.blend')
        with self.assertRaisesRegex(ValueError, 'different main'):
            evaluated_dock_reference(self.root, path, 'wrong main')
        dock = json.loads(path.read_text())
        dock['matrices']['Parking_Cradle'][0][3] = 100
        path.write_text(json.dumps(dock))
        with self.assertRaisesRegex(ValueError, 'published input'):
            evaluated_dock_reference(self.root, path, 'main')

    def test_missing_or_different_historical_hardware_never_passes(self):
        path = self.root/'old-board.txt'
        path.write_bytes(b'old')
        expected = {'old-board.txt': hashlib.sha256(b'old').hexdigest()}
        self.assertEqual(historical_hardware_provenance(self.root, expected)['status'], 'PASS')
        path.write_bytes(b'current owner design')
        result = historical_hardware_provenance(self.root, expected)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['different_files'], ['old-board.txt'])
        path.unlink()
        result = historical_hardware_provenance(self.root, expected)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['missing_files'], ['old-board.txt'])


if __name__ == '__main__':
    unittest.main()
