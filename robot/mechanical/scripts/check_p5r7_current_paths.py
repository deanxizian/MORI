"""Recompute received P5R7 plug/service checks on current saved main model.

Reuse the reviewed inspection algorithms, redirecting their reports only.
Do not overwrite the independent candidate or the current .blend.
"""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);sourcehash=hashlib.sha256(source.read_bytes()).hexdigest()
HERE=ROOT/'studies/prearrival_closure';OUT=ROOT/'reports/p5r7_current';OUT.mkdir(exist_ok=True)
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
candidate_hash=sourcehash
code=(HERE/'p5r7_followthrough.py').read_text().split('# Locate residual E/header contact')[1].split('\n',1)[1].split('# The same accepted')[0]
code=code.replace("json.loads((HERE/'p5r7_fit.json').read_text())","json.loads((ROOT/'reports/p5r7_adoption_build.json').read_text())")
exec(compile(code,str(HERE/'p5r7_followthrough.py'),'exec'),globals())
code=(HERE/'p5r7_service.py').read_text().split('# Three current-source views')[0]
code=code.replace("json.loads((HERE/'p5r7_fit.json').read_text())","json.loads((PROJECT/'mechanical/reports/p5r7_adoption_build.json').read_text())")
code=code.replace("(HERE/'p5r7_receipt/service.json')","(PROJECT/'mechanical/reports/p5r7_current/service.json')")
exec(compile(code,str(HERE/'p5r7_service.py'),'exec'),{'__file__':str(HERE/'p5r7_service.py'),'__name__':'current_service'})
for name in ['followthrough','service']:
    p=OUT/(name+'.json');d=json.loads(p.read_text());d.pop('candidate_sha256',None);d['source_main_sha256']=sourcehash;d['revision']=P['revision'];d['scope_current_main']=True;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==sourcehash
print('P5R7_CURRENT_PATHS_COMPLETE',flush=True)
