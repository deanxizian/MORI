# -*- coding: utf-8 -*-
"""A2 static lead study on the saved assembly; never save or alter that blend.

Inputs distinguish documented pin pitch/wire OD from assumed terminal exits.
Circular bends retain the received wire radius; no smaller-radius relaxation.
"""
from pathlib import Path
import csv, json, hashlib, math, itertools, time

STUDY = Path(__file__).resolve().parent
SCRIPT = Path(__file__).resolve()
__file__ = str(STUDY.parent / 'body_routes_current.py')
bootstrap = Path(__file__).read_text().split('prior=json.loads')[0]
exec(compile(bootstrap, __file__, 'exec'), globals())
__file__ = str(SCRIPT)
from native_electronics import board_transform, source_mesh

HANDOFF = PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json'
A2 = PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json'
CSV = PROJECT/'hardware/v1_2/prearrival_20261002/harness_detail.csv'
received = json.loads(HANDOFF.read_text())
wire_rows = {r['线束']: r for r in csv.DictReader(CSV.open(encoding='utf-8-sig'))}
ECOWIRE = '--ecowire' in sys.argv
OUTPUT_STEM = 'ecowire_candidate' if ECOWIRE else 'static_screen'
if ECOWIRE:
    # Alternative research inputs only. Received A2 CSV is left untouched.
    options = json.loads((STUDY/'ecowire_sources.json').read_text())['products']
    for hid in ['H01','H02','H03','H04','H05']:
        row=wire_rows[hid];o=next(q for q in options if q['AWG']==int(row['AWG']))
        row['绝缘外径最大mm']=str(o['insulation_OD_max_mm'])
        row['厂家弯曲10D保守mm']=str(o['required_radius_using_max_OD_mm'])
        row['导线筛查样本']='Alpha '+o['part_number']+' CANDIDATE_NOT_SELECTED;5D manufacturer basis'
board_sources = {}
port_pins = {}
for kind, spec in P['native_electronics']['boards'].items():
    cache = source_mesh(spec['mesh']); rot, trans = board_transform(kind, cache)
    board = next(v for k, v in received['boards'].items() if k.startswith('MORI_'+kind+'_'))
    assert board['pcb_sha256'] == cache['source_native_sha256'], kind
    board_sources[kind] = dict(file=cache['source_native_file'], sha256=cache['source_native_sha256'])
    for c in board['connectors']:
        key = kind+'_'+c['ref']
        if key not in plug: continue
        pad_points = {p['pin']: rot@np.array([p['xy_mm'][0], -p['xy_mm'][1], 0])+trans for p in c['pins']}
        mean = np.mean(list(pad_points.values()), axis=0)
        row = portrows[key]
        # P5R7 rear J3 is on the opposite PCB side. Its actual plug is already
        # rigidly transformed by the bootstrap; the historical row is not.
        axis = np.array(row['axis'], float)
        if key == 'rear_J3': axis = -axis
        p = plug[key]; center = (p.lo+p.hi)/2
        face = center+axis*(max(p.v@axis)-center@axis)
        port_pins[key] = dict(axis=axis, exit_face=face, pins={
            n: face+(v-mean)-axis*((v-mean)@axis) for n, v in pad_points.items()})

MARGIN = .3  # Explicit project clearance allocation; not a supplier tolerance.
STEP = .4
def bad_at(point, clearance, ignore=()):
    point = np.asarray(point)
    if not (-59<point[0]<59 and -71<point[1]<64 and 65<point[2]<150):
        return ['study_workspace_boundary']
    near = np.where(np.all(point>=los-clearance,axis=1)&np.all(point<=his+clearance,axis=1))[0]
    bad=[]
    for i in near:
        name=obs[i]
        if name in ignore: continue
        pos, norm, _, dist = trees[name].find_nearest(Vector(point))
        if dist<clearance:
            bad.append(name)
        elif np.all(point>=los[i]) and np.all(point<=his[i]):
            # At a face edge its normal is not a point-containment test.
            # The query is already farther than clearance from all surfaces,
            # so a tiny closed solid distinguishes full containment reliably.
            probe=manifold.Manifold.sphere(.01,16).translate(point.tolist())
            if (probe^obstacles[name].m).volume()>probe.volume()*.5:bad.append(name)
    return bad

def straight_check(port, pin, od, length=5):
    d=port_pins[port]; e=d['pins'][str(pin)]; a=d['axis']
    # Cylinder caps begin at the exit face. Ignore only its own mating housing
    # in the *outward* straight segment, where the clearance sphere otherwise
    # rejects the deliberate terminal contact. All other solids remain live.
    for s in np.linspace(0,length,26):
        hit=bad_at(e+a*s,od/2+MARGIN,{'Plug_'+port})
        if hit:return dict(status='FAIL',first_blocked_offset_mm=float(s),blockers=hit)
    return dict(status='PASS',length_allocation_mm=length)

