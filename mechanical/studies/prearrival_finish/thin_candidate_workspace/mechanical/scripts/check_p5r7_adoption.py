"""Independent received-candidate, numbered-pin and unchanged-print audit."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from native_electronics import board_transform
load_collections();assembled();bpy.context.view_layer.update()
q=P['p5r7_adoption'];old=json.loads((PROJECT/q['baseline_geometry']).read_text())
now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
changed=sorted(n for n in old['parts'] if n in now and old['parts'][n]!=now[n])
added=sorted(set(now)-set(old['parts']));retired=sorted(set(old['parts'])-set(now))
printed=[n for n,x in old['parts'].items() if x['category']=='PRINTABLE']
print_changed=[n for n in printed if now.get(n)!=old['parts'][n]]
scopeok=set(changed)==set(q['changed_existing_ids']) and set(added)==set(q['new_ids']) and not retired and not print_changed
hand=json.loads((PROJECT/q['handoff']).read_text());build=json.loads((ROOT/'reports/p5r7_adoption_build.json').read_text())
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
candidate=ROOT/'studies/prearrival_closure/p5r7_receipt';comparisons=[]
for n in q['changed_existing_ids']+q['new_ids']:
    d=json.loads((candidate/('solid_'+n+'.json')).read_text())
    m=manifold.Manifold(manifold.Mesh64(np.array(d['vertices_mm']),np.array(d['triangles'],dtype=np.uint64)))
    a=ss[n].m;delta=max(0,(m-a).volume())+max(0,(a-m).volume())
    comparisons.append(dict(id=n,symmetric_difference_mm3=delta))
inv=json.loads((PROJECT/P['native_electronics']['inventory']).read_text())
module=next(x for x in inv['boards']['motion']['footprints'] if x['reference']=='U100')
r,t=board_transform('motion');pads={x['number']:(r@np.array([x['xy_mm'][0],-x['xy_mm'][1],0])+t)[:2] for x in module['pads']}
audit=json.loads((PROJECT/'hardware/v1_2/reviews/weact_E_J3_20260930/weact_alignment_audit.json').read_text())
pinrows=[dict(pin=x['pin'],error_mm=float(np.linalg.norm(pads[x['pin']]-x['world_xy_mm']))) for x in audit['rows']]
source=json.loads((PROJECT/q['weact']['source_mesh']).read_text());rotation=np.array(hand['weact_assembly']['core_STEP_to_robot_rotation']);translation=np.array(build['core']['translation_mm'])
assert np.linalg.det(rotation)==1
core=ss['MCU_Motion'].o;refs={x['reference']:x for x in json.loads(core['component_reference_index'])};vertices=np.array([tuple(x) for x in vertices_world(core)]);errors=[]
for i,s in enumerate(source['solids']):
    if i==32:continue
    v=np.array(s['vertices_mm'])
    if i in [159,160,161,162]:
        cy=(v[:,1].min()+v[:,1].max())/2
        v=v@np.diag([1.,-1.,-1.])+[0,2*cy,-build['core']['vendor_substrate_thickness_mm']]
    v=v@rotation.T+translation;lo,hi=refs['VENDOR_'+str(i)]['vertices']
    errors.append(float(np.max(np.abs(v-vertices[lo:hi]))))
overlap=max(0,(ss['MCU_Motion'].m^ss['E_Straight_Header'].m).volume())
from p5r7_adoption import known_source_pair
sourcechecks=[]
for key in ['handoff','addendum']:
    sourcechecks.append(dict(path=q[key],unchanged=hashlib.sha256((PROJECT/q[key]).read_bytes()).hexdigest()==q[key+'_sha256']))
for kind,c in inv['boards'].items():
    sourcechecks.append(dict(path=c['source'],unchanged=hashlib.sha256((PROJECT/c['source']).read_bytes()).hexdigest()==c['source_sha256']))
ok=scopeok and max(x['symmetric_difference_mm3'] for x in comparisons)<.02 and len(pinrows)==68 and max(x['error_mm'] for x in pinrows)<.001 and max(errors)<.001 and len(refs)==223 and all(x['unchanged'] for x in sourcechecks) and known_source_pair('MCU_Motion','E_Straight_Header',overlap)
out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),adoption_status='PASS' if ok else 'FAIL',full_mated_fit='BLOCKED',scope=dict(changed=changed,added=added,retired=retired,print_changed=print_changed,printed_objects_checked=len(printed)),independent_candidate_comparison=comparisons,numbered_pins=pinrows,retained_vendor_solids=len(refs),max_source_vertex_error_mm=max(errors),sources=sourcechecks,E_source_discrepancy=dict(status='BLOCKED',overlap_mm3=overlap,action='Preserved original STEP holes and nominal pins; await finished-hole and matched-header evidence.'),limits=q['limits'])
save_json(ROOT/'reports/p5r7_adoption_validation.json',out)
print('P5R7_ADOPTION_AUDIT',out['adoption_status'],out['scope'],'E overlap',overlap,flush=True)
assert ok,out
