"""Final M1.44 readback: approved geometry, capture, installation and pilot walls.

Checks use final saved triangle solids, not a separate regenerated candidate.
"""
from common import *
from validate import Solid,rigidtr
from head_axial_retention import cylinder,annulus,cube,change_region
from validate_head_cleanup import geometry_record
import hashlib

def hit(m,t,threshold=.01):
 a=np.array(m.bounding_box());b=np.array(t.bounding_box())
 if np.any(a[3:]<b[:3]) or np.any(b[3:]<a[:3]):return 0.
 v=max(0.,float((m^t).volume()));return v if v>threshold else 0.

def run():
 load_collections();assembled();bpy.context.view_layer.update()
 q=P['head_axial_retention'];ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
 geom={n:s.m for n,s in ss.items()};yoke=geom['Pitch_Yoke'];base=geom['Yaw_Base'];keeper=geom['Yaw_Anti_Lift_Keeper'];bearing=geom['Yaw_Bearing']
 fasteners={n:geom[n] for n in q['new_ids'] if n!='Yaw_Anti_Lift_Keeper'};axes=q['keeper']['screw_xy_mm']
 changed=['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper']+list(fasteners)
 allowed={frozenset(('Yaw_Base',n)) for n in fasteners if 'Insert' in n}
 static=[]
 for n in changed:
  for other,t in geom.items():
   if n==other or (other in changed and changed.index(other)<changed.index(n)) or frozenset((n,other)) in allowed:continue
   v=hit(geom[n],t)
   if v:static.append(dict(a=n,b=other,mm3=v))
 print('STATIC',len(static),static[:4],flush=True)
 # Scope: changed interfaces versus all bodies at130 combined nominal head poses.
 fixed={n:m for n,m in geom.items() if n not in ss or ss[n].group not in ['yaw','pitch']}
 moving={n:m for n,m in geom.items() if n in ss and ss[n].group in ['yaw','pitch']}
 body_changed={'Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper'}|set(fasteners)
 motion=[]
 for yd in range(-60,61,10):
  for pd in range(-20,26,5):
   moved={n:m.transform(np.array(rigidtr(yd,pd if ss[n].group=='pitch' else 0))[:3,:]) for n,m in moving.items()}
   for n,m in moved.items():
    for other in (fixed if n=='Pitch_Yoke' else body_changed):
     v=hit(m,fixed[other])
     if v:motion.append(dict(yaw=yd,pitch=pd,a=n,b=other,mm3=v))
 print('MOTION',len(motion),motion[:4],flush=True)
 # Positive axial capture: journal can turn normally, but cannot lift out with
 # plate fitted. This is hard-stop geometry, not a stiffness/strength calculation.
 up=[]
 for yd in range(-60,61,10):
  for dz in [.39,.41,1.0]:
   m=yoke.transform(np.array(rigidtr(yd,0))[:3,:]).translate((0,0,dz));v=hit(m,keeper)
   up.append(dict(yaw=yd,lift_mm=dz,overlap_mm3=v,expected='clear' if dz==.39 else 'blocked'))
 # Bench-load C plate laterally before lowering it with the yaw subassembly.
 bench=[]
 bench_names={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output','Yaw_Reaction_Link','Yaw_Horn','Yaw_Lock_Screw'}
 for dy in np.arange(0,60.01,.5):
  for n in bench_names:
   v=hit(keeper.translate((0,float(dy),0)),geom[n])
   if v:bench.append(dict(y_mm=float(dy),fixed=n,mm3=v))
 # Install/remove keeper + yaw-only subassembly together after bridge and upper
 # shell are in place; pitch cradle/head have not yet been installed.
 yawset={n for n,s in ss.items() if s.group=='yaw'}|{'Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
 fixture=set(geom)-yawset-{n for n,s in ss.items() if s.group=='pitch'}-set(fasteners)-{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
 path=[]
 # Existing yaw-only path is already checked; examine every new/changed piece
 # against all relevant obstacles rather than certifying unselected horn parts.
 for dz in np.arange(0,90.01,.5):
  for n in ['Pitch_Yoke','Yaw_Anti_Lift_Keeper']:
   for other in fixture:
    v=hit(geom[n].translate((0,0,float(dz))),geom[other])
    if v:path.append(dict(z_mm=float(dz),moving=n,fixed=other,mm3=v))
 print('PATHS',len(bench),len(path),bench[:2],path[:2],flush=True)
 # Long-leg2AF L-key, before pitch cradle/optics are installed. Nominal2AF
 # handle envelope, all5deg orientations of the20mm transverse leg.
 from interface_completion import axial
 tool=[];screwin=[]
 tool_fixture={n:m for n,m in geom.items() if n not in ss or ss[n].group!='pitch'}
 for i,(x,y) in enumerate(axes):
  n='Yaw_Keeper_Screw_'+str(i)
  # Turn the unpowered yaw seat to60deg for each opposing fastener; pitch
  # head is absent. This exposes each axis beyond the yoke floor.
  tf={k:(v.transform(np.array(rigidtr(60,0))[:3,:]) if k in ss and ss[k].group=='yaw' else v) for k,v in tool_fixture.items() if k!=n}
  p=np.array([x,y,163.55]);a=np.array([0.,0,1.]);shapes=[axial(1.16,70,p+a*35.04,a)]
  for angle in range(0,360,5):
   t=math.radians(angle);b=np.array([math.cos(t),math.sin(t),0]);shapes.append(axial(1.16,20,p+a*(70-1.16)+b*10,b))
  for k,m in enumerate(shapes):
   for other,t in tf.items():
    v=hit(m,t)
    if v:tool.append(dict(screw=n,piece=k,other=other,mm3=v))
  for dz in np.arange(0,35.01,.5):
   for other,t in tf.items():
    v=hit(fasteners[n].translate((0,0,float(dz))),t)
    if v:screwin.append(dict(screw=n,z_mm=float(dz),other=other,mm3=v))
 print('TOOLS',len(tool),len(screwin),tool[:2],screwin[:2],flush=True)
 connect={n:len(geom[n].decompose()) for n in ['Pitch_Yoke','Yaw_Base','Yaw_Anti_Lift_Keeper']}
 cap_ok=all((r['overlap_mm3']==0)==(r['expected']=='clear') for r in up)
 status='PASS' if not any([static,motion,bench,path,tool,screwin]) and cap_ok and all(v==1 for v in connect.values()) else 'FAIL'
 baseline=json.loads((ROOT/'reports/head_retention_baseline_reference.json').read_text());accepted=json.loads((ROOT/'reports/head_retention_approved_reference.json').read_text())
 now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
 changed_ids=sorted(n for n in now if n in baseline['parts'] and now[n]!=baseline['parts'][n] and now[n]['group']!='dock');added=sorted(set(now)-set(baseline['parts']));retired=sorted(set(baseline['parts'])-set(now))
 def solid(data):return manifold.Manifold(manifold.Mesh64(np.array(data['vertices_mm']),np.array(data['triangles'],dtype=np.uint64)))
 from validate_thin_cleanup import prior_solid,declared_ids
 exact=[];local=[]
 for n in q['changed_existing_ids']+q['new_ids']:
  a=solid(accepted[n]);b=prior_solid(n,geom[n]);delta=max(0,(a-b).volume())+max(0,(b-a).volume());exact.append(dict(id=n,symmetric_difference_mm3=delta))
 for n in q['changed_existing_ids']:
  a=solid(baseline[n]);b=prior_solid(n,geom[n]);zone=change_region();local.append(dict(id=n,outside_region_mm3=max(0,((a-b)-zone).volume())+max(0,((b-a)-zone).volume())))
 scope=dict(changed=changed_ids,added=added,retired=retired,accepted_candidate_sha256=accepted['sha256'],exact_candidate_comparison=exact,local_differences=local)
 scopeok=set(changed_ids)==set(q['changed_existing_ids'])|declared_p5r7_changes()|declared_rear_mesh_repair_changes()|declared_ids()|declared_camera_cam_changes()|(declared_neck_capacity_changes()&set(baseline['parts'])) and set(added)==set(q['new_ids'])|declared_p5r7_additions() and not retired and accepted['sha256']==q['candidate_sha256'] and max(r['symmetric_difference_mm3'] for r in exact)<.03 and max(r['outside_region_mm3'] for r in local)<.03
 pilots=[];bz=D['yaw_bearing_z'];kb=bz+q['keeper']['bottom_from_bearing_mm'];bottom=bz+q['fasteners']['pilot_bottom_from_bearing_mm']
 for i,(x,y) in enumerate(axes):
  walls=[];broken=0
  for z in np.linspace(bottom+.25,kb-.25,12):
   for th in range(0,360,5):
    d=np.array([math.cos(math.radians(th)),math.sin(math.radians(th)),0.]);p=np.array([x,y,z]);hs=base.ray_cast(p.tolist(),(p+d*100).tolist())
    if len(hs)<2:broken+=1
    else:walls.append((hs[1].distance-hs[0].distance)*100)
  # Actual solid rays through the blind floor (five points across pilot).
  caps=[]
  for dx,dy in [(0,0),(.7,0),(-.7,0),(0,.7),(0,-.7)]:
   hs=base.ray_cast([x+dx,y+dy,bottom-.01],[x+dx,y+dy,bottom-100.01])
   caps.append(hs[0].distance*100+.01 if hs else 0)
  screw_bottom=min(v.co.z for v in ss['Yaw_Keeper_Screw_'+str(i)].o.data.vertices)
  pilots.append(dict(id='Yaw_Keeper_Insert_'+str(i),minimum_wall_mm=min(walls) if walls else 0,broken_radial_rays=broken,minimum_blind_floor_mm=min(caps),screw_tip_clearance_mm=screw_bottom-bottom,nominal_thread_engagement_mm=4))
 pilotok=all(r['minimum_wall_mm']>=1.6 and r['broken_radial_rays']==0 and r['minimum_blind_floor_mm']>=1 and r['screw_tip_clearance_mm']>=.15 for r in pilots)
 stop_rows=[]
 for sign in [-1,1]:
  onset=None
  for yd in np.arange(60,66.01,.25):
   m=yoke.transform(np.array(rigidtr(sign*yd,0))[:3,:]);v=hit(m,base)
   if v:onset=float(sign*yd);break
  stop_rows.append(onset)
 stopok=all(v is not None and 64<=abs(v)<=64.5 for v in stop_rows)
 bt=bz+3.5;bb=bz-3.5
 if P.get('neck_harness_capacity',{}).get('enabled'):
  areas=dict(rotor_shoulder_mm2=float((yoke^annulus(16,15.3,bt,bt+.01)).volume()/.01),housing_outer_ring_mm2=float((base^annulus(20.7,20,bb-.01,bb)).volume()/.01))
 else:
  areas=dict(rotor_shoulder_mm2=float((yoke^annulus(11,10.3,bt,bt+.01)).volume()/.01),housing_outer_ring_mm2=float((base^annulus(15.7,15,bb-.01,bb)).volume()/.01))
 result=dict(revision=P['revision'],status='PASS' if status=='PASS' and scopeok and pilotok and stopok and min(areas.values())>30 else 'FAIL',source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),blender_version=bpy.app.version_string,scope=scope,scope_status='PASS' if scopeok else 'FAIL',static_hits=static,motion=dict(poses=130,hits=motion),capture=dict(status='PASS' if cap_ok else 'FAIL',samples=up),bench_plate_side_entry=dict(samples=121,hits=bench),paired_vertical_insertion=dict(samples=181,hits=path),tool_assembly_yaw_deg=60,tool_hits=tool,screw_entry_hits=screwin,connected_components=connect,pilot_status='PASS' if pilotok else 'FAIL',pilots=pilots,mechanical_stop_onsets_deg=stop_rows,nominal_abutment_contact_areas=areas,limits=q['limits'])
 save_json(ROOT/'reports/head_axial_retention_validation.json',result)
 print('HEAD_RETENTION_VALIDATION',result['status'],'scope',scopeok,'pilots',pilotok,flush=True)
 return result

if __name__=='__main__':
 result=run()
 if result['status']!='PASS':raise SystemExit(1)
