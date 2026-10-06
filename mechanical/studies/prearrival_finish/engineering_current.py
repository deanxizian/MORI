"""Current-geometry mass/inertia/load screening, with explicit missing inputs.

Run on the saved main assembly after validate.py refreshes mass assumptions.
No assumption is promoted to physical measurement or actuator qualification.
"""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid,volume_moments,rigidtr

load_collections();assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);start_hash=hashlib.sha256(source.read_bytes()).hexdigest()
mass_file=ROOT/'reports/mass_budget.json'
budget=json.loads(mass_file.read_text());entries=[]
for r in budget['density_and_component_mass_assumptions']:
    o=bpy.data.objects[PREFIX+r['id']];s=Solid(o);volume,c,Q=volume_moments(s)
    mass=volume*P['prearrival_completion']['printing']['density_kg_m3_reference']/1e6 if o.get('category')=='PRINTABLE' else r['mass_g']
    raw=(np.eye(3)*np.trace(Q)-Q)*(mass/volume)
    inertia=(raw-mass*(c@c*np.eye(3)-np.outer(c,c)))*1e-9
    assert mass>0 and np.linalg.eigvalsh(inertia).min()>-1e-11,r['id']
    entries.append(dict(id=r['id'],group=o.get('group'),mass_g=mass,COM_mm=c.tolist(),
                        I_COM_kg_m2=inertia.tolist(),category=o.get('category'),
                        basis=r['assumption'],physical_mass='NOT_TESTED'))
