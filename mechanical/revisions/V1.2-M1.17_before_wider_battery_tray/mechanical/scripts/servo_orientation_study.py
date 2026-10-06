"""Rigid, real-size yaw-servo orientation screening around the same drive point.

This is a packaging comparison, not a new gearbox or approved mounting design.
The scene is never saved or modified; retained design comes from geometry.json.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid,intersect_volume

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
moving=['Yaw_Servo','Yaw_Output']
# Keep the shaft tip at the existing drive interface: comparing arbitrarily
# translated boxes would hide the transmission/mounting changes required.
tip=Vector((0,0,float(solids['Yaw_Output'].hi[2])))
records=[]
for name,axis,angle in [('upright','Z',0),('horizontal_Y90','Y',90),('inverted_X180','X',180),('clocked_Z180','Z',180)]:
    rotation=Matrix.Rotation(math.radians(angle),4,axis)
    tr=Matrix.Translation(tip)@rotation@Matrix.Translation(-tip)
    transformed=[Solid(solids[n].o,solids[n],tr) for n in moving]
    bad=[]
    for a in transformed:
        for n,b in solids.items():
            if n in moving:continue
            volume=intersect_volume(a,b)
            if volume>.01:bad.append({'moving':a.name,'target':n,'overlap_mm3':round(volume,2)})
    lo=np.min([a.lo for a in transformed],axis=0);hi=np.max([a.hi for a in transformed],axis=0)
    direction=rotation.to_3x3()@Vector((0,0,1))
    records.append({'orientation':name,'rotation_axis':axis,'angle_deg':angle,
        'bounds_xyz_mm':[[round(float(a),2),round(float(b),2)] for a,b in zip(lo,hi)],
        'output_axis':list(direction),'same_vertical_yaw_axis':abs(abs(direction.z)-1)<1e-6,
        'observed_intersections':bad,
        'boundary':'Same fixed output-tip datum and current adjacent geometry. Alternative mounts/transmissions are not designed; collisions do not prove every possible relocation impossible.'})
save_json(ROOT/'reports/servo_orientation_study.json',{
    'revision':P['revision'],'source_model_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),
    'source':'Original-size SCS0009 drawing-based body/ears/output, no rescaling; bought revision and real leads remain unknown.',
    'fixed_output_tip_ground_mm':list(tip),'cases':records,'retained':'upright',
    'decision':'Upright preserves the flat deck and direct vertical drive. Y90 turns the output horizontal and needs a direction-changing transmission. X180 puts the body above the same output into head/yaw space; Z180 changes clocking, not height. User permits all orientations if a later real-hardware layout benefits.',
    'limits':'Rigid packaging screen only. Ear fastening, actual horn/spline engagement, wire exit, bearing axial retention, gear design and dynamics NOT_TESTED.'})
print('SERVO_ORIENTATION_STUDY_COMPLETE',[(r['orientation'],len(r['observed_intersections'])) for r in records])
