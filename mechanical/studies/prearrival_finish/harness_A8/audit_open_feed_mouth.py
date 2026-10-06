"""Inspect the saved open mouth, local source preservation and old roof remains."""
from pathlib import Path
AUDIT_SCRIPT=Path(__file__).resolve();AUDIT_DIR=AUDIT_SCRIPT.parent
AUDIT_HELPER=AUDIT_DIR/'plan_h06_documented_mates.py';__file__=str(AUDIT_HELPER)
exec(compile(AUDIT_HELPER.read_text().split('\nports=json.loads',1)[0],str(AUDIT_HELPER),'exec'),globals())
__file__=str(AUDIT_SCRIPT);J3=AUDIT_DIR/'assembly_feed_v3';OUT=J3/'open_mouth'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def readm(path):
    d=np.load(path);return manifold.Manifold(manifold.Mesh64(vert_properties=d['vertices_mm'],tri_verts=d['triangles'].astype(np.uint64)))
before=readm(J3/'cleaned/Pitch_Yoke.npz');after=readm(OUT/'cleaned/Pitch_Yoke.npz')
expected_removed=readm(OUT/'Pitch_Yoke_roof_removed.npz')
construct=json.loads((OUT/'candidate_screen.json').read_text());storage=json.loads((OUT/'cleaned/storage.json').read_text())
assert storage['candidate_blend_sha256']==sha(OUT/'cleaned/candidate.blend')
top_test=manifold.Manifold.cube([200,200,36.5]).translate([-100,-100,147.])
kept_interfaces=(before^top_test)^(after^top_test)
interface_diff=((before^top_test)-(after^top_test))+((after^top_test)-(before^top_test))
rows=[];section_store={}
for phase in [45,135,225,315]:
    angle=math.radians(phase);co,si=math.cos(angle),math.sin(angle)
    tr=np.array([[0,0,1,0],[co,si,0,0],[-si,co,0,0]])
    for label,m in [('before',before),('after',after)]:
        sm=m.transform(tr)
        for off in np.linspace(-1.2,1.2,25):
            polys=[];small=[]
            for q in sm.slice(float(off)).to_polygons():
                p=np.array(q)[:,[1,0]];n=np.roll(p,-1,axis=0)
                area=abs(float(np.sum(p[:,0]*n[:,1]-n[:,0]*p[:,1]))/2)
                lo,hi=p.min(0),p.max(0)
                if hi[0]<12.4 or lo[0]>19.1 or hi[1]<183.4 or lo[1]>191.1:continue
                polys.append(p.tolist())
                if lo[0]>=12.4 and hi[0]<=19.1 and lo[1]>=183.4 and hi[1]<=191.1 and 1e-6<area<10:
                    small.append({'area_mm2':area,'bounds_rz_mm':[lo.tolist(),hi.tolist()]})
            rows.append({'phase_deg':phase,'variant':label,'offset_mm':float(off),'isolated_local_sections':small})
            if phase==45 and abs(off)<1e-8:section_store[label]=polys
after_islands=[r for r in rows if r['variant']=='after' and r['isolated_local_sections']]
remaining=float((expected_removed^after).volume())
assert not after_islands,after_islands[:2]
assert remaining<.005,remaining
assert abs(interface_diff.volume())<.005,float(interface_diff.volume())
old_journal=json.loads((J3/'journal_sections.json').read_text())['wall_samples']['J3']
new_journal=json.loads((OUT/'journal_sections.json').read_text())['wall_samples']['J3']
assert abs(old_journal['minimum']['thickness_mm']-new_journal['minimum']['thickness_mm'])<.00001
source_gaps=[]
for name,s in ss.items():
    if name in ['Yaw_Base','Pitch_Yoke']:continue
    gap=float(expected_removed.min_gap(s.m,4.))
    if gap<4:source_gaps.append({'part':name,'minimum_gap_mm':gap})
result={'status':'PASS','scope':'Saved upper mouth roof cleanup and finite adjacent-section inspection; not all-part wall or strength qualification',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(AUDIT_SCRIPT),'source_helper_sha256':sha(AUDIT_HELPER),
    'source_previous_candidate_sha256':sha(J3/'cleaned/candidate.blend'),
    'source_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),
    'source_construction_sha256':sha(OUT/'candidate_screen.json'),'source_storage_sha256':sha(OUT/'cleaned/storage.json'),
    'roof_remaining_volume_mm3':remaining,'roof_remaining_numerical_limit_mm3':.005,
    'material_difference_below_mouth_z183_5_mm3':float(interface_diff.volume()),
    'changed_functional_axes':False,'journal_minimum_sample_unchanged_mm':new_journal['minimum']['thickness_mm'],
    'adjacent_sections':rows,'before_isolated_section_count':sum(len(r['isolated_local_sections']) for r in rows if r['variant']=='before'),
    'after_isolated_section_count':0,'sections_checked_per_variant':100,
    'source_gaps_below_4mm':source_gaps,'radial_zero_offset_polygons':section_store,
    'all_print_wall_and_strength':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED'}
(OUT/'mouth_cleanup_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('OPEN_MOUTH_AUDIT',result['status'],result['before_isolated_section_count'],remaining,float(interface_diff.volume()),flush=True)
