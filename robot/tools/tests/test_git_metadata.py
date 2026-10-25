import sys,subprocess,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from git_metadata import project_git

class GitMetadataTests(unittest.TestCase):
    def test_source_zip_without_git(self):
        with tempfile.TemporaryDirectory() as path:
            result=project_git(path)
            self.assertEqual(result['status'],'NOT_APPLICABLE');self.assertIsNone(result['head']);self.assertIsNone(result['dirty'])
    def test_real_worktree_and_nested_unpacked_bundle(self):
        with tempfile.TemporaryDirectory() as path:
            subprocess.run(['git','init','-q',path],check=True)
            subprocess.run(['git','-C',path,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-m','Fixture','-q'],check=True)
            self.assertEqual(project_git(path)['status'],'PASS');self.assertFalse(project_git(path)['dirty'])
            nested=Path(path)/'unpacked';nested.mkdir()
            self.assertEqual(project_git(nested)['status'],'NOT_APPLICABLE')
            (nested/'changed.txt').write_text('test')
            self.assertTrue(project_git(path)['dirty'])
    def test_missing_git_does_not_abort_reporting(self):
        with patch('git_metadata.subprocess.run',side_effect=FileNotFoundError('no git')):
            self.assertEqual(project_git(Path.cwd())['status'],'NOT_APPLICABLE')

    def test_registered_project_retains_git_provenance_but_unpacked_directory_does_not(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            subprocess.run(['git','init','-q',path],check=True)
            subprocess.run(['git','-C',path,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-m','Fixture','-q'],check=True)
            project=root/'robot';project.mkdir()
            (project/'version.json').write_text('{}')
            (root/'projects.json').write_text(json.dumps({'projects':[{'path':'robot','manifest':'robot/version.json'}]}))
            self.assertEqual(project_git(project)['status'],'PASS')
            unregistered=project/'unpacked';unregistered.mkdir()
            self.assertEqual(project_git(unregistered)['status'],'NOT_APPLICABLE')

if __name__=='__main__':unittest.main()