def clean(points):
    out=[]
    for p in points:
        p=np.array(p,float)
        if not out or np.linalg.norm(p-out[-1])>.001:out.append(p)
    i=1
    while i<len(out)-1:
        u=out[i]-out[i-1];v=out[i+1]-out[i]
        if u@v/(np.linalg.norm(u)*np.linalg.norm(v))>.999999:out.pop(i)
        else:i+=1
    return out

def controls(a,b,R,hid):
    # Both endpoints point up in H01-H03. Do not change terminal orientation.
    z0=max(a[2],b[2])+R
    for z in np.arange(math.ceil(z0*2)/2,149.01,1):
        yield clean([a,[a[0],a[1],z],[b[0],b[1],z],b])
        if hid=='H01':
            for y in [-28,-34,-40,-44,-48,-52,-56,-60,-64]:
                yield clean([a,[a[0],a[1],z],[a[0],y,z],[b[0],y,z],[b[0],b[1],z],b])
            for x,y in itertools.product([-46,-42,-38,-32,-26],[-42,-48,-54,-60]):
                yield clean([a,[a[0],a[1],z],[x,a[1],z],[x,y,z],[b[0],y,z],[b[0],b[1],z],b])
        else:
            for x in [25,29,33,37,41,45,49,53]:
                yield clean([a,[a[0],a[1],z],[x,a[1],z],[x,b[1],z],[b[0],b[1],z],b])
            for x,y in itertools.product([32,38,44,50],[-50,-42,-34,-26,-18,-10]):
                yield clean([a,[a[0],a[1],z],[x,y,z],[b[0],b[1],z],b])
    if ECOWIRE and hid in ['H02','H03']:
        # Different-height end turns allow numbered lanes to pass each other
        # without swapping pins or reducing the wire's bend radius.
        for za,zb,x,y in itertools.product([141,143,145,147],[140,142,144,146],
                                          [30,34,38,42,46],[-50,-42,-34,-26,-18]):
            yield clean([a,[a[0],a[1],za],[x,y,(za+zb)/2],[b[0],b[1],zb],b])

def min_poly_dist(A,B):
    # Exact line-segment minimum; endpoint-only sampling cannot certify gaps.
    amin=float('inf');where=None
    for p,q in zip(A,A[1:]):
        u=q-p; aa=u@u
        for r,s in zip(B,B[1:]):
            v=s-r;w=p-r;bb=u@v;cc=v@v;dd=u@w;ee=v@w
            vals=[]
            for x,y,z in [(p,r,s),(q,r,s),(r,p,q),(s,p,q)]:
                vv=z-y; den=vv@vv
                t=np.clip((x-y)@vv/den,0,1) if den>1e-15 else 0
                vals.append(float(np.linalg.norm(x-y-t*vv)))
            det=aa*cc-bb*bb
            if det>1e-12:
                t=(bb*ee-cc*dd)/det;f=(aa*ee-bb*dd)/det
                if 0<=t<=1 and 0<=f<=1:vals.append(float(np.linalg.norm(w+t*u-f*v)))
            d=min(vals)
            if d<amin:amin=d;where=[((p+q)/2).tolist(),((r+s)/2).tolist()]
    return amin,where

