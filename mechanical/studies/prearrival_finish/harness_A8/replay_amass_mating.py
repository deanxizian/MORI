"""Replay J1/J2 against dimensioned AMASS envelopes; main model is read-only."""
from pathlib import Path
TASK_SCRIPT=Path(__file__).resolve();TASK_DIR=TASK_SCRIPT.parent
HELPER=TASK_DIR.parent/'harness_A2/check_static.py';__file__=str(HELPER)
exec(compile(HELPER.read_text().split('MARGIN =')[0],str(HELPER),'exec'),globals())
__file__=str(TASK_SCRIPT)
sys.path.insert(0,str(TASK_DIR/'amass_mating'))
from envelopes import rebuild

OUT=TASK_DIR/'amass_mating';MODE='upper_with_thickness_allocation' if '--upper' in sys.argv else 'nominal'
dimensions=json.loads((OUT/'received_dimensions.json').read_text())
assert dimensions['mating_pair']==['XT30UPB-M','XT30U-F']
rows=rebuild(plug,portrows,port_pins,globals(),MODE)
trees={n:s.bvh() for n,s in plug.items()}
route=json.loads((TASK_DIR/'joined_entry_screen.json').read_text())
wire_checks=[]
for row in route['rows']:
    points=np.asarray(row['curve_mm']);error=row['error_bound_mm']
    allowance=.3302+.3+np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2+error+1e-4
    hits=[]
    for n,s in plug.items():
        mask=np.all(points>=s.lo-allowance,axis=1)&np.all(points<=s.hi+allowance,axis=1)
        # A segment that enters a solid necessarily approaches its boundary;
        # checking every in-box sample also catches a wholly-contained curve.
        for p in points[mask]:
            d=float(trees[n].find_nearest(Vector(p))[3])
            hit={'plug':n,'point_mm':p.tolist(),'distance_mm':d,'required_sampled_mm':float(allowance)} if d<allowance else None
            if not hit and np.all(p>=s.lo) and np.all(p<=s.hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(p.tolist())
                if (tiny^s.m).volume()>tiny.volume()/2:hit={'plug':n,'point_mm':p.tolist(),'inside':True}
            if hit:hits.append(hit);break
    wire_checks.append({'yaw_deg':row['yaw_deg'],'azimuth_deg':row['azimuth_deg'],
                        'status':'BLOCKED' if hits else 'PASS','hits':hits})
sweep_checks=[]
for i,angle in enumerate([45,135,225,315]):
    raw=np.load(TASK_DIR/'terminal_threading'/f'terminal_sweep_{i}.npz')
    sweep=manifold.Manifold(manifold.Mesh64(vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
    hits=[]
    for n,s in plug.items():
        overlap=max(0.,float((sweep^s.m).volume()))
        if overlap>1e-5:hits.append({'plug':n,'padded_sweep_overlap_mm3':overlap})
    sweep_checks.append({'azimuth_deg':angle,'status':'BLOCKED' if hits else 'PASS','hits':hits})

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={'status':'BLOCKED' if any(r['hits'] for r in wire_checks+sweep_checks) else 'PASS',
    'scope':'J1 installed local wires and J2 temporary bare-contact reference sweeps vs29 mating envelopes only',
    'mode':MODE,'source_blend_sha256':source_hash,'source_script_sha256':sha(TASK_SCRIPT),
    'source_helper_sha256':sha(OUT/'envelopes.py'),'source_dimensions_sha256':sha(OUT/'received_dimensions.json'),
    'source_route_sha256':sha(TASK_DIR/'joined_entry_screen.json'),
    'source_contact_sweeps':{str(i):sha(TASK_DIR/'terminal_threading'/f'terminal_sweep_{i}.npz') for i in range(4)},
    'mating_allocation_count':len(plug),'replaced_clearance_envelopes':rows,
    'installed_wire_vs_mates':wire_checks,'temporary_contact_sweep_vs_mates':sweep_checks,
    'main_model_applied':False,'whole_harness':'BLOCKED','physical_clearance':'NOT_TESTED',
    'unresolved':['Female-half thickness tolerance is not documented; upper5.9mm is a project allocation.',
      'No solder/heat-shrink/lead departure envelope added; nominal box clearance is not full wiring qualification.',
      'PCB seating and complete moulded profiles are not measured; historical23.1mm boxes remain archived.',
      'All other22 mating boxes retained; no main hardware, dimensions or pin maps modified.']}
(OUT/(MODE+'_replay.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('AMASS_REPLAY',MODE,record['status'],sum(r['status']!='PASS' for r in wire_checks),sweep_checks,flush=True)
