"""Normalize the independent candidate for assembly checks; main untouched."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];OUT=HERE/'p5r7_receipt'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,broad
from render import camera
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
candidate_source=Path(bpy.data.filepath);candidate_hash=hashlib.sha256(candidate_source.read_bytes()).hexdigest()
for o in list(bpy.context.scene.objects):
    if o.get('role')!='receipt_candidate':continue
    n=o.name.removeprefix(PREFIX+'RECEIPT_');old=bpy.data.objects.get(PREFIX+n)
    if old:
        old['role']='historical_reference';old.name=PREFIX+'P5R6_RETIRED_'+n;old.hide_render=True;old.hide_set(True)
    o.name=PREFIX+n;o['role']='part'
bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
# Locate residual E/header contact without changing the actual pin cross section.
core_data=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text());fit=json.loads((HERE/'p5r7_fit.json').read_text())
r=np.array(fit['core']['rotation']);t=np.array(fit['core']['translation_mm'])
residual=[]
for i,s in enumerate(core_data['solids']):
    if i in [32,159,160,161,162]:continue
    v=np.array(s['vertices_mm'])@r.T+t;m=manifold.Manifold(manifold.Mesh64(v,np.array(s['triangles'],dtype=np.uint64)))
    if m.status()!=manifold.Error.NoError:continue
    ov=m^ss['E_Straight_Header'].m
    if ov.volume()>.0001:residual.append(dict(vendor_solid=i,overlap_mm3=ov.volume(),bounds_mm=ov.bounding_box()))
print('E_RESIDUAL',residual,flush=True)
# All previously selected native connector placements unchanged except rearJ3.
prior=PROJECT/'mechanical/studies/prearrival_preparation';mr=json.loads((prior/'mated_connector_review.json').read_text())
with bpy.data.libraries.load(str(prior/'mated_connector_review.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(PREFIX+'PREARRIVAL_Plug_')]
for o in dst.objects:
    if o:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update();plugsolids={o.name.removeprefix(PREFIX+'PREARRIVAL_Plug_'):Solid(o) for o in dst.objects if o}
hand=json.loads((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_text())
def hits(m,fixture):
    bb=np.array(m.bounding_box());out=[]
    for n in fixture:
        s=ss[n]
        if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
        v=max(0,(m^s.m).volume())
        if v>.02:out.append(dict(part=n,overlap_mm3=v))
    return out
plugs=[]
for row in mr['rows']:
    key=row['board']+'_'+row['ref'];p=plugsolids[key];m=p.m;a=np.array(row['axis']);owner=P['native_electronics']['boards'][row['board']]['object']
    if key=='rear_J3':
        center=(p.lo+p.hi)/2;bb=hand['rear_J3']['nominal_screen']['plug_world_bounds_mm'];target=(np.array(bb[:3])+bb[3:])/2
        tr=Matrix.Translation(Vector(target))@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-Vector(center));m=m.transform(np.array(tr)[:3,:]);a=np.array([0.,0.,-1.])
    static=hits(m,set(ss)-{owner})
    fixture={n for n in ss if n in ['Load_Frame',owner] or n.startswith(('Carrier_','Socket_'))} if row['board']=='motion' else ({n for n in ss if n.startswith(('Body_Upper','Speaker','Rear_Interface','USB_','Power_Switch'))} if row['board']=='rear' else {n for n in ss if n=='Load_Frame'})
    fixture-={owner};path=[]
    for d in np.arange(0,12.01,.5):path.extend(dict(travel_mm=float(d),**h) for h in hits(m.translate((a*d).tolist()),fixture))
    plugs.append(dict(id=key,status='PASS' if not static and not path else 'BLOCKED',static_hits=static,bench_path_hits=path,bench_fixture=sorted(fixture),axis=a.tolist(),travel_mm=12,samples=25))
    if static or path:print('P5R7_PLUG',key,static[:2],path[:2],flush=True)
result=dict(candidate_sha256=candidate_hash,handoff_sha256=hashlib.sha256((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_bytes()).hexdigest(),E_pin_residual=residual,mated_plugs=plugs,status='BLOCKED' if residual or any(x['status']!='PASS' for x in plugs) else 'PASS',limits=['Residual source STEP hole versus straight pin must not be hidden by shrinking vendor interfaces.','Insertion fixture is recorded; no flexible leads or hand grip. All other mates preserve received same native footprints.'])
(OUT/'followthrough.json').write_text(json.dumps(result,indent=2)+'\n')
# The same accepted P5R6 body-shell sequence is recomputed with the new core,
# current B-side J3 and actual socket bodies/tails, preserving the old report.
script=HERE/'dual_body_sequence.py';code=script.read_text().replace("(HERE/'dual_body_sequence.json')","(HERE/'p5r7_receipt/dual_body_sequence.json')")
exec(compile(code,str(script),'exec'),{'__file__':str(script),'__name__':'p5r7_sequence_review'})
d=json.loads((OUT/'dual_body_sequence.json').read_text());d['candidate_sha256']=candidate_hash;d['hardware_revision']='P5R7';(OUT/'dual_body_sequence.json').write_text(json.dumps(d,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'p5r7_received_preview.blend'))
print('RECEIPT_FOLLOWTHROUGH_COMPLETE',flush=True)
