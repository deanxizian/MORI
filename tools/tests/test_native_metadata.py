import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('native_metadata',Path(__file__).resolve().parents[2]/'hardware/v1_2/tools/sync_native_metadata.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class NativeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        folder=self.root/'hardware/v1_2/native_projects';folder.mkdir(parents=True)
        projects=[]
        for name in ('one_P1','two_P1'):
            base=f'hardware/v1_2/kicad/{name}';directory=self.root/base;directory.mkdir(parents=True)
            meta=base+'/connectivity.json';board=base+'/'+name+'.kicad_pcb'
            data={meta:json.dumps({'components':[{'ref':'R1','at':[0,0]}]}).encode(),board:b'(kicad_pcb (footprint "R" (layer "F.Cu") (at 2 3) (property "Reference" "R1")))'}
            (self.root/meta).write_bytes(data[meta]);archive=f'hardware/v1_2/native_projects/{name}.zip'
            with zipfile.ZipFile(self.root/archive,'w') as z:
                for key,value in data.items():z.writestr(key,value)
            projects.append({'project':name,'archive':archive,'files':[{'path':p} for p in data]})
        (folder/'manifest.json').write_text(json.dumps({'projects':projects}))
    def files(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.state' not in p.parts}
    def test_later_project_failure_never_changes_any_archive(self):
        before=self.files();original=module.placements;calls=0
        def failure(data):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('simulated disk/parse failure in second project')
            return original(data)
        with patch.object(module,'placements',failure),self.assertRaises(OSError):module.update(self.root)
        self.assertEqual(before,self.files())
    def test_publication_failure_rolls_back_all_files(self):
        before=self.files();original=module.atomic_bytes;failed=False
        def failure(path,data):
            nonlocal failed
            if path.name=='manifest.json' and not failed:
                failed=True;raise OSError('interruption before final manifest')
            return original(path,data)
        with patch.object(module,'atomic_bytes',failure),self.assertRaises(OSError):module.update(self.root)
        self.assertEqual(before,self.files())
        module.update(self.root);after=self.files();module.update(self.root)
        self.assertEqual(after,self.files())
        for p in (self.root/'hardware/v1_2/native_projects').glob('*.zip'):
            with zipfile.ZipFile(p) as z:self.assertIsNone(z.testzip())

if __name__=='__main__':unittest.main()
