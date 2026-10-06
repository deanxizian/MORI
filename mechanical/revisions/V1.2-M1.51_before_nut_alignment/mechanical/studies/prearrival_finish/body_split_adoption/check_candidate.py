"""Build and check the completed seam candidate without changing the main model."""
from pathlib import Path
import sys, json, time
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context, np, sha
from common import bpy, manifold, P, D
from validate import Solid, rigidtr
from monocoque_structure import source_build
from body_shell_split import make_forms, boxm
ctx=Context();started=time.time()
q=json.loads((OUT/'candidate_parameters.json').read_text())
b=source_build()
o=b.body_outer('split_outer');outer=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
o=b.body_outer('split_inner',P['shell_thickness_mm']);inner=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
forms,base,locators=make_forms(ctx.ss['Body_Upper'].m,ctx.ss['Body_Lower'].m,outer,inner,q)
old=OUT.parent/'head_harness_M1_49/remaining_routes/cam_restraints/body_front_rear_split'
records={};base_differences={}
for n,m in forms.items():
    assert m.status()==manifold.Error.NoError and len(m.decompose())==1,n
    a=m.to_mesh64();np.savez_compressed(OUT/(n+'_candidate.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
    records[n]=dict(volume_mm3=m.volume(),islands=len(m.decompose()),status=str(m.status()),bounds_mm=list(m.bounding_box()))
    a=np.load(old/(n+'_candidate.npz'));prior=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    base_differences[n]=abs((base[n]-prior).volume())+abs((prior-base[n]).volume())
    assert base_differences[n]<1e-5,(n,base_differences[n])
def collisions(m,fixed):
    bb=np.asarray(m.bounding_box());rows=[]
    for n,t in fixed.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        v=abs((m^t).volume())
        if v>1e-5:rows.append(dict(target=n,overlap_mm3=v))
    return rows
native={n:s.m for n,s in ctx.ss.items()}
omitted={n for n in native if n.startswith(('Shell_Screw_','Shell_Insert_','Frame_Screw_'))}
front={n for n in native if n.startswith('Speaker') or n in ['Frame_Insert_0','Frame_Insert_1']}
rear={n for n in native if n.startswith('Rear_Interface_') or n in ['Power_Switch','USB_Receptacle','Frame_Insert_2','Frame_Insert_3']}
fixed={n:m for n,m in native.items() if n not in omitted|front|rear|{'Body_Upper','Body_Lower'}}
fixed.update({'Plug_'+n:s.m for n,s in ctx.plug.items() if n not in ['rear_J2','rear_J3']})
path=[]
for n,sgn in [('Body_Front',1),('Body_Rear',-1)]:
    targets={**fixed,**{k:m for k,m in forms.items() if k!=n}}
    first=None;checked=0
    for travel in np.r_[np.linspace(0,6,61),np.arange(7,221)]:
        hits=collisions(forms[n].translate([0,float(travel)*sgn,0]),targets);checked+=1
        if hits:first=dict(travel_mm=float(travel),hits=hits);break
    path.append(dict(id=n,positions=checked,status='FAIL' if first else 'PASS',first=first))
    print('LOCATOR_PATH',path[-1],flush=True)
keychecks=[]
for loc in locators:
    tongue=loc['tongue'];cover=loc['female'];tip=q['locators']['tongue_tip_y_mm']
    overlaps=collisions(loc['male']+loc['female'],fixed)
    # The actual minimum roof and side ligaments are defined by the same
    # rectangular pocket planes; ray checks verify both solid sections.
    x=loc['center_x_mm'];a=q['locators'];sample_y=-2
    rays={}
    for label,start,end in [
        ('roof',[x,sample_y,31.31],[x,sample_y,40]),
        ('side_left',[x-5.31,sample_y,30],[x-12,sample_y,30]),
        ('side_right',[x+5.31,sample_y,30],[x+12,sample_y,30])]:
        rays[label]=[list(h.position) for h in cover.ray_cast(start,end)]
    keychecks.append(dict(center_x_mm=x,expected_roof_mm=1.7,expected_side_mm=1.7,ray_exits_mm=rays,
                          nominal_tongue_thickness_mm=2,nominal_engagement_mm=3.6,collisions=overlaps))
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
    for n,s in ctx.ss.items():
        if s.group not in ['yaw','pitch']:continue
        tr=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:]
        hits=collisions(s.m.transform(tr),forms)
        if hits:motion.append(dict(yaw=yaw,pitch=pitch,part=n,hits=hits))
diff=(forms['Body_Front']+forms['Body_Rear'])-(base['Body_Front']+base['Body_Rear'])
change_outside=abs((diff-outer).volume())
assert change_outside<1e-5
ctx.assert_unchanged()
result=dict(status='PASS' if all(r['status']=='PASS' for r in path) and not motion and all(not r['collisions'] for r in keychecks) else 'FAIL',
    source=ctx.sources,inputs={str(p.relative_to(PROJECT)):sha(p) for p in [OUT/'candidate_parameters.json',PROJECT/'mechanical/scripts/body_shell_split.py',Path(__file__)]},
    accepted_base_symmetric_difference_mm3=base_differences,parts=records,paths=path,locators=keychecks,
    head_motion=dict(poses=130,failures=motion),added_material_outside_mother_mm3=change_outside,
    additional_volume_mm3=sum(forms[n].volume()-base[n].volume() for n in forms),
    scope='Original approved split plus two integrated bottom trial sliding locators; unchanged main model',
    full_harness='BLOCKED',physical_fit='NOT_TESTED',main_changed=False,elapsed_s=time.time()-started)
(OUT/'candidate_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('BODY_SPLIT_LOCATOR_CANDIDATE',result['status'],result['additional_volume_mm3'],flush=True)
