import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import restore_m1_55_evidence as restore


class EvidenceRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)/'source'
        self.source.mkdir()
        self.root = Path(self.temp.name)/'destination'
        self.manifest = {'groups': {}}

    def group(self, name, payloads):
        bundle = self.source/(name+'.zip')
        with zipfile.ZipFile(bundle, 'w') as z:
            for member, data in payloads.items():
                z.writestr(member, data)
        digest = restore.archive.digest(bundle)
        self.manifest['groups'][name] = {
            'archive': bundle.name, 'sha256': digest,
            'files': [dict(path=member, member=member, bytes=len(data),
                           sha256=hashlib.sha256(data).hexdigest(), storage='LOCAL_ZIP',
                           archive=bundle.name, archive_sha256=digest)
                      for member, data in payloads.items()]}

    def run_restore(self, *groups):
        return restore.restore_groups(self.manifest, groups, self.root, self.source)

    def test_late_ancestor_file_aborts_before_any_output(self):
        self.group('test', {'first/new.txt': b'new', 'mechanical/revisions/later.txt': b'later'})
        blocked = self.root/'mechanical/revisions'
        blocked.parent.mkdir(parents=True)
        blocked.write_bytes(b'user work')
        with self.assertRaisesRegex(ValueError, 'Non-directory ancestor'):
            self.run_restore('test')
        self.assertEqual(blocked.read_bytes(), b'user work')
        self.assertEqual([p for p in self.root.rglob('*') if p.is_file()], [blocked])
        self.assertFalse((self.root/'first').exists())

    def test_ancestor_file_above_missing_root_is_preflighted(self):
        self.group('test', {'a.txt': b'a'})
        self.root.write_bytes(b'root is a file')
        self.root = self.root/'missing'/'root'
        with self.assertRaisesRegex(ValueError, 'Non-directory ancestor'):
            self.run_restore('test')

    def test_each_zip_is_hashed_and_opened_once_for_many_members(self):
        self.group('a', {f'a/{i}.txt': bytes([i]) for i in range(40)})
        self.group('b', {f'b/{i}.txt': bytes([i]) for i in range(40)})
        with patch.object(restore.archive, 'digest', wraps=restore.archive.digest) as digest, \
             patch.object(restore.zipfile, 'ZipFile', wraps=zipfile.ZipFile) as opened:
            result = self.run_restore('a', 'b', 'a')
        self.assertEqual(len(result), 80)
        self.assertEqual(digest.call_count, 2)
        self.assertEqual(opened.call_count, 2)
        stamps = {p: p.stat().st_mtime_ns for p in self.root.rglob('*.txt')}
        self.assertTrue(all(status == 'already present' for status, _ in self.run_restore('a', 'b')))
        self.assertTrue(all(p.stat().st_mtime_ns == stamp for p, stamp in stamps.items()))

    def test_selected_file_cannot_also_be_a_directory(self):
        self.group('test', {'first.txt': b'first', 'nested': b'file', 'nested/last.txt': b'last'})
        with self.assertRaisesRegex(ValueError, 'also a destination directory'):
            self.run_restore('test')
        self.assertFalse(self.root.exists())

    def test_different_existing_file_and_internal_symlink_are_preserved(self):
        self.group('test', {'first.txt': b'new', 'sub/file.txt': b'new'})
        (self.root/'sub').mkdir(parents=True)
        target = self.root/'sub/file.txt'
        target.write_bytes(b'user')
        with self.assertRaisesRegex(ValueError, 'Existing file differs'):
            self.run_restore('test')
        self.assertFalse((self.root/'first.txt').exists())
        self.assertEqual(target.read_bytes(), b'user')
        (self.root/'alias').symlink_to(self.root/'sub', target_is_directory=True)
        self.group('link', {'alias/new.txt': b'new'})
        with self.assertRaisesRegex(ValueError, 'Symlink ancestor'):
            self.run_restore('link')
        self.assertFalse((self.root/'sub/new.txt').exists())

    def test_bad_member_hash_cleans_temp_and_does_not_publish(self):
        self.group('test', {'a.txt': b'new'})
        self.manifest['groups']['test']['files'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'Member SHA256'):
            self.run_restore('test')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_exclusive_publication_preserves_concurrent_file(self):
        self.group('test', {'a.txt': b'new'})
        original_link = restore.os.link
        def racing_link(source, target):
            target.write_bytes(b'concurrent user work')
            return original_link(source, target)
        with patch.object(restore.os, 'link', side_effect=racing_link), self.assertRaises(FileExistsError):
            self.run_restore('test')
        self.assertEqual((self.root/'a.txt').read_bytes(), b'concurrent user work')
        self.assertFalse(list(self.root.glob('.mori-evidence-*')))


if __name__ == '__main__':
    unittest.main()
