import contextlib,hashlib,importlib.util,io,json,tempfile,unittest,warnings,zipfile
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('legacy_delivery',Path(__file__).resolve().parents[2]/'software/scripts/verify_delivery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class LegacyArchiveTests(unittest.TestCase):
    def test_exact_members_reject_extra_missing_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sources=root/'reference_sources';sources.mkdir()
            for v in ('0.3','0.4'):
                (sources/f'HW-SW-{v}_baseline_manifest.json').write_text(json.dumps({'sha256':{'source.txt':hashlib.sha256(b'good').hexdigest()}}))
                with zipfile.ZipFile(sources/f'HW-SW-{v}_firmware_baseline.zip','w') as z:z.writestr('source.txt',b'good')
            with patch.object(module,'SW',root),contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(module.verify_archives())
                path=sources/'HW-SW-0.4_firmware_baseline.zip'
                for members in [[('source.txt',b'good'),('extra.txt',b'unverified')],[('extra.txt',b'unverified')],[('source.txt',b'good'),('source.txt',b'good')]]:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        with zipfile.ZipFile(path,'w') as z:
                            for name,data in members:z.writestr(name,data)
                    self.assertFalse(module.verify_archives())
                path.write_bytes(b'corrupt ZIP')
                self.assertFalse(module.verify_archives())

if __name__=='__main__':unittest.main()
