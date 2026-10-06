"""Independent pitch-side support screen; no main model or route changes."""
from pathlib import Path
PB_SCRIPT=Path(__file__).resolve();PB_A8=PB_SCRIPT.parent
PB_HELPER=PB_A8/'screen_CAM_anchor_support.py';__file__=str(PB_HELPER)
exec(compile(PB_HELPER.read_text().split('\nhost=ss[',1)[0],str(PB_HELPER),'exec'),globals())
__file__=str(PB_SCRIPT)
PB_OUT=PB_A8/'cam_pitch_anchor';PB_OUT.mkdir(exist_ok=True)
original_candidate=PB_A8/'cam_anchors/candidate_v3/cleaned'
def readsolid(p):
    a=np.load(p);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))
    assert m.status()==manifold.Error.NoError and m.volume()>0
    return m
source_solids={n:(s.group,s.m) for n,s in ss.items()}
source_solids['Pitch_Yoke']=('yaw',readsolid(original_candidate/'Pitch_Yoke.npz'))
source_solids['Yaw_Base']=('body',readsolid(original_candidate/'Yaw_Base.npz'))
source_solids['CAM_Tie_Head']=('yaw',readsolid(PB_A8/'cam_tie_install/oriented_head.npz'))
source_solids['CAM_Tie_Band']=('yaw',readsolid(PB_A8/'cam_tie_install/oriented_band.npz'))
host=source_solids['Display_Frame'][1]
wire_z=202.10000610351562
def prism_yz(poly,xmin,xmax):
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))
    if area<0:poly=poly[::-1]
    m=manifold.CrossSection([poly]).extrude(xmax-xmin).transform(np.array([[0,0,1,xmin],[1,0,0,0],[0,1,0,0]]))
    assert m.volume()>0 and len(m.decompose())==1
    return m
def screen(m):
    hits=[];count=0;nearest={'gap_mm':2.,'object':None}
    for pitch in range(-20,26,5):
        inverse=np.linalg.inv(np.array(rigidtr(0,pitch)))
        for name,(group,target) in source_solids.items():
            if name=='Display_Frame':continue
            for yaw in (range(-60,61,10) if group=='body' else [0]):
                mat=np.eye(4) if group=='pitch' else inverse
                if group=='body':mat=inverse@np.asarray(rigidtr(-yaw,0))
                obstacle=target.transform(mat[:3,:4]);count+=1
                if not overlap_boxes(m,obstacle,2.):continue
                volume=max(0.,float((m^obstacle).volume()))
                if volume>.001:
                    hits.append({'object':name,'pitch_deg':pitch,'yaw_deg':yaw,'volume_mm3':volume})
                    return {'status':'BLOCKED','checks':count,'hits':hits,'nearest':nearest}
                gap=float(m.min_gap(obstacle,2.))
                if gap<nearest['gap_mm']:nearest={'gap_mm':gap,'object':name,'pitch_deg':pitch,'yaw_deg':yaw}
                if gap<.3-1e-5:
                    hits.append({'object':name,'pitch_deg':pitch,'yaw_deg':yaw,'gap_mm':gap})
                    return {'status':'BLOCKED','checks':count,'hits':hits,'nearest':nearest}
    return {'status':'PASS','checks':count,'hits':hits,'nearest':nearest}
rows=[]
for rise,root_top in itertools.product([0.,.5,1.],[210.5,212.,213.5]):
    lo=float(xx.min()-1.2);hi=float(xx.max()+1.2)
    bed=box([lo,6.3,wire_z+.25],[hi,9.3,wire_z+3.25])
    grooves=manifold.Manifold.batch_boolean([
      manifold.Manifold.cylinder(4.,.35,circular_segments=64).rotate([90.,0.,0.]).translate([float(x),9.8,wire_z]) for x in xx],manifold.OpType.Add)
    bed=bed-grooves
    beam=prism_yz([[8.8,wire_z+1.+rise],[31.8,root_top-3.],[31.8,root_top],[8.8,wire_z+4.+rise]],lo,hi)
    addition=bed+beam
    root_overlap=max(0.,float((addition^host).volume()))
    joined=host+addition
    row={'parameters':{'rise_mm':rise,'root_top_z_mm':root_top},'root_overlap_mm3':root_overlap,
         'addition_volume_mm3':float(addition.volume()),'combined_components':len(joined.decompose())}
    row['source']=screen(addition) if root_overlap>1. and len(joined.decompose())==1 else {'status':'BLOCKED','reason':'root_or_connectivity'}
    row['status']=row['source']['status']
    idx=len(rows);cache(PB_OUT/f'trial_{idx}_addition.npz',addition)
    rows.append(row);print('PITCH_ANCHOR',idx,row,flush=True)
report={'status':'PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
        'scope':'Pitch support structural geometry versus source parts only; wire, tie, assembly, strength remain unchecked',
        'source_main_sha256':source_hash,'script_sha256':sha(PB_SCRIPT),'rows':rows,
        'main_applied':False,'whole_harness':'BLOCKED','wire_fit':'NOT_TESTED',
        'fastening_and_tie':'NOT_TESTED','physical_strength':'NOT_TESTED'}
(PB_OUT/'support_screen.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(source)==source_hash
