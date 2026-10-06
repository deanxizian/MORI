import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad
from interface_completion import replace_owned
load_collections();assembled();bpy.context.view_layer.update()
s={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
old=s['Drive_Bridge'].m;new=old;rows=[]
for side in ['L','R']:
 for y in [-8,8]:
  name=f'Drive_{side}_{y}_Nut';n=s[name];center=(n.lo+n.hi)/2;sign=1 if y>0 else -1
  # Complete nut envelope plus0.15mm each side; opening follows a required insertion path.
  z0=center[2]-.8-.15;z1=center[2]+.8+.15;x0=center[0]-2.5;x1=center[0]+2.5
  y0,y1=sorted([y,sign*18])
  cutter=manifold.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0]);new-=cutter
  rows.append({'nut':name,'entry_direction':[0,sign,0],'entry_opening_mm':[5,z1-z0],'cutter_bounds_mm':[[x0,y0,z0],[x1,y1,z1]],'thread_center_unchanged':True})
replace_owned('Drive_Bridge',new)
for r in rows:
 n=s[r['nut']];r['entry_hits']=[]
 for d in np.arange(0,18.01,.25):
  m=n.m.translate((np.array(r['entry_direction'])*d).tolist());v=max(0,(m^new).volume())
  if v>.02:r['entry_hits'].append([float(d),v])
 r['rotation_stops_deg']={};p=(n.lo+n.hi)/2
 for sign in [-1,1]:
  for angle in range(1,31):
   tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle*sign),4,'Z')@Matrix.Translation(-Vector(p));v=max(0,(n.m.transform(np.array(tr)[:3,:])^new).volume())
   if v>.02:r['rotation_stops_deg'][str(sign)]=angle;break
 r['status']='PASS' if not r['entry_hits'] and len(r['rotation_stops_deg'])==2 else 'FAIL'
# Bearing bores and surrounding lower saddle must stay exact.
bearingzone=manifold.Manifold.cube([140,50,9],True).translate([0,0,54.5]);delta=old-new
report={'status':'PASS' if all(r['status']=='PASS' for r in rows) and (delta^bearingzone).volume()<.001 and len([m for m in new.decompose() if m.volume()>.01])==1 else 'FAIL','main_updated':False,'rows':rows,'removed_mm3':delta.volume(),'change_below_z59_mm3':max(0,(delta^bearingzone).volume()),'positive_components':sum(m.volume()>.01 for m in new.decompose()),'limits':'Trial side-entry clearances, nominal nut envelope. Load strength, PA12 dimensional shrinkage and fastener torque unqualified.'}
(HERE/'drive_nut_entry.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'drive_nut_entry.blend'));print('DRIVE_NUT_ENTRY',report,flush=True)
# 1:1 exact horizontal section through four nut pockets, with insertion arrows.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="550" viewBox="0 0 1100 550"><rect width="1100" height="550" fill="#f5f7f8"/><g font-family="Arial"><text x="35" y="35" font-size="22">Four M2 nuts: short side entry, no extra part</text>']
for j,(title,m) in enumerate([('Existing closed pocket',old),('Candidate: side entry5.0 x1.9mm',new)]):
 ox=40+j*550;oy=85;scale=10;paths=[]
 region=m.slice(62.25)^manifold.CrossSection.square([18,36]).translate([35.5,-18])
 for poly in region.to_polygons():paths.append('M '+' L '.join(f'{ox+(x-35.5)*scale},{oy+(18-y)*scale}' for x,y in poly)+' Z')
 svg.append(f'<text x="{ox}" y="{oy-15}" font-size="18">{title}</text><path d="{" ".join(paths)}" fill="#7d9ca7" stroke="#294452" fill-rule="evenodd"/>')
 for y in [-8,8]:
  region=s[f'Drive_R_{y}_Nut'].m.slice(62.25);paths=[]
  for poly in region.to_polygons():paths.append('M '+' L '.join(f'{ox+(x-35.5)*scale},{oy+(18-yy)*scale}' for x,yy in poly)+' Z')
  svg.append(f'<path d="{" ".join(paths)}" fill="#dda34d" stroke="#8c641f" fill-rule="evenodd"/>')
 svg.append(f'<text x="{ox}" y="495" font-size="15">Actual horizontal section Z62.25mm; right side shown.</text>')
svg.append('</g></svg>');(HERE/'drive_nut_entry.svg').write_text(''.join(svg))