specs=[('H01','power_J17','motion_J1',[1,2]),('H02','motion_J2','power_J13',[1,2]),('H03','motion_J3','power_J14',[1,2])]
straight_rows=[];pools={};rows=[];start=time.time()
for hid,pa,pb,pins in specs:
    wire=wire_rows[hid]; od=float(wire['绝缘外径最大mm']);R=float(wire['厂家弯曲10D保守mm']); straight=float(wire['端后直段分配mm_ASSUMED'])
    for pin in pins:
        wid=hid+'_'+str(pin); da=port_pins[pa];db=port_pins[pb]
        ea=da['pins'][str(pin)];eb=db['pins'][str(pin)];aa=da['axis'];ab=db['axis']
        assert aa[2]>.999 and ab[2]>.999
        a=ea+aa*straight;b=eb+ab*straight
        exits=[dict(port=p,pin=pin,**straight_check(p,pin,od,straight)) for p in (pa,pb)]
        straight_rows+=exits; pool=[];count=dict(controls=0,short_legs=0,obstructed=0);closest=None;seen=set()
        if all(x['status']=='PASS' for x in exits):
            for cp in controls(a,b,R,hid):
                count['controls']+=1;curve=rounded(cp,R)
                if curve is None:count['short_legs']+=1;continue
                curve=np.array(curve);pts=resample(curve,STEP)
                first=None
                # STEP/2 supplies a conservative sampled-distance allowance.
                for i,p in enumerate(pts):
                    hits=bad_at(p,od/2+MARGIN+STEP/2)
                    if hits:first=dict(point_mm=p.tolist(),blockers=hits,samples_passed=i,total_samples=len(pts));break
                if first:
                    count['obstructed']+=1
                    if closest is None or first['samples_passed']/first['total_samples']>closest['samples_passed']/closest['total_samples']:
                        closest=first
                    continue
                full=np.concatenate([[ea],curve,[eb]])
                key=tuple(np.rint(resample(full,10)[1:-1].ravel()/2).astype(int))
                if key in seen:continue
                seen.add(key)
                pool.append(dict(id=wid,harness=hid,pin=pin,from_port=pa,to_port=pb,curve_mm=full.tolist(),
                    controls_mm=[p.tolist() for p in cp],wire_OD_max_mm=od,analytic_bend_radius_mm=R,
                    terminal_straight_mm=straight,geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum())))
        pools[wid]=sorted(pool,key=lambda r:r['geometric_centerline_length_mm'])[:120]
        row=dict(id=wid,status='PASS' if pool else 'BLOCKED',candidate_count=len(pool),search=count,
                 terminal_checks=exits,closest_failed_candidate=closest,
                 scope='Individual static circular-wire corridor only; no joint packing/retention/assembly approval')
        rows.append(row);print('A2_STATIC',wid,row['status'],len(pool),count,flush=True)
        (STUDY/(OUTPUT_STEM+'_progress.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')

# A separate *single-wire* exit check for each IMU/H05 pin, avoiding an
# invented OD2.8 four-wire bundle. No claim this creates a complete route.
extra=[]
for hid,ports in [('H04',['motion_J4','imu_J1']),('H05',['motion_J7','power_J10'])]:
    w=wire_rows[hid];od=float(w['绝缘外径最大mm'])
    for port in ports:
        for pin in range(1,9):extra.append(dict(harness=hid,port=port,pin=pin,**straight_check(port,pin,od)))

# Local escape survey isolates terminal constraints from the full-route search.
# A quarter circle turns each outgoing vertical lead towards a horizontal
# azimuth. This finite family is diagnostic, never a claim of impossibility.
escape=[]
for hid,pa,pb,pins in specs:
    w=wire_rows[hid];od=float(w['绝缘外径最大mm']);R=float(w['厂家弯曲10D保守mm'])
    for port in [pa,pb]:
        for pin in pins:
            d=port_pins[port];e=d['pins'][str(pin)];axis=d['axis'];startp=e+axis*5
            trials=[]
            for degrees in range(0,360,5):
                theta=math.radians(degrees);lateral=np.array([math.cos(theta),math.sin(theta),0])
                arc=np.array([startp+R*(math.sin(a)*axis+(1-math.cos(a))*lateral) for a in np.linspace(0,math.pi/2,101)])
                first=None
                for i,p in enumerate(arc):
                    hh=bad_at(p,od/2+MARGIN+.11)
                    if hh:first=dict(point_mm=p.tolist(),blockers=hh,angle_deg=i*.9);break
                trials.append(dict(azimuth_deg=degrees,status='PASS' if first is None else 'FAIL',first_block=first))
            escape.append(dict(harness=hid,port=port,pin=pin,exit_mm=e.tolist(),
                radius_mm=R,straight_mm=5,trials=trials,clear_azimuths_deg=[q['azimuth_deg'] for q in trials if q['status']=='PASS']))

out=dict(revision=P['revision'],source_blend_sha256=source_hash,status='BLOCKED',
    scope='Received A2 wire-size screening; no complete harness or manufacturing release',
    alternative_wire_research=ECOWIRE,
    alternative_source='ecowire_sources.json' if ECOWIRE else None,
    sources={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HANDOFF,A2,CSV,SCRIPT]},
    native_board_sources=board_sources,received_harness_count=len(wire_rows),rows=rows,candidate_pools=pools,
    H04_H05_single_wire_straight_exit_checks=extra,
    terminal_quarter_turn_survey=escape,
    geometry_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,
    extra_print_holes=False,cut_lengths_released=False,elapsed_s=time.time()-start,
    assumptions=['Wire exit centers follow documented numbered pad pitch, on the centerline of the documented mating-housing envelope; precise crimp/terminal transverse offset is unknown.',
      '5mm terminal straight and0.3mm rigid margin are project allocations; supplier wire OD and10D radius are received screening data, not selected procurement.',
      'Existing connector envelopes have incomplete contacts/tolerances. Every named clearance is nominal.',
      'Analytic circular arcs are tessellated at<=0.5mm; screening adds0.2mm sample-distance allowance. Actual selected route requires solid sweep, pairwise clearance and fixation.',
      'Workspace bounds are finite; failure is not proof no possible routing exists.',
      'Final cut length needs both termination allowances, strain relief, unplug slack and removal paths. Geometric lengths are not cut instructions.',
      'No dynamic cable lifetime or moving head loop qualification.'])
(STUDY/(OUTPUT_STEM+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A2_STATIC_COMPLETE',out['status'],round(out['elapsed_s'],2),flush=True)
