"""Run in a background Blender to prove rebuild idempotence and ownership isolation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build
from common import *
scene=bpy.data.scenes.get('MORI_Assembly') or bpy.data.scenes.new('MORI_Assembly')
sentinel=bpy.data.objects.new('REBUILD_TEST_UNRELATED_OBJECT',None); scene.collection.objects.link(sentinel)
sentinel['verification_only']=True; sentinel['keep_value']='preserved'; sentinel.hide_render=True
original_nonowned={o.name for o in bpy.data.objects if o.get('mori_owner')!=OWNER}
records=[]
for iteration in [1,2]:
    build.main()
    owned=[o for o in bpy.context.scene.objects if o.get('mori_owner')==OWNER]
    records.append(dict(iteration=iteration,tagged_objects=len(owned),part_count=len(parts()),candidate_count=len([o for o in parts(True) if o.get('export_candidate')]),
                        owned_names=sorted(o.name for o in owned),unrelated_preserved=all(n in bpy.data.objects for n in original_nonowned)))
same=records[0]['owned_names']==records[1]['owned_names'] and records[0]['part_count']==records[1]['part_count']
ok=same and all(r['unrelated_preserved'] for r in records) and sentinel.get('keep_value')=='preserved'
result=dict(status='PASS' if ok else 'FAIL',runs=records,sentinel_survived=True,method='Same process, two build.main calls; exact generated object names/counts and an unrelated sentinel checked.')
save_json(ROOT/'reports/rebuild_check.json',result)
bpy.data.objects.remove(sentinel,do_unlink=True)
assembled(); bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/MORI_assembly.blend'))
if not ok: raise RuntimeError('Rebuild isolation failed')
print('MORI REBUILD CHECK PASS',flush=True)
