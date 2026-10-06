"""Read-only print, insert-seat and mass screening for the current assembly."""
import sys,json,math,copy,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid,volume_moments,rigidtr
from mathutils.bvhtree import BVHTree
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
bom=json.loads((ROOT/'mechanical/reports/bom.json').read_text());names={r['id'] for r in bom if r['group'] not in ['dock','coupon']}
solids={n:Solid(bpy.data.objects[PREFIX+n]) for n in names if bpy.data.objects.get(PREFIX+n)}
prints={n:s for n,s in solids.items() if s.o.get('category')=='PRINTABLE'}
bvhs={n:BVHTree.FromPolygons(s.v.tolist(),s.f.tolist(),all_triangles=True) for n,s in prints.items()}
wall=[]
for name,s in prints.items():
 tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);areas=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(areas[:,None]*2,1e-12)
 idx=np.unique(np.searchsorted(np.cumsum(areas),np.linspace(0,areas.sum(),10002)[1:-1]));rows=[]
 for i in idx:
  p=tri[i].mean(0);n=ns[i];h,hn,other,dist=bvhs[name].ray_cast(Vector(p-n*1e-4),Vector(-n),300)
  if h is not None and other!=i and float(n@np.array(hn))<-.95 and dist>.02:rows.append((float(dist+.0001),p.tolist(),int(i)))
 rows.sort()
 wall.append({'id':name,'opposed_faces_sample_count':len(rows),'sampled_minimum_mm':rows[0][0] if rows else None,'samples_below_1mm':sum(r[0]<1 for r in rows),'samples_below_1_5mm':sum(r[0]<1.5 for r in rows),'critical_sample_positions':rows[:15], 'interpretation':'Finite normal rays to nearly opposite faces; edge/corner/taper classification still required. Not a strength assessment or proof of global minimum.'})
# Existing insert axes derived from planar annular end faces. Do not move them.
insertrows=[]
for name,s in solids.items():
 if 'Insert' not in name:continue
 tri=s.v[s.f];cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cr,axis=1)/2;ns=cr/np.maximum(2*ar[:,None],1e-12)
 groups={}
 for n,a in zip(ns,ar):
  if n[np.argmax(abs(n))]<0:n=-n
  k=tuple(np.round(n,4));groups[k]=groups.get(k,0)+a
 axis=np.array(max(groups,key=groups.get));axis/=np.linalg.norm(axis)
 mid=(s.lo+s.hi)/2;proj=(s.v-mid)@axis;length=proj.max()-proj.min();radius=np.max(np.linalg.norm((s.v-mid)-proj[:,None]*axis,axis=1))
 m3=name.startswith(('Frame_Insert','Shell_Insert'));od,wallmin=(4.6,1.6) if m3 else (3.6,1.3)
 h=[1,0,0] if abs(axis[0])<.9 else [0,1,0];u=np.cross(axis,h);u/=np.linalg.norm(u);v=np.cross(axis,u)
 candidates=[]
 for pn,ps in prints.items():
  if np.any(mid<ps.lo-8) or np.any(mid>ps.hi+8):continue
  distances=[]
  for dz in [-length*.3,0,length*.3]:
   p=mid+dz*axis
   for th in np.arange(0,360,15):
    d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th))
    hit,normal,idx,dist=bvhs[pn].ray_cast(Vector(p),Vector(d),15)
    if hit is None or dist>4 or np.dot(np.array(normal),d)>0:continue
    out,nn,j,dd=bvhs[pn].ray_cast(hit+Vector(d)*.001,Vector(d),25)
    if out is not None and np.dot(np.array(nn),d)>0:distances.append(float(dist+.001+dd-od/2))
  if distances:candidates.append({'part':pn,'valid_radial_rays':len(distances),'minimum_remaining_wall_for_proposed_OD_mm':min(distances)})
 host=max(candidates,key=lambda x:x['valid_radial_rays']) if candidates else None
 insertrows.append({'id':name,'axis':axis.tolist(),'center_mm':mid.tolist(),'old_length_mm':length,'old_outer_diameter_mm':2*radius,'proposed_reference':'FINE SL M3 (OD4.6)' if m3 else 'FINE SL M2 (OD3.6)','proposed_OD_mm':od,'supplier_min_wall_mm':wallmin,'host_screening':host,'status':'NOT_TESTED' if not host else ('FAIL' if host['minimum_remaining_wall_for_proposed_OD_mm']<wallmin else 'NOT_TESTED'),'sampled_radial_wall_meets_reference':bool(host and host['minimum_remaining_wall_for_proposed_OD_mm']>=wallmin),'limits':'Compatibility screening for a proposed larger supplier insert, not failure of a selected/qualified existing part. Missing rays are inconclusive, not automatic FAIL. Even sufficient sampled radial walls leave end wall, insertion access, depth and tolerances NOT_TESTED. This report does not resize an insert or a print.'})
