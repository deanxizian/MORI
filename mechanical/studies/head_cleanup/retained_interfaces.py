"""Check whether squaring the remaining lower U-floor corners is harmless.

This is a read-only counterfactual; it does not change or save the assembly.
"""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from validate import Solid,intersect_volume,rigidtr
from structural_simplification import plate

load_collections()
for n in ['DATUMS','DOCK','COUPONS','KEEP_OUT']:COLS[n].hide_viewport=False
assembled();s=P['head_print_cleanup'];hz=D['head_z']
z0,z1=[hz+z for z in s['yoke_floor_z_from_head_mm']]
extra=box('hypothetical_squared_floor',(0,0,(z0+z1)/2),
          (2*s['floor_upper_half_width_mm'],s['floor_depth_mm'],z1-z0))
boolean(extra,plate('current_floor_outline',[
    (-s['floor_lower_half_width_mm'],z0),(s['floor_lower_half_width_mm'],z0),
    (s['floor_upper_half_width_mm'],z1),(-s['floor_upper_half_width_mm'],z1)],0,s['floor_depth_mm']))
boolean(extra,clone(bpy.data.objects[PREFIX+'Pitch_Yoke'],'existing_material'))
fill=Solid(extra);rows=[]
for name in ['Head_Front','Head_Rear']:
    base=Solid(bpy.data.objects[PREFIX+name])
    for pitch in range(-20,26,5):
        shell=Solid(base.o,base,rigidtr(0,pitch));volume=intersect_volume(fill,shell)
        if volume>.01:rows.append({'part':name,'pitch_deg':pitch,'overlap_mm3':round(volume,2)})
save_json(root/'reports/retained_head_interfaces.json',{
    'revision':P['revision'],'status':'TESTED_COUNTERFACTUAL',
    'hypothesis':'Fill only the two tapered lower U-floor corners to make a full84x38mm rectangle. Keep all existing centre holes and interfaces.',
    'added_corner_volume_mm3':round(fill.m.volume(),1),'intersections':rows,
    'decision':'Retain lower clearance slopes' if rows else 'No overlap in this limited test; other checks still required',
    'method':'Actual triangle-solid volume, pitch-20..+25deg in5deg samples, yaw0 (yaw cancels between these two moving groups).',
    'limits':'Counterfactual is not adopted, not a continuous sweep proof or strength calculation.'})
print('RETAINED_INTERFACE_COUNTERFACTUAL',len(rows),'intersections; assembly not saved')
