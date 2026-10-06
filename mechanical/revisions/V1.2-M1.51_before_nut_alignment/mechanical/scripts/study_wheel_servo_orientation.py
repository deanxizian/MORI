"""Real-size wheel-servo packaging comparisons, with grounded axle unchanged.

This is an orientation study, not a replacement for an assembled drive frame.
Every existing support conflict is recorded separately, never waived as PASS.
"""
import sys, json, hashlib, math, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
from validate import Solid, intersect_volume
import build

out=ROOT/'studies/wheel_servo_orientation';out.mkdir(parents=True,exist_ok=True)
source=ROOT/'mori_v1_2.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
moving_names={n for n in solids if n.startswith(('Drive_Motor_','S288_Output_'))}
supports={n for n in solids if n=='Drive_Bridge' or n.startswith('Motor_Retainer')}
routes=[Solid(o) for o in bpy.context.scene.objects if o.get('role')=='routing']
inner_obj=build.body_outer('wheel_study_nominal_inner',P['shell_thickness_mm']);inside=Solid(inner_obj)
wz=D['wheel_z'];cx=P['drive']['motor_center_abs_x_mm']
cases=[('current', 'X',0,'axle'),('down_180','X',180,'axle'),('forward_90','X',-90,'axle'),
       ('rearward_90','X',90,'axle'),('opposed_90','X',90,'opposed'),
       ('swap_ends_same_center','Z',180,'center'),('swap_ends_and_down','Y',180,'center'),
       ('flip_about_outer_output_face','Z',180,'output_face')]
records=[];started=time.time()
for name,axis,angle,pivot_rule in cases:
    transformed=[];transforms={}
    for side,sign in [('L',-1),('R',1)]:
        pivot=Vector((sign*(27 if pivot_rule=='output_face' else cx),0,wz))
        ang=angle*sign if pivot_rule=='opposed' else angle
        tr=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(ang),4,axis)@Matrix.Translation(-pivot)
        transforms[side]=[list(row) for row in tr]
        transformed.extend(Solid(solids[n].o,solids[n],tr) for n in sorted(moving_names) if ('_'+side) in n)
    hard=[];mount=[];wires=[]
    for a in transformed:
        for n,b in solids.items():
            if n in moving_names:continue
            vol=intersect_volume(a,b)
            if vol>P['validation']['collision_volume_tolerance_mm3']:
                row={'moving':a.name,'target':n,'overlap_mm3':round(vol,3)}
                (mount if n in supports else hard).append(row)
        for b in routes:
            vol=intersect_volume(a,b)
            if vol>P['validation']['collision_volume_tolerance_mm3']:
                wires.append({'moving':a.name,'route':b.name,'overlap_mm3':round(vol,3)})
    for i,a in enumerate(transformed):
        for b in transformed[i+1:]:
            vol=intersect_volume(a,b)
            if vol>P['validation']['collision_volume_tolerance_mm3']:
                hard.append({'moving':a.name,'target':b.name,'overlap_mm3':round(vol,3)})
    bodies=[a for a in transformed if a.name.startswith('Drive_Motor_')]
    lo=np.min([a.lo for a in bodies],axis=0);hi=np.max([a.hi for a in bodies],axis=0)
    lower_shell=solids['Body_Lower'];wall=[]
    for a in bodies:
        wall.append({'id':a.name,'gap_to_actual_lower_shell_mm':round(float(a.m.min_gap(lower_shell.m,100)),3),
                     'outside_nominal_inner_body_volume_mm3':round(max(0,(a.m-inside.m).volume()),3)})
    l=next(a for a in bodies if a.name.endswith('_L'));r=next(a for a in bodies if a.name.endswith('_R'))
    baseline_top=max(solids[n].hi[2] for n in ['Drive_Motor_L','Drive_Motor_R'])
    mass_report=json.loads((ROOT/'reports/mass_budget.json').read_text());entries=mass_report['density_and_component_mass_assumptions'];total=sum(e['mass_g'] for e in entries)
    dz_mass=0
    for e in entries:
        if e['id'] in moving_names:
            side='L' if '_L' in e['id'] else 'R';v=Vector(e['com_mm']);v2=Matrix(transforms[side])@v
            dz_mass+=e['mass_g']*(v2.z-v.z)
    tilt=[]
    for tilt_deg in range(-15,16):
        center=Vector((0,0,wz));tr=Matrix.Translation(center)@Matrix.Rotation(math.radians(tilt_deg),4,'X')@Matrix.Translation(-center)
        tilt.append({'body_tilt_deg':tilt_deg,'motor_bottom_ground_mm':round(float(min(Solid(a.o,a,tr).lo[2] for a in bodies)),3)})
    records.append({'case':name,'axis':axis,'angle_deg':angle,'pivot_rule':pivot_rule,
        'transforms_world':transforms,'axle_ground_height_mm':wz,
        'motor_body_bounds_xyz_mm':[[round(float(a),3),round(float(b),3)] for a,b in zip(lo,hi)],
        'body_to_body_center_gap_x_mm':round(float(r.lo[0]-l.hi[0]),3),
        'potential_top_height_gain_mm_before_mount_redesign':round(float(baseline_top-hi[2]),3),
        'lower_shell_clearance':wall,'other_part_conflicts':hard,'old_support_conflicts':mount,'existing_route_conflicts':wires,
        'motor_only_COM_change_mm_assumed_other_parts_unchanged':round(dz_mass/total,2),
        'tilt_samples':tilt,'minimum_tilted_motor_ground_mm':min(v['motor_bottom_ground_mm'] for v in tilt),
        'assembly_status':'BASELINE_REFERENCE' if name=='current' else 'NOT_AN_ASSEMBLED_DESIGN'})
    print('CASE',name, 'Z',records[-1]['motor_body_bounds_xyz_mm'][2], 'shell',wall,'other',len(hard),'mount',len(mount),flush=True)
result={'source_revision':P['revision'],'source_model_sha256':digest,'study_status':'ORIENTATION_ONLY',
        'wheel_diameter_mm':P['wheel_diameter_mm'],'unchanged_axle_height_mm':wz,'cases':records,
        'method':'Rigid transforms of original-size S288 body and BOTH opposed output envelopes; actual Manifold solid intersections and min_gap. Nominal inner-skin containment checked on body cases. Bearings, axles, wheels, battery and shells left at their source positions. Thirty-one body-tilt samples per case; no continuous/dynamic proof.',
        'limits':['Old drive frame/retainer must be redesigned for a selected orientation. No collision exemption certifies an assembly.',
                  'Reported top gain is the motor envelope alone, not a verified battery lowering distance or usable PCB volume.',
                  'S288 model is a dimensioned simplification; wire outlet/connector approach and selected unit not measured.',
                  'PCB/battery envelopes remain provisional; output adapter, fastening, print strength, thermal and real balance unqualified.'],
        'elapsed_s':round(time.time()-started,1)}
save_json(out/'orientation_study.json',result)
bpy.data.objects.remove(inner_obj,do_unlink=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
print('WHEEL_SERVO_STUDY_COMPLETE',flush=True)
