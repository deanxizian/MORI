"""Screen all 11 functional wires as three separate planning allocations."""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(BASE.read_text().split('# Endpoints are named')[0],str(BASE),'exec'),globals())
power=float(wire_rows['P_J9']['绝缘外径最大mm']);signal=float(wire_rows['H06']['绝缘外径最大mm'])
specs=[dict(id='CAM_POWER_AND_SPK',count=4,OD=power,z=151.5,bend=14.224,
    members=['P_J18_1','P_J18_2','SPK_1','SPK_2']),
    dict(id='SERVO',count=3,OD=power,z=155.2,bend=14.224,members=['P_J9_1','P_J9_2','P_J9_3']),
    dict(id='UART',count=4,OD=signal,z=158.6,bend=10.922,members=['H06_1','H06_2','H06_3','H06_4'])]
trees={n:s.bvh() for n,s in ss.items()};angles=np.linspace(0,2*math.pi,361)[:-1]
unit=np.column_stack([np.cos(angles),np.sin(angles),np.zeros(len(angles))]);groups=[]
for spec in specs:
    step=spec['OD']+.05
    if spec['count']==3:
        locs=[[step/math.sqrt(3)*math.cos(q),step/math.sqrt(3)*math.sin(q)] for q in [0,2*math.pi/3,4*math.pi/3]]
    else:locs=[[x*step/2,y*step/2] for x in [-1,1] for y in [-1,1]]
    radius=max(math.hypot(*q)+spec['OD']/2 for q in locs);accepted=[];rejected=collections.Counter()
    for rr in np.arange(31.,59.01,.5):
        pp=unit*rr+np.array([0,0,spec['z']]);clear=radius+.3+rr*math.sin(math.pi/360)+1e-4;fail=None
        for name,s in ss.items():
            mask=np.all(pp>=s.lo-clear,axis=1)&np.all(pp<=s.hi+clear,axis=1)
            for p in pp[mask]:
                if trees[name].find_nearest(Vector(p))[3]<clear:fail=name;break
            if fail:break
            if np.all(pp>=s.lo) and np.all(pp<=s.hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(pp[0].tolist())
                if (tiny^s.m).volume()>tiny.volume()*.5:fail=name;break
        if fail:rejected[fail]+=1
        else:accepted.append(float(rr))
    groups.append(dict(**spec,cross_section_centres_mm=locs,enclosing_diameter_mm=2*radius,
        accepted_centre_radii_mm=accepted,certified_external_project_gap_mm=.3,reject_counts=dict(rejected)))
    print('SPLIT_YAW_SPACE',spec['id'],2*radius,accepted,flush=True)
assert sum(s['count'] for s in groups)==11
out=dict(status='PASS' if all(s['accepted_centre_radii_mm'] for s in groups) else 'BLOCKED',
    source_blend_sha256=before,source_wire_csv_sha256=hashlib.sha256(wire_path.read_bytes()).hexdigest(),
    scope='Static annulus screening of 3 planning groups containing all 11 functional conductors',groups=groups,
    selected_harness=False,SPK_gauge='ASSUMED same22AWG sample solely for space allocation',
    source_wire_samples='UNSELECTED catalogue22AWG/26AWG; not actual USB or servo factory cable',
    static_circle_clearance='PASS',yaw_constant_length_motion='NOT_TESTED',individual_lengths='NOT_TESTED',
    real_anchors='NOT_TESTED',main_geometry_changed=False,elapsed_s=time.time()-start,
    limits=['All shields, connector backshells, joins, twisting and real jackets remain unspecified.',
        'Each group is only a circular planning envelope; this is not material or cable selection.',
        'These layers are study planes, not installed fixed points.',
        'No dynamic life, acoustic/EMC separation, continuous routing or access approval.'])
(HERE/'split_yaw_space.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
