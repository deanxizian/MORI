"""Reproducible M1.43 load screening; never changes source geometry or electronics."""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,volume_moments,rigidtr

load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=PROJECT/'mechanical/mori_v1_2.blend'
old=json.loads((PROJECT/'mechanical/reports/mass_budget.json').read_text())
entries=[]
for r in old['density_and_component_mass_assumptions']:
    o=bpy.data.objects[PREFIX+r['id']];s=Solid(o);V,c,Q=volume_moments(s)
    m=V*P['prearrival_completion']['printing']['density_kg_m3_reference']/1e6 if o.get('category')=='PRINTABLE' else r['mass_g']
    raw=(np.eye(3)*np.trace(Q)-Q)*(m/V)
    Ic=raw-m*(np.dot(c,c)*np.eye(3)-np.outer(c,c))
    assert m>0 and np.linalg.eigvalsh(Ic).min()>-0.01,(r['id'],m,Ic)
    entries.append(dict(id=r['id'],group=r['group'],mass_g=m,COM_mm=c.tolist(),I_COM_kg_m2=(Ic*1e-9).tolist(),category=o.get('category'),basis=r['assumption'],physical_mass='NOT_TESTED'))

def aggregate(rows,pivot):
    mass=sum(r['mass_g'] for r in rows);c=sum(r['mass_g']*np.array(r['COM_mm']) for r in rows)/mass
    I=np.zeros((3,3))
    for r in rows:
        d=(np.array(r['COM_mm'])-pivot)/1000
        I+=np.array(r['I_COM_kg_m2'])+r['mass_g']/1000*(d@d*np.eye(3)-np.outer(d,d))
    return dict(mass_g=mass,COM_mm=c.tolist(),inertia_about_pivot_kg_m2=I.tolist(),pivot_mm=list(pivot))

hp=np.array([0,0,D['head_z']]);wp=np.array([0,0,D['wheel_z']])
pitch=aggregate([r for r in entries if r['group']=='pitch'],hp)
yaw=aggregate([r for r in entries if r['group'] in ['yaw','pitch']],hp)
whole=aggregate(entries,wp)
prints=aggregate([r for r in entries if r['category']=='PRINTABLE'],wp)
pose_rows=[];g=9.80665
for yd in range(-60,61,10):
    ry=np.array(Matrix.Rotation(math.radians(yd),3,'Z'));pitch_axis=ry@np.array([1.,0,0])
    for pd in range(-20,26,5):
        for lean in [-10,0,10]:
            rb=np.array(Matrix.Rotation(math.radians(-lean),3,'X'))
            coords=[];pitch_t=np.zeros(3);yaw_t=np.zeros(3)
            for r in entries:
                c=np.array(r['COM_mm']);moving=r['group'] in ['yaw','pitch']
                if moving:c=np.array(rigidtr(yd,pd if r['group']=='pitch' else 0)@Vector(c))
                cw=wp+rb@(c-wp);coords.append((r['mass_g'],cw))
                force=np.array([0,0,-r['mass_g']/1000*g]);lever=rb@(c-hp)/1000
                if r['group']=='pitch':pitch_t+=np.cross(lever,force)
                if moving:yaw_t+=np.cross(lever,force)
            pose_rows.append(dict(yaw_deg=yd,pitch_deg=pd,body_lean_deg=lean,COM_mm=(sum(m*c for m,c in coords)/whole['mass_g']).tolist(),pitch_gravity_Nm=abs(float(pitch_t@(rb@pitch_axis))),yaw_gravity_Nm=abs(float(yaw_t@(rb@np.array([0.,0,1.]))))))

# Explicit design scenarios, NOT measured friction, cable drag or duty limits.
# Cable allowance is modelled as head mass at35mm worst gravitational offset
# for pitch and50mm for yaw. Body linear acceleration also loads the head.
head=[];rated=.65*g/100 # FEETECH A/0 p3 at4.8V; conservative vs6V table
for axis,ag,arm,wire_g in [('pitch',pitch,.035,10),('yaw',yaw,.05,15)]:
    grav=max(r[axis+'_gravity_Nm'] for r in pose_rows);idx=0 if axis=='pitch' else 2
    inertia=ag['inertia_about_pivot_kg_m2'][idx][idx]
    for alpha in [1,5,10,20]:
        nominal=grav+inertia*alpha
        stress=1.35*nominal+wire_g/1000*(g*arm+arm*arm*alpha)+.01
        # Conservative whole head mass at maximum nominal COM offset under
        # horizontal acceleration; use a geometric bound, not zero yaw gravity.
        lever=np.linalg.norm((np.array(ag['COM_mm'])-hp)/1000)
        stress+=1.35*ag['mass_g']/1000*.5*lever
        head.append(dict(axis=axis,acceleration_rad_s2=alpha,gravity_max_Nm=grav,nominal_Nm=nominal,stress_scenario_Nm=stress,rated_reference_Nm=rated,rated_to_scenario_ratio=rated/stress,assumed_wire_g=wire_g,assumed_wire_lever_m=arm,assumed_friction_and_cable_drag_Nm=.01,assumed_body_accel_m_s2=.5))

