"""Bounded placement screen of an unapproved CAM clamp; no native edits."""
from pathlib import Path
import json, sys, time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes'; OUT=BASE/'cam_restraints/position_screen'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from mathutils import Vector
ctx=Context();started=time.time();CON=BASE/'cam_restraints/connector';JOIN=BASE/'cam_side_fans/c6_join'
source=json.loads((CON/'review.json').read_text())
for n,h in source['output_geometry'].items():assert sha(CON/n)==h,n
def stored(p):
    a=np.load(p);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
old={n:stored(CON/(n+'.npz')) for n in ['addition','band','head']}
curves=np.load(JOIN/'candidate_curves.npz');rows=[]
for dz in [.4,.6,.8,1.0]:
    for tx in [.01,.03,.05]:
        pieces={n:m.translate([tx if n!='addition' else 0,0,dz]) for n,m in old.items()}
        bed=pieces['addition'];tie=pieces['band']+pieces['head'];host=ctx.ss['Pitch_Cradle'].m
        overlap=float((tie^(host+bed)).volume());grip=[]
        for pin in range(1,5):
            x=-11.600000143051147+pin-1;r=(.3302+.001)/np.cos(np.pi/64)
            tube=manifold.Manifold.cylinder(5.,r,circular_segments=64).translate([x,-20.800000190734863,209.6000061])
            grip.append(float((tube^(bed+tie)).volume()))
        native=[]
        for n,s in ctx.ss.items():
            if s.group!='pitch' or n=='Pitch_Cradle':continue
            for part,m in pieces.items():
                bb=np.array(m.bounding_box())
                if not (np.all(bb[:3]<=s.hi+.3) and np.all(bb[3:]>=s.lo-.3)):continue
                vol=float((m^s.m).volume());gap=float(m.min_gap(s.m,.31)) if abs(vol)<1e-7 else 0.
                if abs(vol)>1e-6 or gap<.3-1e-5:native.append(dict(part=part,target=n,volume_mm3=vol,gap_mm=gap))
        power=[]
        for pitch in [0,10,15,20,25]:
            inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
            p=curves['P_J18_1_y0']@inv[:3,:3].T+inv[:3,3]
            ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
            bound=.5842+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0004
            for part,m in pieces.items():
                t=ctx.target(m);ids=np.flatnonzero(np.all(p>=t['lo']-bound[:,None],axis=1)&np.all(p<=t['hi']+bound[:,None],axis=1))
                for i in ids:
                    d=float(t['tree'].find_nearest(Vector(p[i]))[3])
                    if d<bound[i]:power.append(dict(pitch=pitch,part=part,distance_mm=d,required_mm=float(bound[i])));break
        row=dict(dz_mm=dz,tie_translation_x_mm=tx,tie_solid_overlap_mm3=overlap,
                 wire_grip_overlap_mm3=grip,same_group_native_hits=native,power_hits=power,
                 root_overlap_mm3=float((host^bed).volume()),host_components=len((host+bed).decompose()))
        row['status']='PASS' if overlap<1e-6 and max(grip)<1e-6 and not native and not power and row['root_overlap_mm3']>1 and row['host_components']==1 else 'BLOCKED'
        rows.append(row);print('POSITION',dz,tx,row['status'],overlap,max(grip),len(native),len(power),flush=True)
ctx.assert_unchanged();inputs=[CON/'review.json',JOIN/'candidate_curves.npz',*[CON/(n+'.npz') for n in old]]
r=dict(status='PASS',scope='Completed limited placement screen, not full acceptance',rows=rows,
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},main_changed=False,
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n')