ids={r['id'] for r in entries}
expected={o.name.removeprefix(PREFIX) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon'] and o.get('role')=='part'}
coverage=dict(missing=sorted(expected-ids),unexpected=sorted(ids-expected),count=len(entries))

def aggregate(rows,pivot):
    mass=sum(r['mass_g'] for r in rows)
    center=sum(r['mass_g']*np.array(r['COM_mm']) for r in rows)/mass
    inertia=np.zeros((3,3))
    for r in rows:
        d=(np.array(r['COM_mm'])-pivot)/1000
        inertia+=np.array(r['I_COM_kg_m2'])+r['mass_g']/1000*(d@d*np.eye(3)-np.outer(d,d))
    return dict(mass_g=mass,COM_mm=center.tolist(),inertia_about_pivot_kg_m2=inertia.tolist(),pivot_mm=list(pivot))

hp=np.array([0.,0.,D['head_z']]);wp=np.array([0.,0.,D['wheel_z']]);g=9.80665
totals={name:aggregate(rows,pivot) for name,rows,pivot in [
    ('whole',entries,wp),('prints',[r for r in entries if r['category']=='PRINTABLE'],wp),
    ('pitch',[r for r in entries if r['group']=='pitch'],hp),
    ('yaw',[r for r in entries if r['group'] in ['yaw','pitch']],hp)]}
pose_rows=[]
for yd in range(-60,61,10):
    ry=np.array(Matrix.Rotation(math.radians(yd),3,'Z'));pa=ry@np.array([1.,0,0])
    for pd in range(-20,26,5):
        ryp=ry@np.array(Matrix.Rotation(math.radians(pd),3,'X'))
        transformed=[];inertias={'pitch':np.zeros((3,3)),'yaw':np.zeros((3,3))}
        for r in entries:
            moving=r['group'] in ['yaw','pitch'];rot=ryp if r['group']=='pitch' else ry if moving else np.eye(3)
            c=hp+rot@(np.array(r['COM_mm'])-hp) if moving else np.array(r['COM_mm'])
            transformed.append((r,c))
            if moving:
                d=(c-hp)/1000;I=rot@np.array(r['I_COM_kg_m2'])@rot.T+r['mass_g']/1000*(d@d*np.eye(3)-np.outer(d,d))
                inertias['yaw']+=I
                if r['group']=='pitch':inertias['pitch']+=I
        for lean in [-10,0,10]:
            rb=np.array(Matrix.Rotation(math.radians(-lean),3,'X'));coords=[];pt=np.zeros(3);yt=np.zeros(3)
            for r,c in transformed:
                cw=wp+rb@(c-wp);coords.append((r['mass_g'],cw))
                force=np.array([0,0,-r['mass_g']/1000*g]);lever=rb@(c-hp)/1000
                if r['group']=='pitch':pt+=np.cross(lever,force)
                if r['group'] in ['yaw','pitch']:yt+=np.cross(lever,force)
            pose_rows.append(dict(yaw_deg=yd,pitch_deg=pd,body_lean_deg=lean,
                COM_mm=(sum(m*c for m,c in coords)/totals['whole']['mass_g']).tolist(),
                pitch_gravity_Nm=abs(float(pt@(rb@pa))),yaw_gravity_Nm=abs(float(yt@(rb@np.array([0.,0,1.])))),
                pitch_inertia_kg_m2=float(pa@inertias['pitch']@pa),yaw_inertia_kg_m2=float(inertias['yaw'][2,2])))
head=[];torque_ref=.65*g/100
for axis,arm,wire_g in [('pitch',.035,10),('yaw',.05,15)]:
    grav=max(r[axis+'_gravity_Nm'] for r in pose_rows);inertia=max(r[axis+'_inertia_kg_m2'] for r in pose_rows)
    ag=totals[axis];lever=np.linalg.norm((np.array(ag['COM_mm'])-hp)/1000)
    for alpha in [1,5,10,20]:
        nominal=grav+inertia*alpha
        scenario=1.35*nominal+wire_g/1000*(g*arm+arm*arm*alpha)+.01+1.35*ag['mass_g']/1000*.5*lever
        head.append(dict(axis=axis,acceleration_rad_s2=alpha,gravity_max_Nm=grav,
            workspace_max_axis_inertia_kg_m2=inertia,nominal_Nm=nominal,stress_scenario_Nm=scenario,
            vendor_table_reference_Nm=torque_ref,reference_to_scenario_ratio=torque_ref/scenario,
            assumed_wire_g=wire_g,assumed_wire_lever_m=arm,assumed_friction_and_cable_drag_Nm=.01,
            assumed_body_accel_m_s2=.5,actuator_qualification='BLOCKED: matching transmission/duty/cable drag not qualified'))
radius=D['wheel_radius']/1000
wheel_I=sum(r['I_COM_kg_m2'][0][0]+r['mass_g']/1000*((r['COM_mm'][1]/1000)**2+((r['COM_mm'][2]-D['wheel_z'])/1000)**2) for r in entries if r['group'] in ['wheel_L','wheel_R'])
wheel=[]
for scale in [1,1.35]:
    mass=totals['whole']['mass_g']/1000*scale+.04
    for acc in [.25,.5,1.]:
        for grade in [0,5,10]:
            slope=math.radians(grade);rr=.03
            torque=(mass*(acc+g*math.sin(slope)+rr*g*math.cos(slope))*radius+wheel_I*acc/radius)/2
            wheel.append(dict(mass_kg=mass,mass_scale=scale,harness_allowance_g=40,
                acceleration_m_s2=acc,slope_deg=grade,assumed_Crr=rr,tractive_torque_each_Nm=torque,
                qualification='BLOCKED: S288 9V continuous torque/speed/thermal data and balancing reserve are missing'))
checks=dict(source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==start_hash,
            all_physical_actors_accounted_for=not coverage['missing'],positive_inertia=True,
            mass_conservation=abs(sum(r['mass_g'] for r in entries)-totals['whole']['mass_g'])<1e-8,
            head_pose_count=len(pose_rows)==390)
out=dict(revision=P['revision'],source_blend_sha256=start_hash,mass_assumptions_sha256=hashlib.sha256(mass_file.read_bytes()).hexdigest(),
    status='PASS' if all(checks.values()) else 'FAIL',scope='Current nominal mass/inertia and scenario calculations only',
    checks=checks,coverage=coverage,entries=entries,totals=totals,head_poses=pose_rows,head_scenarios=head,wheel_scenarios=wheel,
    whole_mass_target_g=P['validation']['whole_mass_target_g'],
    mass_target_status='BLOCKED' if totals['whole']['mass_g']>P['validation']['whole_mass_target_g'][1] else 'PASS',
    missing_mass=['Unselected external 3S charger','Final braking resistors and heat-isolated mounts','Final fuse/holder','Complete selected harness/mating terminals'],
    limitations=['All masses/loads are documented nominal values or explicit estimates, never measurements.',
        'The 35% scenario and 40g harness allowance are sensitivity cases, not an upper bound on unselected hardware.',
        'Head inertia uses the worst sampled yaw/pitch workspace pose; coupled gyroscopic loads and control transients remain unqualified.',
        'Tractive load excludes balancing control reserve. Peak/stall torque is not continuous available torque.',
        'PA12 strength, fatigue, creep, fastener fit, thermal duty and actual balance need separate verification.'],
    sources={'SCS0009':'mechanical/sources/v1_2/scs0009_spec.pdf A/0 p3; 0.65kgf.cm at4.8V',
             'density':'config/geometry.json#/prearrival_completion/printing; PA12 reference, not JLC batch measurement'})
(HERE/'engineering_current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['revision','status','checks','coverage','totals','mass_target_status']},ensure_ascii=False,indent=2),flush=True)
assert all(checks.values()),checks