old=json.loads((ROOT/'mechanical/reports/mass_budget.json').read_text())['density_and_component_mass_assumptions'];new=[]
for a in old:
 n=a['id'];b=copy.deepcopy(a)
 if n in prints:
  V,com,Q=volume_moments(prints[n]);mass=V*1.01/1000;ratio=mass/a['mass_g'];b['mass_g']=mass;b['raw_inertia_g_mm2']=(np.array(a['raw_inertia_g_mm2'])*ratio).tolist();b['assumption']='FULL SOLID MJF PA12 volume x1.01g/cm3; prospective density from Ricoh MJF PA12 TDS, not measured JLC batch; no FDM fill factor'
 new.append(b)
totals={}
for lab,groups in [('whole_robot',None),('head_pitch',['pitch']),('head_yaw',['pitch','yaw'])]:
 a=[r for r in new if groups is None or r['group'] in groups];mass=sum(r['mass_g'] for r in a);com=sum(np.array(r['com_mm'])*r['mass_g'] for r in a)/mass
 raw=sum(np.array(r['raw_inertia_g_mm2']) for r in a);ic=raw-mass*(np.dot(com,com)*np.eye(3)-np.outer(com,com));d=com-np.array([0,0,D['head_z']]);ip=ic+mass*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
 totals[lab]={'mass_g':mass,'COM_mm':com.tolist(),'inertia_about_head_pivot_kg_m2':(ip*1e-9).tolist()}
mg=totals['head_pitch']['mass_g']/1000;com=np.array(totals['head_pitch']['COM_mm']);pitchrows=[]
for deg in range(-20,26,5):
 c=np.array(rigidtr(0,deg)@Vector(com));pitchrows.append({'pitch_deg':deg,'gravity_Nm':abs(mg*9.80665*c[1]/1000)})
peak=max(r['gravity_Nm'] for r in pitchrows);inertia=totals['head_pitch']['inertia_about_head_pivot_kg_m2'][0][0]
torque=[{'acceleration_rad_s2':alpha,'nominal_gravity_plus_inertia_Nm':peak+inertia*alpha,'stress_scenario_35pct_mass_plus_0_01Nm_unmeasured_friction':1.35*(peak+inertia*alpha)+.01} for alpha in [1,5,10]]
report={'baseline':P['revision'],'proposal':'PA12 MJF all15 robot prints; no geometry changed','density_source':'https://3d.ricoh.com/wp-content/uploads/2019/10/Ricoh-TDS-MJF-PA12-Web-Final.pdf','density_is_material_family_reference_not_JLC_batch_measurement':True,'totals':totals,'entries':new,'pitch_static_by_pose':pitchrows,'pitch_torque_scenarios':torque,'yaw_inertial_torque_at_10rad_s2_Nm':totals['head_yaw']['inertia_about_head_pivot_kg_m2'][2][2]*10,'limitations':'Other hardware retains explicitly assumed/source nominal masses, wires/connectors/paint missing. 35pct is a scenario not a statistical confidence limit. Friction/loops unknown. Stall torque is not continuous rating. No balancing, fatigue or thermal PASS.'}
report['servo_reference']={'model':'FEETECH SCS0009','received_spec_rated_torque_kgf_cm_at_6V':.75,'current_manufacturer_page_rated_torque_kgf_cm_at_6V':.7,'comparison_uses_lower_reference_Nm':.7*9.80665/100,'spec':'mechanical/sources/v1_2/scs0009_spec.pdf, A/0 p3','page':'https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html','source_conflict':'0.75 in received PDF vs0.7 current table; not silently harmonized; verify ordered revision. Neither is a system-level thermal/duty qualification.'}
(HERE/'pa12_mass_and_torque.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda x:float(x) if isinstance(x,np.generic) else x.tolist()))
(HERE/'opposed_wall_screening.json').write_text(json.dumps(wall,ensure_ascii=False,indent=2,default=lambda x:float(x) if isinstance(x,np.generic) else x.tolist()))
(HERE/'insert_seat_screening.json').write_text(json.dumps(insertrows,ensure_ascii=False,indent=2,default=lambda x:float(x) if isinstance(x,np.generic) else x.tolist()))
print('ENGINEERING_REVIEW_COMPLETE',len(wall),len(insertrows),totals,flush=True)
