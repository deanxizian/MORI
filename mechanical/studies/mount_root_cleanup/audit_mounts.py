"""Read-only root-footprint and current insert-wall audit, excluding intentional bores.
Finite material probes do not qualify strength, tolerance or full minimum walls.
"""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from monocoque_structure import obj
from power_board_mount import mount_sites
study=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
prints={n:a for n,a in solids.items() if a.o.get('category')=='PRINTABLE'}
rows=[]
def probe(name,host,point,axis,radius,bore=1.65,shape='round'):
 # 0.15mm witness entirely behind the mounting face, beyond construction overlaps.
 axis=Vector(axis);a=Vector(point)+axis*.3;tr=Matrix.Translation(a)@axis.to_track_quat('Z','Y').to_matrix().to_4x4()
 if shape=='round':p=manifold.Manifold.cylinder(.15,radius,radius,128)
 else:p=manifold.Manifold.cube((2*radius,2*radius,.15)).translate([-radius,-radius,0])
 p-=manifold.Manifold.cylinder(.15,bore,bore,96)
 p=p.transform(np.array(tr)[:3,:]);missing=max(0,(p-prints[host].m).volume());total=p.volume()
 rows.append({'id':name,'host':host,'root_mm':list(point),'inward_axis':list(axis),'outline':shape,'radius_or_halfwidth_mm':radius,'excluded_intentional_bore_radius_mm':bore,'material_fraction':max(0,1-missing/total),'missing_mm3':missing,'status':'PASS' if missing<.005 else 'FAIL','method':'0.15mm actual-solid backing footprint beyond0.30mm construction overlap; intentional central bore excluded'})
q=P['assembly_completion']['cam_mount'];cam=P['waveshare_detail']['cam'];x,y,z=P['layout']['cam_board_center_from_head_mm'];z+=D['head_z'];h=P['head_print_cleanup']
for i,(u,v) in enumerate(((u,v) for u in [-1,1] for v in [-1,1])):
 probe('CAM_'+str(i),'Pitch_Cradle',(x+u*cam['hole_grid_mm']/2,h['cradle_rear_y_mm']+h['cradle_wall_mm'],z+v*cam['hole_grid_mm']/2),(0,-1,0),q.get('support_side_mm',q['support_diameter_mm'])/2,shape='square' if q.get('support_shape')=='square' else 'round')
dz=P['layout']['deck_z_mm'];dt=P['layout']['deck_thickness_mm'];decktop=dz+dt/2;deckbottom=dz-dt/2
for i,(x,y) in enumerate(( (x,y) for x in [-32.5,32.5] for y in [-59,-29])):probe('Carrier_'+str(i),'Load_Frame',(x,y,decktop),(0,0,-1),3.2)
im=P['layout_cleanup']['imu'];r=np.diag([1.,-1.,-1.]);t=np.array([*im['center_xy_mm'],im['pcb_reference_z_mm']])-r@np.array([10,-8,0.])
for i,(x,y) in enumerate(im['mounting_holes_native_xy_mm']):
 x,y,z=r@np.array([x,-y,0])+t;probe('IMU_'+str(i),'Load_Frame',(x,y,deckbottom),(0,0,1),3.3)
for row in mount_sites():probe('Power_'+row['ref'],'Load_Frame',(*row['xy_mm'],decktop),(0,0,-1),P['layout_cleanup']['power_bay']['local_mount']['support_diameter_mm']/2)
native=json.loads((ROOT/'reports/native_electronics_geometry.json').read_text())
for k,v in native['modules'].items():
 for r in v['mount_sites']:probe(k+'_'+str(r['index']),'Load_Frame',(*r['world_xy_mm'],deckbottom),(0,0,1),P['native_electronics']['buck_mount']['seat_diameter_mm']/2)
# Inventory every current insert and inspect actual radial material at72 samples.
insertrows=[]
for name,s in solids.items():
 if 'Insert' not in name:continue
 tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);areas=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(2*areas[:,None],1e-12);directions={}
 for n,a in zip(ns,areas):
  if n[np.argmax(abs(n))]<0:n=-n
  key=tuple(np.round(n,4));directions[key]=directions.get(key,0)+a
 axis=np.array(max(directions,key=directions.get));axis/=np.linalg.norm(axis);mid=(s.lo+s.hi)/2;proj=(s.v-mid)@axis;length=proj.max()-proj.min();rad=np.max(np.linalg.norm((s.v-mid)-proj[:,None]*axis,axis=1))
 u=np.cross(axis,[1,0,0] if abs(axis[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u);hosts=[]
 for pn,ps in prints.items():
  if np.any(mid<ps.lo-8) or np.any(mid>ps.hi+8):continue
  dists=[];missing=0
  for zz in [-.3*length,0,.3*length]:
   for th in np.linspace(0,2*math.pi,24,endpoint=False):
    dire=u*math.cos(th)+v*math.sin(th);p=mid+axis*zz;hit,normal,ix,dist=ps.bvh().ray_cast(Vector(p),Vector(dire),15)
    if hit is None or dist>4 or np.dot(normal,dire)>0:missing+=1;continue
    out,nn,j,dd=ps.bvh().ray_cast(hit+Vector(dire)*.001,Vector(dire),25)
    if out is not None and np.dot(nn,dire)>0:dists.append((dist+.001+dd-rad,dist+.001+dd-(2.3 if name.startswith(('Frame_Insert','Shell_Insert')) else 1.8)))
  if dists:hosts.append((len(dists),pn,dists,missing))
 hosts.sort(reverse=True)
 if hosts:
  count,pn,dists,missing=hosts[0];actual=min(x[0] for x in dists);prospective=min(x[1] for x in dists)
  insertrows.append({'id':name,'host':pn,'current_nominal_OD_mm':2*rad,'sampled_radial_material_beyond_current_OD_mm':actual,'valid_samples':count,'expected_samples':72,'missing_first_hits':missing,'common_insert_reference_remaining_mm':prospective,'common_insert_reference_min_mm':1.6 if name.startswith(('Frame_Insert','Shell_Insert')) else 1.3,'selected_insert_status':'BLOCKED','limits':'Current nominal envelope only; common insert is a reference compatibility screen, not selected hardware. Missing rays are inconclusive.'})
 else:insertrows.append({'id':name,'status':'NOT_TESTED','reason':'No confident printed host found'})
parts_review=[]
for n,s in prints.items():
 comps=s.m.decompose();parts_review.append({'id':n,'positive_components':sum(a.volume()>.001 for a in comps),'closed_manifold_status':str(s.m.status()),'volume_mm3':s.m.volume(),'purpose':s.o.get('functional_purpose',s.o.get('purpose',s.o.get('integrated_features',''))),'global_minimum_wall_and_strength':'NOT_TESTED'})
report={'revision':P['revision'],'root_footprint_checks':rows,'all_15_prints':parts_review,'current_insert_radial_screen':insertrows,'root_failures':[r['id'] for r in rows if r['status']=='FAIL'],'scope':'19 board-seat roots; all15robot printable solids; all34current insert sites. Separate rectangular/service/actuator connections reviewed with source and existing local validators. No mechanical edits by this script.','limitations':'Not global automatic defect detection; no material/strength qualification. Current insert SKU and remaining mated hardware are unresolved.'}
(study/('audit_'+P['revision'].replace('.','_')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('ROOT_AUDIT',len(rows),report['root_failures'],'PRINTS',len(parts_review),'INSERTS',len(insertrows),flush=True)