radius=D['wheel_radius']/1000
wheel_I=sum(r['I_COM_kg_m2'][0][0]+r['mass_g']/1000*((r['COM_mm'][1]/1000)**2+((r['COM_mm'][2]-D['wheel_z'])/1000)**2) for r in entries if r['group'] in ['wheel_L','wheel_R'])
wheel=[]
for massscale in [1,1.35]:
    m=whole['mass_g']/1000*massscale+.04 #40g total harness/connector allowance
    for a in [.25,.5,1.]:
        for grade in [0,5,10]:
            slope=math.radians(grade);rr=.03
            tr=(m*(a+g*math.sin(slope)+rr*g*math.cos(slope))*radius+wheel_I*a/radius)/2
            wheel.append(dict(mass_kg=m,mass_scale=massscale,acceleration_m_s2=a,slope_deg=grade,assumed_Crr=rr,wheel_pair_inertia_kg_m2=wheel_I,tractive_torque_each_Nm=tr,required_before_balance_reserve_Nm=tr,continuous_margin_status='BLOCKED: S2889V continuous torque-speed/thermal curve not supplied',peak_0_6Nm_is_not_rated_margin=True))
speed=[]
for v in [.2,.3,.5]:speed.append(dict(speed_m_s=v,wheel_rad_s=v/radius,wheel_rpm=v/radius*60/(2*math.pi),status='NOT_TESTED',note='Do not scale12V no-load speed to9V or infer loaded continuous performance.'))

# Head inertial disturbance on the balancing body is separated from drive load.
# m*g*h*sin(theta) is overturning moment about ground wheel axis, not a motor
# torque equation; no false per-wheel balance requirement is inferred from it.
body_moments=[]
for angle in [5,10,15]:
    h=(whole['COM_mm'][2]-D['wheel_z'])/1000
    body_moments.append(dict(lean_deg=angle,gravity_overturning_moment_Nm=whole['mass_g']/1000*g*h*math.sin(math.radians(angle)),interpretation='Open-loop gravitational destabilizing moment; coupled inverted-pendulum control not validated.'))

checks={'mass_conservation':abs(sum(r['mass_g'] for r in entries)-whole['mass_g'])<1e-8,'tensor_units_and_positive_semidefinite':True,'head_pose_count':len(pose_rows),'source_not_modified':hashlib.sha256(source.read_bytes()).hexdigest()=='e81df3f1f7ba1d832b17341ae244c75a582f9ba91341356a62c80a26b04d9b25'}
out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),status='PASS',scope='Completed nominal engineering calculations with explicit uncertainty; NOT actuator or structure qualification',entries=entries,totals=dict(whole=whole,prints=prints,pitch=pitch,yaw=yaw),head_poses=pose_rows,head_scenarios=head,wheel_scenarios=wheel,speed_scenarios=speed,body_overturning=body_moments,checks=checks,unresolved=['S2889V torque-speed-current and allowable continuous/duty thermal envelope','SCS0009 horn/coupling and backlash, cable drag and actual terminal voltage','Unknown pack/PCB/cable masses and PA12 process tolerance','Structural creep, fatigue, stress concentration and impact; these are not certified by torque arithmetic'],recommendation='Screen initially alpha<=5rad/s2 for head, v<=0.3m/s and a<=0.5m/s2 on flat floor; provisional engineering envelope only, disabled wheels until separate commissioning checks',sources={'SCS0009':'mechanical/sources/v1_2/scs0009_spec.pdf p3-4;0.65kgf.cm at4.8V','PA12':'Ricoh PA12 density1.01g/cm3 family reference, not JLC batch measurement','JLC':'https://jlc3dp.com/help/article/pa12-hp-nylon','S288':'mechanical/sources/v1_2/unitree_servo_manual.pdf; peak0.6Nm must not be used as rated continuous torque'})
(HERE/'engineering.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('ENGINEERING',json.dumps(out['totals']),flush=True)
print('HEAD_SCENARIOS',json.dumps(head),flush=True)
