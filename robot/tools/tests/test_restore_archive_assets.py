import importlib.util
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('restore',Path(__file__).resolve().parents[1]/'restore_archive_assets.py')
restore=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(restore)

class RestoreTests(unittest.TestCase):
    def test_verified_local_archive_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'inputs.zip';payload=b'official model bytes'
            with zipfile.ZipFile(bundle,'w') as z:z.writestr('mesh.json',payload)
            entry={'storage':'LOCAL_ZIP','path':'sources/mesh.json','archive':'inputs.zip','archive_sha256':restore.digest(bundle),'member':'mesh.json','sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
            with patch.object(restore,'DEFAULT_ROOT',root):
                self.assertEqual(restore.restore(root,entry),'restored')
                self.assertEqual(restore.restore(root,entry),'already present')
                target=root/entry['path'];target.write_bytes(b'user changes')
                with self.assertRaises(FileExistsError):restore.restore(root,entry)
                self.assertEqual(target.read_bytes(),b'user changes')
                target.unlink();bad=dict(entry,sha256='0'*64)
                with self.assertRaises(ValueError):restore.restore(root,bad)
                self.assertFalse(target.exists())
                self.assertFalse(list(target.parent.glob('.mori-download-*')))
                with self.assertRaises(ValueError):restore.restore(root,dict(entry,archive_sha256='0'*64))
    def test_paths_and_symlinks_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            root=Path(a);(root/'outside').symlink_to(b,target_is_directory=True)
            for name in ['../escape','/absolute','outside/escape']:
                with self.subTest(name=name),self.assertRaises(ValueError):restore.destination(root,name)
            (root/'link').symlink_to(root/'missing')
            with self.assertRaises(ValueError):restore.destination(root,'link')

if __name__=='__main__':unittest.main()
