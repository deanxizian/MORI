"""Read-only sections of the current neck and failed raised-entry route family.

This diagnoses the actual retained solids. It neither cuts a new channel nor
promotes an individual route to a complete harness.
"""
from pathlib import Path
import json, math, sys, time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE/'remaining_routes/entry_topology_review'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT/'mechanical/scripts'))
sys.path.insert(0, str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context, np, sha, Vector
from curvature_paths import paths
ctx = Context(); started = time.time(); step = .03
base = HERE/'remaining_routes/cam_four_order_expanded'
src = json.loads((base/'body_prefix_screen.json').read_text())
assert src['status'] == 'PASS'
for f,h in {**src['sources'], **src['inputs']}.items(): assert sha(ROOT/f)==h, f
assert sha(base/'body_prefix_candidates.npz') == src['curve_sha256']
raw = np.load(base/'body_prefix_candidates.npz')
UP = np.array([0.,0.,1.])
def line(a,b): return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
def rebuild(seed, z):
    p = ctx.port_pins['motion_J5']['pins'][str(seed['pin'])]
    R = seed['minimum_centerline_radius_mm']; lead = seed['lead_mm']
    unit = lambda deg: np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg)),0.])
    eh,xh = unit(seed['entry_deg']),unit(seed['exit_deg'])
    tt = np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
    stem = line(p,p+lead*UP)
    entry = stem[-1]+R*(1-np.cos(tt))[:,None]*eh+R*np.sin(tt)[:,None]*UP
    q=raw[seed['id']][-1].copy(); q[2]=z
    bottom=q-R*xh-R*UP; drop=entry[-1,2]-bottom[2]
    if drop<=0:return None
    angle=math.acos(1-drop/(2*R)) if drop<2*R else math.pi/2
    aa=np.linspace(0,angle,math.ceil(R*angle/step)+1)
    c=bottom-2*R*math.sin(angle)*xh+drop*UP
    a=c+R*np.sin(aa)[:,None]*xh-R*(1-np.cos(aa))[:,None]*UP
    v=line(a[-1],a[-1]-max(0.,drop-2*R)*UP);back=aa[::-1]
    b=v[-1]+R*(math.sin(angle)-np.sin(back))[:,None]*xh-R*(np.cos(back)-math.cos(angle))[:,None]*UP
    last=bottom+R*np.sin(tt)[:,None]*xh+R*(1-np.cos(tt))[:,None]*UP
    plan=next((x for x in paths(entry[-1,:2],eh[:2],a[0,:2],xh[:2],seed['planar_radius_mm'],step) if x['family']==seed['family']),None)
    if plan is None:return None
    middle=np.c_[plan['points_xy_mm'],np.full(len(plan['points_xy_mm']),entry[-1,2])]
    return np.vstack([stem,entry[1:],middle[1:],a[1:],v[1:],b[1:],last[1:]])

rows = [r for rs in src['pools'].values() for r in rs]
selected = [min((r for r in rows if r['pin']==pin),key=lambda r:r['analytic_length_mm']) for pin in [1,2]]
curves = {}; cases = []
for r in selected:
    for z in [142.,149.]:
        p = rebuild(r,z)
        if p is None: continue
        key=f'pin{r["pin"]}_entry{z:g}'; curves[key]=p
        target=ctx.targets['Yaw_Base']
        candidates=[(float(target['tree'].find_nearest(Vector(v))[3]),i) for i,v in enumerate(p)]
        distance,i=min(candidates)
        witness=p[i]; probe=__import__('manifold3d').Manifold.sphere(.01,12).translate(witness.tolist())
        cases.append(dict(id=key,seed=r['id'],entry_z_mm=z,pin=r['pin'],
            global_nearest_surface_distance_mm=distance,point_mm=witness.tolist(),
            sampled_point_inside_solid=(probe^target['m']).volume()>probe.volume()/2,
            first_clearance_failure=ctx.clear(p,radius=.3302,ignore=['Plug_motion_J5']),
            scope='One reconstructed representative, not all paths'))

sections=[]
for z in [134.,137.,140.,142.,145.,149.]:
    solids={}
    for n in ['Yaw_Base','Yaw_Reaction_Link','Yaw_Reaction_Retainer_Screw','Power_Module','MCU_Carrier']:
        s=ctx.ss.get(n)
        if s is not None and s.lo[2]<z<s.hi[2]:solids[n]=[p.tolist() for p in s.m.slice(z).to_polygons()]
    sections.append(dict(kind='XY',z_mm=z,solids=solids))
for angle in [117.,135.,153.,180.]:
    a=math.radians(angle);tr=np.array([[math.cos(a),math.sin(a),0,0],[0,0,1,0],[-math.sin(a),math.cos(a),0,0]])
    solids={n:[p.tolist() for p in ctx.ss[n].m.transform(tr).slice(0).to_polygons()]
            for n in ['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Bearing']}
    sections.append(dict(kind='RZ',angle_deg=angle,solids=solids))
ctx.assert_unchanged()
np.savez_compressed(OUT/'representative_curves.npz',**curves)
report=dict(status='PASS',scope='Read-only extraction and diagnosis, not route qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [base/'body_prefix_screen.json',base/'body_prefix_candidates.npz']},
    sections=sections,cases=cases,root_pins={k:{i:p.tolist() for i,p in ctx.port_pins[k]['pins'].items()} for k in ['motion_J5','power_J9','power_J18']},
    curve_sha256=sha(OUT/'representative_curves.npz'),main_changed=False,
    full_harness='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'sections.json').write_text(json.dumps(report,indent=2)+'\n')
print('ENTRY_SECTIONS_DONE',report['elapsed_s'],cases,flush=True)
