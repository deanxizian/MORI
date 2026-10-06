"""Independent PA12 fit coupons. Does not change the robot or production geometry."""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from export import write_stl,read_stl,topology
from validate import Solid
ROOT=PROJECT
setup_scene();material('frame',(.24,.32,.35));out=HERE/'jlc_coupons';out.mkdir(exist_ok=True);rows=[]
def plate_coupon(name,xyz,holes,notes):
 o=box(name,(0,0,xyz[2]/2),xyz)
 # The cropped lower-left corner identifies row/column origin without tiny printed text.
 boolean(o,box('corner_index',(-xyz[0]/2,-xyz[1]/2,xyz[2]/2),(4,4,xyz[2]+2)))
 for h in holes:
  depth=h.get('depth',xyz[2]+2);z=xyz[2]-depth/2+.001
  boolean(o,cyl('trial_hole',(h['x'],h['y'],z),h['diameter']/2,depth+.002,n=96))
  if 'counterbore' in h:
   d,height=h['counterbore'];boolean(o,cyl('spotface',(h['x'],h['y'],xyz[2]-height/2+.001),d/2,height+.002,n=96))
 finish(o,'PRINTABLE',name+' / 嘉立创PA12试片','frame','coupon',True,note=notes)
 o['role']='coupon';o['data_status']='ASSUMED';o['material_selection']='Recommended MJF PA12; not a material qualification';o['robot_part']=False
 rows.append({'id':name,'holes':holes,'dimensions_mm':xyz,'instructions':notes});return o
plate_coupon('C01_M2_inserts',[65,16,7],[dict(x=(i-2)*12,y=0,diameter=d,depth=4) for i,d in enumerate([3.,3.1,3.2,3.3,3.4])], 'FINE SL M2 reference OD3.6/L3.0; supplier pilot3.2. Five independent holes from left to right. Measure before fitting; do not force or heat a resin sample. Keep3mm closed bottom.')
plate_coupon('C02_M3_inserts',[75,18,8],[dict(x=(i-2)*14,y=0,diameter=d,depth=5) for i,d in enumerate([3.8,3.9,4.,4.1,4.2])], 'FINE SL M3 reference OD4.6/L4.0; supplier pilot4.0. Five independent holes left to right;3mm bottom. Record installed height, turning and pullout after cooling. No load rating inferred.')
plate_coupon('C03_small_bearings',[90,45,7],[dict(x=(i-1.5)*21,y=y,diameter=d) for y,ds in [(-11,[11.9,12.,12.1,12.2]),(11,[12.9,13.,13.1,13.2])] for i,d in enumerate(ds)], 'Near index corner:12mm-OD pitch bearing row. Far row:13mm-OD wheel bearing. Through bores screen radial fit only; no axial shoulder/preload qualification. Press outer race only.')
plate_coupon('C04_yaw_bearing',[126,42,9],[dict(x=(i-1)*41,y=0,diameter=d) for i,d in enumerate([31.9,32.1,32.3])], '32mm-OD yaw bearing bore sweep; actual batch dimensions determine selection. Do not choose a final bore by nominal STL alone. Through bores do not certify axial retention.')
o=plate_coupon('C05_yaw_journal',[90,32,3],[], 'Three20mm-class integral journals19.8/20.0/20.2 left to right,8mm exposed height. Seat bearing without force; record radial wobble/rotation. Candidate fit gauge, not the robot journal.')
for i,d in enumerate([19.8,20.,20.2]):union(o,cyl('journal',((i-1)*29,0,7),d/2,8,n=128))
rows[-1]['journal_diameters_mm']=[19.8,20.,20.2]
plate_coupon('C06_screw_bearing',[58,22,6],[dict(x=x,y=0,diameter=d,counterbore=cb) for x,d,cb in [(-21,2.2,[4.2,1.6]),(-7,2.4,[4.2,1.6]),(7,3.2,[6.2,2.0]),(21,3.4,[6.2,3.2])]], 'M2 GB823 small pan head and M3 selected low/button/socket heads; verify full annular seating and driver access. Measure counterbore depth; no thread printed. Blank drawing is authoritative for dimensions.')
o=plate_coupon('C07_M2_nut_pockets',[48,16,6],[dict(x=x,y=0,diameter=2.2) for x in [-14,0,14]], 'ThreeM2 hex nut pockets AF4.2/4.4/4.6,1.8mm deep, left to right. Supplier nut AF4max,height1.6max. Inspect fit/anti-rotation after depowdering; trial only.')
for x,af in zip([-14,0,14],[4.2,4.4,4.6]):boolean(o,ring('nut_trial',(x,0,5.101),af/math.sqrt(3),.05,1.802,n=6))
rows[-1]['nut_pockets_AF_mm']=[4.2,4.4,4.6]
for row in rows:
 o=bpy.data.objects[PREFIX+row['id']];fn=out/(row['id']+'.stl');write_stl(o,fn);v,f,n=read_stl(fn);t=topology(v,f,n);m=Solid(o).m
 row['base_plate_dimensions_mm']=row['dimensions_mm'];row['dimensions_mm']=[round(float(b-a),4) for a,b in bounds(o)]
 row.update(file=str(fn.relative_to(ROOT)),sha256=hashlib.sha256(fn.read_bytes()).hexdigest(),topology=t,connected_components=len(m.decompose()),volume_cm3=m.volume()/1000)
 row['status']='PASS' if len(m.decompose())==1 and all(t[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles','inconsistent_stl_normals']) else 'FAIL'
report={'baseline':P['revision'],'material_recommendation':'JLC MJF PA12','status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','units':'mm','robot_parts_added':0,'source_dimensions':'FINE SL/SHK insert drawing; retained20x32x7/5x12x4/6x13x5 bearing interfaces; GB823 envelope; all fits are trial values','manufacturing_scope':'Local calibration coupons only; not approval to print the robot or place an order','orientation':'Shown +Z, flat bottom down is a comparison datum. Ask JLC to keep similar process/orientation between coupons and affected interfaces. MJF vendor controls nesting; no support/G-code supplied.','parts':rows}
(out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Arrange copies for an overview without affecting separately exported local STL coordinates.
for i,row in enumerate(rows):
 o=bpy.data.objects[PREFIX+row['id']];o.location.x+=(i%2)*150;o.location.y+=(i//2)*64
bpy.ops.wm.save_as_mainfile(filepath=str(out/'MORI_PA12_fit_coupons.blend'))
print('JLC_COUPONS_COMPLETE',report['status'],len(rows),flush=True)
