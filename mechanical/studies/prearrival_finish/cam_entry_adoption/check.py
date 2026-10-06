"""Check the saved adopted model against both baseline and independent candidate."""
from pathlib import Path
import json,sys,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,P
from validate import rigidtr

ctx=Context();started=time.time()
base=json.loads((OUT/'baseline.json').read_text())
assert P['revision']=='V1.2-M1.50'
actual={n:ctx.fingerprint(s) for n,s in ctx.ss.items()}
assert set(actual)==set(base['parts'])
changed=[n for n,h in actual.items() if h!=base['parts'][n]['fingerprint']]
assert changed==['CAM_Mainboard'],changed
s=ctx.ss['CAM_Mainboard'];o=s.o
rows=json.loads(o['component_reference_index'])
v=np.asarray([tuple(o.matrix_world@p.co) for p in o.data.vertices],float)
f=np.asarray([tuple(p.vertices) for p in o.data.polygons],np.int64)
before=np.load(OUT/'CAM_before.npz')
oldrows=json.loads((OUT/'CAM_before_index.json').read_text())
oldrows={r['reference']:r for r in oldrows}
study=ROOT/'mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/static_flex/connector_faces/correction'
candidate=np.load(study/'CAM_Mainboard_candidate.npz')
assert np.array_equal(f,candidate['triangles'])
candidate_error=float(np.max(np.abs(v-candidate['vertices_mm'])))
assert candidate_error<2e-5,candidate_error
assert len(rows)==len(oldrows)==132
refs=['CAMERA_FPC_24','DISPLAY_FPC_18']
def group(vertices,faces,row):
    a,b=row['vertices'];fa,fb=row['faces']
    vv=vertices[a:b];ff=(faces[fa:fb]-a).astype(np.uint64)
    assert ff.min()>=0 and ff.max()<len(vv)
    raw=manifold.Manifold(manifold.Mesh64(vv,ff))
    assert raw.status()==manifold.Error.NoError
    solid=manifold.Manifold.batch_boolean(raw.decompose(),manifold.OpType.Add)
    return vv,ff,solid
old={};new={};unchanged=[];changes=[]
for row in rows:
    name=row['reference']
    bv,bf,bm=group(before['vertices_mm'],before['triangles'],oldrows[name])
    nv,nf,nm=group(v,f,row);old[name]=bm;new[name]=nm
    if name not in refs:
        assert np.array_equal(bv,nv) and np.array_equal(bf,nf),name
        unchanged.append(name)
    else:
        bounderror=float(np.max(np.abs(np.array([bv.min(0),bv.max(0)])-np.array([nv.min(0),nv.max(0)]))))
        assert bounderror<2e-5,(name,bounderror)
        changes.append(dict(reference=name,old_volume_mm3=float(bm.volume()),new_volume_mm3=float(nm.volume()),
            added_volume_mm3=float((nm-bm).volume()),removed_volume_mm3=float((bm-nm).volume()),bound_error_mm=bounderror))
assert len(unchanged)==130
entry=json.loads(o['connector_entry_review'])
assert {r['reference']:r['entry_direction_uvw'] for r in entry['components']}=={
    'CAMERA_FPC_24':[0,1,0],'DISPLAY_FPC_18':[-1,0,0]}
sibling=[];failures=[];poses=[]
added={n:new[n]-old[n] for n in refs}
for ref,shape in added.items():
    for other,target in new.items():
        if other==ref:continue
        vol=float((shape^target).volume())
        row=dict(reference=ref,other=other,added_overlap_mm3=vol);sibling.append(row)
        if vol>1e-6:failures.append(row)
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        tr=np.asarray(rigidtr(yaw,pitch));ty=np.asarray(rigidtr(yaw,0));checks=0
        for ref,shape in added.items():
            moving=shape.transform(tr[:3,:]);points=np.asarray(moving.to_mesh64().vert_properties[:,:3]);lo=points.min(0);hi=points.max(0)
            for name,target in ctx.ss.items():
                if name=='CAM_Mainboard':continue
                move=tr if target.group=='pitch' else ty if target.group=='yaw' else None
                tv=target.v if move is None else target.v@move[:3,:3].T+move[:3,3]
                if np.any(lo>tv.max(0)) or np.any(hi<tv.min(0)):continue
                solid=target.m if move is None else target.m.transform(move[:3,:])
                vol=float((moving^solid).volume());checks+=1
                if vol>1e-7:failures.append(dict(yaw=yaw,pitch=pitch,reference=ref,part=name,new_overlap_mm3=vol))
        poses.append(dict(yaw=yaw,pitch=pitch,broadphase_checks=checks))
    print('CAM_ENTRY_MOTION',yaw,len(failures),flush=True)
ctx.assert_unchanged()
report=dict(status='FAIL' if failures else 'PASS',revision=P['revision'],
    scope='Exact adopted-package scope, original outline preservation and new-material interference only',
    sources=ctx.sources,baseline_main_sha256=base['sources']['mechanical/mori_v1_2.blend'],
    production_inputs={str(p.relative_to(ROOT)):sha(p) for p in [
        ROOT/'mechanical/scripts/waveshare_detail.py',ROOT/'mechanical/scripts/cam_fpc_entries.py',
        ROOT/'mechanical/scripts/common.py',ROOT/'mechanical/scripts/validate_cam_entry.py']},
    independent_candidate={str(p.relative_to(ROOT)):sha(p) for p in [study/'CAM_Mainboard_candidate.npz',study/'component_index.json',study/'review.json']},
    changed_native_parts=changed,unchanged_native_parts=len(actual)-len(changed),
    unchanged_CAM_components=unchanged,changes=changes,candidate_max_coordinate_error_mm=candidate_error,
    candidate_faces_equal=True,sibling_checks=sibling,poses=poses,failures=failures,
    entry_correction=entry,printed_geometry_change=False,hardware_source_change=False,
    exact_FPC_mating='BLOCKED',full_harness='BLOCKED',physical_validation='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert not failures,failures[:5]
print('CAM_ENTRY_ADOPTION_CHECK_PASS',len(actual)-1,len(unchanged),len(poses),len(sibling),flush=True)
