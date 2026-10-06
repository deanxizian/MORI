"""Saved-main checks for the approved body split. No mesh is changed."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,manifold,P,D,save_json
from interface_completion import axial
ctx=Context();started=time.time()
q=P['body_front_rear_split'];snapshot=ROOT/q['baseline']
prior=json.loads((OUT/'seam_space.json').read_text())
old=prior['native_fingerprints'];now=ctx.print_fingerprints
retired={'Body_Upper','Body_Lower'}|{f'{stem}{i}' for stem in ['Shell_Screw_','Shell_Insert_'] for i in range(4)}
new_ids={'Body_Front','Body_Rear'}
changed=[n for n in set(old)&set(now) if old[n]!=now[n]]
assert not changed,changed
assert set(old)-set(now)==retired and set(now)-set(old)==new_ids
oldp=json.loads((snapshot/'config/geometry.json').read_text());current=json.loads(json.dumps(P))
oldp.pop('revision');current.pop('revision');current.pop('body_front_rear_split')
assert oldp==current,'Unexpected geometry settings'
prep=json.loads((OUT/'preparation.json').read_text());hardware_bad=[n for n,h in prep['protected_hardware'].items() if sha(ROOT/n)!=h]
assert not hardware_bad,hardware_bad
forms={n:ctx.ss[n].m for n in new_ids};candidate_delta={}
for n,m in forms.items():
    a=np.load(OUT/(n+'_candidate.npz'));ref=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    candidate_delta[n]=abs((m-ref).volume())+abs((ref-m).volume())
    assert candidate_delta[n]<.02,(n,candidate_delta[n])
    assert len(m.decompose())==1

def collision(m,fixed):
    bb=np.asarray(m.bounding_box());out=[]
    for n,t in fixed.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        overlap=m^t;v=float(overlap.volume())
        if abs(v)>1e-5:out.append(dict(target=n,overlap_mm3=v))
    return out
native={n:s.m for n,s in ctx.ss.items()}
fasteners={n for n in native if n.startswith('Frame_Screw_')}
front_follow={n for n in native if n.startswith('Speaker') or n in ['Frame_Insert_0','Frame_Insert_1']}
rear_follow={n for n in native if n.startswith('Rear_Interface_') or n in ['Power_Switch','USB_Receptacle','Frame_Insert_2','Frame_Insert_3']}
modules={'front':{**{n:native[n] for n in front_follow},'Body_Front':forms['Body_Front']},
         'rear':{**{n:native[n] for n in rear_follow},'Body_Rear':forms['Body_Rear'],
                 **{'Plug_'+n:ctx.plug[n].m for n in ['rear_J2','rear_J3']}}}
fixed={n:m for n,m in native.items() if n not in fasteners|front_follow|rear_follow|new_ids}
fixed.update({'Plug_'+n:s.m for n,s in ctx.plug.items() if n not in ['rear_J2','rear_J3']})
paths=[]
for label,sign in [('front',1),('rear',-1)]:
    target={**fixed,**modules['rear' if label=='front' else 'front']}
    first=None;checked=0
    for travel in np.r_[np.linspace(0,6,61),np.arange(7,221)]:
        for n,m in modules[label].items():
            hits=collision(m.translate([0,float(travel)*sign,0]),target)
            if hits:first=dict(travel_mm=float(travel),moving=n,hits=hits);break
        checked+=1
        if first:break
    paths.append(dict(module=label,positions=checked,travel_mm=220,wheels='present',opposite_shell='closed',status='FAIL' if first else 'PASS',first=first))
    print('CURRENT_BODY_MODULE_PATH',paths[-1],flush=True)
# Tools and real frame screws enter from below with the closed candidate shell.
# The body can be inverted in a bench fixture; no floor/standing claim.
fixed={n:m for n,m in native.items() if n not in retired|fasteners|{'Body_Front','Body_Rear'}}
fixed.update(forms)
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
toolrows=[]
for i,(x,y) in enumerate(P['shell_service']['frame_mount_xy_mm']):
    # Conservative straight shaft plus handle; nominal cross-drive compatibility
    # is not established by this geometric envelope.
    shaft=axial(2.5,125,[x,y,109-62.5],[0,0,1])
    handle=axial(10,60,[x,y,109-125-30],[0,0,1])
    parts=[shaft,handle];hits=[];thread_contacts=[]
    for j,m in enumerate(parts):
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);hull=manifold.Manifold.hull_points(np.r_[v,v+[0,0,-150]].tolist())
        hits += [dict(piece=j,**h) for h in collision(hull,fixed)]
    screw=ctx.ss[f'Frame_Screw_{i}'].m
    s=ctx.ss[f'Frame_Screw_{i}'];r=np.linalg.norm(s.v[:,:2]-[x,y],axis=1)
    headtop=float(s.v[r>1.5001,2].max())
    # Select native vertices rather than Boolean clipping at the coplanar
    # shoulder: a microscopic wide cap retained by the clip would make a
    # false full-radius shank hull. Each hull must enclose its native portion.
    head=manifold.Manifold.hull_points(s.v[s.v[:,2]<=headtop+1e-7].tolist())
    shank=manifold.Manifold.hull_points(s.v[(s.v[:,2]>=headtop-1e-7)&(r<1.5001)].tolist())
    assert abs((screw-(head+shank)).volume())<1e-6
    for j,m in enumerate([head,shank]):
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);hull=manifold.Manifold.hull_points(np.r_[v,v+[0,0,-150]].tolist())
        for h in collision(hull,fixed):
            if h['target']==f'Frame_Insert_{i}':
                # The same named nominal thread pair is already engaged in
                # the saved assembly. Do not ignore an entire fastener host:
                # prove the sweep adds no intersection beyond this endpoint.
                baseline=screw^fixed[h['target']]
                added=(hull^fixed[h['target']])-baseline
                assert abs(added.volume())<1e-6
                thread_contacts.append(dict(**h,native_engaged_overlap_mm3=float(baseline.volume()),
                    additional_overlap_mm3=float(added.volume()),status='NOT_TESTED',
                    meaning='Existing named screw/insert nominal thread engagement; physical threading not qualified'))
            else:hits.append(dict(piece='screw_'+str(j),**h))
    row=dict(screw=f'Frame_Screw_{i}',axis_mm=[x,y],status='BLOCKED' if hits else 'PASS',hits=hits,
             existing_thread_interfaces=thread_contacts)
    toolrows.append(row);print('BODY_SPLIT_FRAME_ACCESS',json.dumps(row),flush=True)


# Independently inspect actual saved locator walls, not just parameters.
wall=[]
for x in q['locators']['center_x_mm']:
    a=q['locators'];rr=[]
    for label,start,end in [('roof',[x,-2,31.3+.01],[x,-2,40]),
          ('left',[x-5.3-.01,-2,30],[x-12,-2,30]),('right',[x+5.3+.01,-2,30],[x+12,-2,30])]:
        hits=forms['Body_Rear'].ray_cast(start,end)
        thick=float(np.linalg.norm(np.asarray(hits[0].position)-start)+.01) if hits else None
        rr.append(dict(side=label,thickness_mm=thick));assert thick is not None and thick>=1.69,(x,label,thick)
    wall.append(dict(center_x_mm=x,wall=rr,tongue_thickness_mm=2,clearance_per_side_mm=.3,physical_fit='NOT_TESTED'))
ctx.assert_unchanged()
r=dict(status='PASS' if all(t['status']=='PASS' for t in paths+toolrows) else 'FAIL',revision=P['revision'],source_blend_sha256=ctx.source_hash,
    sources=ctx.sources,script_sha256=sha(Path(__file__)),scope=dict(unchanged=len(set(now)&set(old)),changed=changed,added=sorted(new_ids),retired=sorted(retired),unrelated_config_unchanged=True,hardware_files_unchanged=len(prep['protected_hardware'])),
    saved_vs_candidate_difference_mm3=candidate_delta,paths=paths,modules={n:sorted(g) for n,g in modules.items()},frame_tool_access=toolrows,locators=wall,
    nominal_tool='ASSUMED diameter5 x125 shaft + diameter20 x60 handle; 150 mm continuous axial hulls',
    complete_wired_assembly='BLOCKED: finite rigid modules and plug housings only; actual lead slack and unplug/closure deformation unresolved',
    physical_fit='NOT_TESTED',strength='NOT_TESTED',elapsed_s=time.time()-started)
save_json(OUT/'check.json',r);save_json(ROOT/'mechanical/reports/body_split_validation.json',r)
print('BODY_SPLIT_CURRENT',r['status'],r['scope'],flush=True)
assert r['status']=='PASS'
