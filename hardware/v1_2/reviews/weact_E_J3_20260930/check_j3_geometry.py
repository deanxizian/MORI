"""Read-only M1.42 assembly screening; writes this review directory only.
Run Blender against the frozen socket_candidate.blend. No scene save or edits.
"""
import sys, json, hashlib, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from validate import Solid
ROOT=PROJECT

load_collections(); assembled(); bpy.context.view_layer.update()
targets={}
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith(PREFIX): continue
    n=o.name.removeprefix(PREFIX)
    if o.get('role') in ['validation_proxy','keepout','study']: continue
    if o.get('group') in ['dock','coupon']: continue
    if n in ['Rear_Interface_PCB','MCU_Motion']: continue
    # Only source parts and the socket candidate geometry; no loose study meshes.
    if o.get('category') not in ['PRINTABLE','PURCHASED_REFERENCE'] and not n.startswith('STUDY_'): continue
    try: targets[n]=Solid(o).m
    except Exception as exc: raise RuntimeError((n,str(exc)))
for o in bpy.data.objects:
    if o.type=='MESH' and o.name.startswith(PREFIX+'STUDY_Socket_'):
        targets[o.name.removeprefix(PREFIX)]=Solid(o).m

# Use immutable received rear-board component meshes, excluding its own J3.
cache=json.loads((ROOT/'mechanical/sources/populated_P5/rear_complete_mesh.json').read_text())
R=np.diag([-1.,-1.,1.]); T=np.array([12.,-75.5,110.545])
for c in cache['components']:
    if c['reference'] in ['PCB','J3']: continue
    for i,s in enumerate(c['solids']):
        v=np.array(s['vertices_mm'])@R.T+T
        m=manifold.Manifold(manifold.Mesh64(v,np.array(s['triangles'],dtype=np.uint64)))
        if m.status()!=manifold.Error.NoError: raise RuntimeError(('invalid CAD',c['reference'],i))
        targets['Rear/'+c['reference']+'/'+str(i)]=m

def hits(m):
    b=np.array(m.bounding_box()); ans=[]
    for n,t in targets.items():
        bb=np.array(t.bounding_box())
        if np.any(b[3:]<bb[:3]) or np.any(bb[3:]<b[:3]):continue
        v=max(0,(m^t).volume())
        if v>.01:ans.append({'target':n,'overlap_mm3':v})
    return ans

rows=[]
poses=[(8.45,19.5,0,'F'),(8.45,19.5,180,'F'),(8.45,19.5,90,'F'),(8.45,19.5,270,'F'),
       (8.45,18.0,0,'F'),(8.45,17.5,0,'F'),(8.45,20,0,'F')]
poses += [(x,y,270,'F') for x in [5.5,6,6.5,7,7.5,8] for y in [18.3,18.8]]
# Bottom-side geometry expressed by a reflected local Y and normal; placement
# is converted to a concrete native footprint only after geometry screening.
poses += [(x,y,90,'B') for x in [10.8,11.3,11.8,12.3,12.8,13.3,13.8,14.3] for y in [24.0,24.5,24.8]]
for x,y,a,side in poses:
    # Native rotation converts x/y on board to STEP axes; board Rz180 above.
    q=math.radians(a)
    F=np.array([[math.cos(q),math.sin(q),0],[-math.sin(q),math.cos(q),0],[0,0,1.]])
    native_to_step=np.diag([1.,-1.,1.]); W=R@native_to_step@F
    if side=='B':W=W@np.diag([1.,-1.,-1.])
    origin=R@np.array([x,-y,1.555 if side=='F' else -.045])+T
    def box(center,size):
        return manifold.Manifold.cube(size,True).transform(np.c_[W,origin+W@np.array(center)])
    header=box([3,2.45,2.4],[9.9,7.6,4.8])
    plug=box([3,4.825,2.4],[9.8,6.85,4.8])
    sweep=box([3,10.825,2.4],[9.8,18.85,4.8])
    rows.append({'native_pad1_xy_mm':[x,y],'rotation_deg':a,'side':side,'type':'SIDE_ENTRY',
                 'header_world_bounds_mm':header.bounding_box(),'plug_world_bounds_mm':plug.bounding_box(),
                 'unplug_axis_world':(W@np.array([0,1,0])).tolist(),
                 'header_hits':hits(header),'mated_hits':hits(plug),'continuous_12mm_sweep_hits':hits(sweep)})
for x,y,a in [(8.45,19.5,0),(8.45,20,0),(8.45,21,0),(8.45,22,0),(14.45,21.2,180)]:
    # JST ePH p1: 4.5mm body depth, pad row 1.7mm from near edge.
    # Generic KiCad model agrees: local Y[-1.7,+2.8], centre +0.55.
    # Earlier 1.025mm centre was not supported and is corrected here.
    W=np.diag([-1.,-1.,-1.]) if a==0 else np.diag([1.,1.,-1.])
    origin=np.array([12-x,y-75.5,110.5])
    def box(center,size):
        return manifold.Manifold.cube(size,True).transform(np.c_[W,origin+W@np.array(center)])
    header=box([3,.55,3],[9.9,4.5,6])
    plug=box([3,.55,4.575],[9.8,4.5,6.85])
    sweep=box([3,.55,10.575],[9.8,4.5,18.85])
    # Conservative full-footprint box over all 3.4mm solder-tail length,
    # including passage through the PCB. This is larger than the actual pins.
    leads=box([3,.55,-1.7],[9.9,4.5,3.4])
    rows.append({'native_pad1_xy_mm':[x,y],'rotation_deg':a,'side':'B','type':'TOP_ENTRY',
                 'header_world_bounds_mm':header.bounding_box(),'plug_world_bounds_mm':plug.bounding_box(),
                 'unplug_axis_world':[0,0,-1],
                 'header_hits':hits(header),'mated_hits':hits(plug),'continuous_12mm_sweep_hits':hits(sweep),
                 'conservative_upward_lead_envelope_bounds_mm':leads.bounding_box(),
                 'conservative_upward_lead_envelope_hits':hits(leads)})
report={'status':'CANDIDATE_SCREENING_NOT_RELEASE','date':'2026-09-30',
        'assembly':str(bpy.data.filepath),'assembly_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        'rear_cache_sha256':hashlib.sha256((ROOT/'mechanical/sources/populated_P5/rear_complete_mesh.json').read_bytes()).hexdigest(),
        'helper_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'mechanical/scripts/common.py',ROOT/'mechanical/scripts/validate.py']},
        'targets':sorted(targets),'candidates':rows,
        'limits':'Rigid nominal PH outer envelopes; continuous 12mm straight plug sweep, no wire/finger/elasticity certification. Wrongly flipped core omitted; stack requalification is pending. No native board or mechanical model saved.'}
(HERE/'j3_geometry_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for r in rows: print(r['native_pad1_xy_mm'],r['rotation_deg'],'body',r['header_hits'],'plug',r['mated_hits'],'sweep',r['continuous_12mm_sweep_hits'],flush=True)
