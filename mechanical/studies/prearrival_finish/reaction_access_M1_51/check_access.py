"""Continuous nominal fastener/tool access with current front/rear shells absent.

No C6 or restraint substitutions; no flexible harness or real horn assumption.
"""
from pathlib import Path
import json,sys,time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,P
from interface_completion import axial
ctx=Context();started=time.time()
native={n:s.m for n,s in ctx.ss.items()}
modules=json.loads((ROOT/'mechanical/studies/prearrival_finish/body_split_adoption/check.json').read_text())['modules']
absent={n for ids in modules.values() for n in ids}|{n for n in native if n.startswith('Frame_Screw_')}
fixed={n:m for n,m in native.items() if n not in absent}
fixed.update({'Plug_'+n:s.m for n,s in ctx.plug.items() if n not in ['rear_J2','rear_J3']})

def hits(m,targets):
    bb=np.asarray(m.bounding_box());rows=[]
    for n,t in targets.items():
        tb=np.asarray(t.bounding_box())
        if np.any(bb[3:]<tb[:3]) or np.any(tb[3:]<bb[:3]):continue
        overlap=m^t;v=float(overlap.volume())
        if abs(v)>1e-6:rows.append(dict(part=n,overlap_mm3=v))
    return rows

def sweep(m,delta):
    points=np.asarray(m.to_mesh64().vert_properties[:,:3])
    return manifold.Manifold.hull_points(np.r_[points,points+np.asarray(delta)].tolist())

rows=[];sweeps={}
for name,partner in [('Yaw_Reaction_Retainer_Nut','Yaw_Reaction_Retainer_Screw'),
                     ('Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut')]:
    s=ctx.ss[name];axis=np.array([0.,-1. if name.endswith('Nut') else 1.,0.])
    targets={n:m for n,m in fixed.items() if n not in {name,partner}}
    if name.endswith('Nut'):
        pieces=[s.m]
    else:
        center=(s.lo+s.hi)/2;radius=np.linalg.norm(s.v[:,[0,2]]-center[[0,2]],axis=1)
        shoulder=float(s.v[radius>1.0,1].min())
        pieces=[manifold.Manifold.hull_points(s.v[s.v[:,1]>=shoulder-1e-7].tolist()),
                manifold.Manifold.hull_points(s.v[(s.v[:,1]<=shoulder+1e-7)&(radius<1.0001)].tolist())]
        assert abs((s.m-(pieces[0]+pieces[1])).volume())<1e-6
    collision=[]
    for i,m in enumerate(pieces):
        volume=sweep(m,axis*150)
        sweeps[name+'_'+str(i)]=volume
        collision += [dict(piece=i,**h) for h in hits(volume,targets)]
    rows.append(dict(id=name,status='PASS' if not collision else 'BLOCKED',direction=axis.tolist(),
                     continuous_travel_mm=150,hits=collision,partner_deferred=partner,
                     method='Union of convex hulls enclosing each actual fastener piece over continuous axial translation'))

name='Yaw_Reaction_Retainer_Screw';s=ctx.ss[name];center=(s.lo+s.hi)/2
face=np.array([center[0],s.hi[1],center[2]])
tools=[axial(1.25,100,face+[0,50,0],[0,1,0]),axial(8,60,face+[0,130,0],[0,1,0])]
collision=[]
for i,m in enumerate(tools):
    volume=sweep(m,[0,150,0]);sweeps['driver_'+str(i)]=volume
    collision += [dict(piece=i,**h) for h in hits(volume,{n:m for n,m in fixed.items() if n!=name})]
rows.append(dict(id='lower_retainer_driver',status='PASS' if not collision else 'BLOCKED',hits=collision,
                 continuous_travel_mm=150,tool='ASSUMED diameter2.5x100 shaft and diameter16x60 handle; actual drive engagement/torque not selected'))

# Revisit the separate upper clamp in the actual current head. A lower tool
# success must never be mistaken for the unresolved first assembly up here.
nut=ctx.ss['Yaw_Reaction_Clamp_Nut'];upper=sweep(nut.m,[0,-30,0])
upper_targets={n:m for n,m in fixed.items() if n not in {'Yaw_Reaction_Clamp_Nut','Yaw_Reaction_Clamp_Screw'}}
upper_hits=hits(upper,upper_targets)
upper_row=dict(id='upper_clamp_nut_after_yoke_installation',status='BLOCKED' if upper_hits else 'PASS',
               continuous_travel_mm=30,direction=[0,-1,0],hits=upper_hits,
               meaning='One specific straight insertion only; does not prove all possible assembly routes impossible')
ctx.assert_unchanged()
for n,m in sweeps.items():
    a=m.to_mesh64();np.savez_compressed(OUT/(n+'_sweep.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
r=dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'BLOCKED',revision=P['revision'],
       source_blend_sha256=ctx.source_hash,sources=ctx.sources,lower_rows=rows,upper_row=upper_row,
       absent_in_core_stage=sorted(absent),fixed_candidate_wires_included=False,
       scope='Current lower reaction-retainer fastener/tool access before front/rear modules and wiring; independent upper-clamp diagnostic',
       full_reaction_preassembly='BLOCKED',final_fastener_and_horn_selection='BLOCKED',
       full_wired_assembly='BLOCKED',physical_fit='NOT_TESTED',C6_applied=False,
       main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'access.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('M1_52_ACCESS',json.dumps(dict(status=r['status'],lower_rows=rows,upper_row=upper_row)),flush=True)
