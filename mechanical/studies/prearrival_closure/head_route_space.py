"""Screen existing annular space; an envelope is NOT a qualified service loop."""
import sys,json,hashlib,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
def annulus(r,half,z0,z1):
    return (manifold.Manifold.cylinder(z1-z0,r+half,r+half,96)-manifold.Manifold.cylinder(z1-z0,r-half,r-half,96)).translate((0,0,z0))
def hits(m,yaw,pitch):
    bb=np.array(m.bounding_box());out=[]
    for n,s in ss.items():
        if s.group in ['yaw','pitch']:t=Solid(s.o,s,rigidtr(yaw,pitch if s.group=='pitch' else 0))
        else:t=s
        if np.any(bb[3:]<t.lo) or np.any(t.hi<bb[:3]):continue
        v=max(0,(m^t.m).volume())
        if v>.05:out.append(dict(part=n,volume_mm3=v))
    return out
rows=[]
for r,z,half in itertools.product([21.5,22.5,24,26,28],[165.5,167,168.5],[1.6,2.6]):
    m=annulus(r,half,z-half,z+half);bad=[]
    for ya,pi in [(0,0),(-60,-20),(60,-20),(-60,25),(60,25),(0,-20),(0,25)]:
        hs=hits(m,ya,pi)
        if hs:bad.append(dict(yaw_deg=ya,pitch_deg=pi,hits=hs));break
    rows.append(dict(radius_mm=r,z_mm=z,bundle_envelope_diameter_mm=2*half,status='FAIL' if bad else 'PASS',failures=bad))
    print('ANNULAR',r,z,half,rows[-1]['status'],flush=True)
best=next((r for r in rows if r['status']=='PASS' and r['bundle_envelope_diameter_mm']>=5.2),next((r for r in rows if r['status']=='PASS'),None))
full=[]
if best:
    m=annulus(best['radius_mm'],best['bundle_envelope_diameter_mm']/2,best['z_mm']-best['bundle_envelope_diameter_mm']/2,best['z_mm']+best['bundle_envelope_diameter_mm']/2)
    for ya in range(-60,61,10):
        for pi in range(-20,26,5):
            hs=hits(m,ya,pi)
            if hs:full.append(dict(yaw_deg=ya,pitch_deg=pi,hits=hs))
out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),screened=rows,selected=best,combined_pose_count=130 if best else 0,selected_failures=full,status='PASS' if best and not full else 'BLOCKED',scope='Space envelope screening only, not a bend/length/anchoring-qualified moving harness',limits=['Existing solid geometry retained; no new openings.','A free circular envelope does not itself supply ingress, egress, constant wire length or strain relief.','Selected cable OD, insulation, bundle packing, 3D slack and manufactured connection ends must be resolved before full routing PASS.'])
(HERE/'head_route_space.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('SELECTED',best,'FULL_FAILURES',len(full),flush=True)
