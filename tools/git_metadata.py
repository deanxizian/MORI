"""Git provenance is optional for an extracted source bundle."""
import pathlib
import subprocess

def project_git(root):
    root=pathlib.Path(root).resolve();records=[]
    def run(*args):
        command=['git',*args]
        try:
            result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=10)
            records.append({'command':command,'exit_code':result.returncode,'output':(result.stdout+result.stderr).strip()})
            return result.stdout.strip() if result.returncode==0 else None
        except (OSError,subprocess.TimeoutExpired) as error:
            records.append({'command':command,'exit_code':None,'error':str(error)});return None
    top=run('rev-parse','--show-toplevel')
    # A ZIP extracted inside another repository must not inherit its identity.
    if top is None or pathlib.Path(top).resolve()!=root:
        return {'status':'NOT_APPLICABLE','head':None,'dirty':None,'scope':'No Git worktree rooted at this source bundle','commands':records}
    head=run('rev-parse','HEAD');status=run('status','--porcelain=v1')
    return {'status':'PASS' if head is not None and status is not None else 'NOT_APPLICABLE','head':head,'dirty':bool(status) if status is not None else None,'scope':'Actual local worktree at report time','commands':records}
