"""Unadopted socket stack / optional straight E header. Native PCB stays intact."""
import sys,json,hashlib,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,rigidtr,broad
from native_electronics import board_transform
from monocoque_structure import source_build
from layout_cleanup import mm_mesh
from render import camera
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();source_build().materials();bpy.context.view_layer.update()
original={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
c=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text());pins=json.loads((HERE/'weact_pin_alignment.json').read_text())
wr=np.array([[0,-1,0],[-1,0,0],[0,0,-1.]])
mp=P['layout_cleanup']['motion_carrier'];wt=np.array([*mp['center_xy_mm'],mp['pcb_reference_z_mm']])+[61.016,116.078,1.595+mp['core_socket_height_assumed_mm']]
# Actual native substrate top is122.600; fixed catalogue socket8.5 + E male insulator2.54.
carrier_top=122.6;core_face=carrier_top+8.5+2.54;dz=core_face-wt[2];wt[2]=core_face
ms=[];vv=[];ff=[];fallbacks=[]
for i,s in enumerate(c['solids']):
 if i==32:continue
 v=np.array(s['vertices_mm'])@wr.T+wt;f=np.array(s['triangles'],dtype=np.uint64);m=manifold.Manifold(manifold.Mesh64(v,f))
 if m.status()!=manifold.Error.NoError:
  lo=v.min(0)-.001;hi=v.max(0)+.001;m=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());fallbacks.append(i)
 ms.append(m);ff.extend((f+len(vv)).tolist());vv.extend(v.tolist())
core=mesh('STUDY_WeAct_Straight_E_Core',vv,ff);finish(core,'PURCHASED_REFERENCE','WeAct 原厂CAD / E直针配置待确认','pcb','body',False,role='study')
core['source_sha256']=c['source_sha256'];cm=manifold.Manifold.batch_boolean(ms,manifold.OpType.Add);d=cm.to_mesh64();cp=HERE/'socket_core_solid.json';cp.write_text(json.dumps({'vertices_mm':d.vert_properties[:,:3].tolist(),'triangles':d.tri_verts.tolist()}));core['validation_solid_source']=str(cp.relative_to(PROJECT))
new={core.name.removeprefix(PREFIX):Solid(core)};socketrows=[]
xyE=next(r['pin_xy'] for r in pins['source_pins'] if r['solid']==32)
# E straight pin is an explicit proposal, not silently substituted vendor CAD.
em=manifold.Manifold.cube([5.08,10.16,2.54],True).translate([np.mean([p[0] for p in xyE]),np.mean([p[1] for p in xyE]),core_face-1.27])
for x,y in xyE:em=em+manifold.Manifold.cube([.64,.64,11.54],True).translate([x,y,core_face+(3-8.54)/2])
e=mm_mesh('STUDY_E_Straight_Header',em);finish(e,'PURCHASED_REFERENCE','WR-PHD 61300821121 / E向下直针候选','metal','body',False,role='study');new[e.name.removeprefix(PREFIX)]=Solid(e)
for label,prefixes,sku in [('AC',['A','C'],'61303021821'),('BD',['B','D'],'61303021821'),('E',[],'61300821821')]:
 xy=[p['xy'] for p in pins['native_pads'] if p['id'][0] in prefixes] if prefixes else xyE
 pts=np.array(xy);center=pts.mean(0);longx=label!='E';size=[38.6,5.08,8.5] if longx else [5.08,10.66,8.5]
 body=manifold.Manifold.cube(size,True).translate([*center,carrier_top+4.25]);tails=[]
 for x,y in xy:
  # Cavity nominal opening only; contact spring surface intentionally omitted.
  body=body-manifold.Manifold.cube([.74,.74,6.35],True).translate([x,y,carrier_top+8.5-6.35/2+.01])
  tails.append(manifold.Manifold.cube([.45,.3,3.1],True).translate([x,y,carrier_top-1.55]))
 body=body+manifold.Manifold.batch_boolean(tails,manifold.OpType.Add)
 o=mm_mesh('STUDY_Socket_'+label,body);finish(o,'PURCHASED_REFERENCE','WR-PHD '+sku+' / 排母候选','dark','body',False,role='study');o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='DOCUMENTED_OUTER_ENVELOPE; contact and tail cross section schematic';new[o.name.removeprefix(PREFIX)]=Solid(o)
 socketrows.append({'id':label,'sku':sku,'pins':len(xy),'center_xy_mm':center.tolist(),'body_xyz_mm':size,'tail_length_mm':3.1,'source_url':'https://www.we-online.com/components/products/datasheet/'+sku+'.pdf','qualification':'E requires corrected carrier hole pattern and approved straight header; contact/retention unmeasured' if label=='E' else 'Official A-D pin centers align with native carrier, nominal untrimmed6mm pins insert5.96mm'})
# Check against complete current hardware, including unmodified carrier E holes.
hits=[]
for n,a in new.items():
 for k,b in original.items():
  if k=='MCU_Motion':continue
  if broad(a,b):
   v=max(0,(a.m^b.m).volume())
   if v>.02:hits.append({'candidate':n,'target':k,'overlap_mm3':v,'interpretation':'E tails meet uncorrected PCB substrate; do not waive actual board mismatch' if n=='STUDY_Socket_E' and k=='MCU_Carrier' else 'REVIEW'})
# Only E substrate tails are a known pending native-board defect, not a successful fit.
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  for k,s in original.items():
   if s.group not in ['yaw','pitch']:continue
   b=Solid(s.o,s,rigidtr(yaw,pitch if s.group=='pitch' else 0))
   for n,a in new.items():
    if broad(a,b):
     v=max(0,(a.m^b.m).volume())
     if v>.02:motion.append({'yaw':yaw,'pitch':pitch,'candidate':n,'target':k,'overlap_mm3':v})
# Rigid module removal before bridge/head/upper-shell assembly; sockets remain on carrier.
bench={n:s for n,s in original.items() if n in ['MCU_Carrier','Load_Frame'] or n.startswith('Carrier_')};approach=[]
for travel in range(0,16):
 for a in [new['STUDY_WeAct_Straight_E_Core'],new['STUDY_E_Straight_Header']]:
  am=a.m.translate([0,0,travel]);bb=np.array(am.bounding_box())
  for k,s in bench.items():
   if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
   v=max(0,(am^s.m).volume())
   if v>.02:approach.append({'travel_mm':travel,'target':k,'volume_mm3':v})
report={'status':'BLOCKED','main_updated':False,'native_PCB_changed':False,'core_rigid_lift_mm':dz,'carrier_actual_substrate_top_z_mm':carrier_top,'core_mating_substrate_face_z_mm':core_face,'nominal_board_face_gap_mm':core_face-carrier_top,'socket_rows':socketrows,'static_collisions':hits,'poses':130,'motion_collisions':motion,'core_removal_15mm':approach,'vendor_solid_fallbacks':fallbacks,'unresolved':['User choice for E straight-header route','Native E hole-pattern/NRST handoff correction','Source A-D nominal6mm pin tolerance and socket contact actual engagement/retention','No complete wire bend, hand or electrical qualification'],'sources':json.loads((HERE/'sources/socket_sources.json').read_text())}
(HERE/'socket_candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.resolution_x=1100;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for o in sc.objects:
 if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in set(new)|{'MCU_Carrier'}
camera('socket_candidate',(-115,-140,180),(-8,-44,129),75);sc.render.filepath=str(HERE/'socket_stack.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'socket_candidate.blend'));print('SOCKET_CANDIDATE_COMPLETE',len(hits),len(motion),len(approach),flush=True)
