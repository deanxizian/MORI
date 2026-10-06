"""Fresh handed-off PCBs + component-up WeAct, independent candidate only."""
import sys,json,hashlib,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr,broad
from native_electronics import board_transform
from layout_cleanup import mm_mesh
from render import camera
from monocoque_structure import source_build
load_collections();source_build().materials()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
received=HERE/'p5r7_receipt';inv=json.loads((received/'inventory.json').read_text())
handoff=json.loads((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_text())
original=dict(ss);new={};details={};fallbacks=[]
def build(n,solids,mat='pcb'):
    vv=[];ff=[];ms=[]
    for i,(v,f) in enumerate(solids):
        v=np.array(v);f=np.array(f,dtype=np.uint64);m=manifold.Manifold(manifold.Mesh64(v,f))
        if m.status()!=manifold.Error.NoError:
            lo=v.min(0)-.001;hi=v.max(0)+.001;m=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());fallbacks.append(dict(part=n,solid=i,method='Conservative closed AABB for validation; original render triangles retained'))
        ms.append(m);ff.extend((f+len(vv)).tolist());vv.extend(v.tolist())
    m=manifold.Manifold.batch_boolean(ms,manifold.OpType.Add);o=mesh('RECEIPT_'+n,vv,ff)
    finish(o,'PURCHASED_REFERENCE','P5R7 接收候选 / '+n,mat,'body',False,role='receipt_candidate')
    q=m.to_mesh64();path=received/('solid_'+n+'.json');path.write_text(json.dumps(dict(vertices_mm=q.vert_properties[:,:3].tolist(),triangles=q.tri_verts.tolist())))
    o['validation_solid_source']=str(path.relative_to(PROJECT));o['data_status']='ASSUMED';o['physical_fit']='NOT_TESTED'
    new[n]=Solid(o);ss[n]=new[n]
    if n in original:original[n].o.hide_render=True;original[n].o.hide_set(True)
    return new[n]
for kind in ['motion','rear']:
    c=json.loads((received/(kind+'_complete_mesh.json')).read_text());r,t=board_transform(kind,c)
    subsets=[(P['native_electronics']['boards'][kind]['object'],None)] if kind=='motion' else [('Rear_Interface_PCB',None),('USB_Receptacle','USB1'),('Power_Switch','SW1')]
    for n,ref in subsets:
        solids=[]
        for comp in c['components']:
            if ref is not None and comp['reference']!=ref:continue
            if ref is None and kind=='rear' and comp['reference'] in ['SW1','USB1']:continue
            for s in comp['solids']:solids.append((np.array(s['vertices_mm'])@r.T+t,s['triangles']))
        build(n,solids)
    details[kind]=dict(native_source_sha256=c['source_native_sha256'],rotation=r.tolist(),translation_mm=t.tolist(),component_count=len(c['components']))
    if kind=='motion':
        pcb=next(x for x in c['components'] if x['reference']=='PCB');pcbverts=np.vstack([s['vertices_mm'] for s in pcb['solids']])@r.T+t;carrier_top=float(pcbverts[:,2].max())
        module=next(x for x in inv['boards']['motion']['footprints'] if x['reference']=='U100')
        pads={a['number']:(r@np.array([a['xy_mm'][0],-a['xy_mm'][1],0])+t)[:2] for a in module['pads']}

c=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text());assert c['source_sha256']==handoff['weact_assembly']['core_model_sha256']
r=np.array(handoff['weact_assembly']['core_STEP_to_robot_rotation'],float)
thickness=-float(c['solids'][0]['cad_bounds_xyz_mm'][2][0]);core_bottom=carrier_top+8.5+2.54
t=np.array([*handoff['weact_assembly']['core_STEP_to_robot_translation_xy_mm'],core_bottom+thickness])
solids=[];header_moves=[]
for i,s in enumerate(c['solids']):
    if i==32:continue # Official bent E header replaced by selected straight reference.
    v=np.array(s['vertices_mm']);f=s['triangles']
    if i in [159,160,161,162]:
        center_y=(v[:,1].min()+v[:,1].max())/2
        # Actual 180deg rigid reorientation of the symmetric unkeyed header,
        # not a whole-board flip or scaling. Pins point down from underside.
        hr=np.diag([1.,-1.,-1.]);ht=np.array([0,2*center_y,-thickness]);v=v@hr.T+ht
        header_moves.append(dict(source_solid=i,rotation=hr.tolist(),translation=ht.tolist()))
    solids.append((v@r.T+t,f))
core=build('MCU_Motion',solids)
epts=np.array([v for k,v in pads.items() if k.startswith('E')]);ec=epts.mean(0)
em=manifold.Manifold.cube([5.08,10.16,2.54],True).translate([*ec,core_bottom-1.27])
for x,y in epts:em+=manifold.Manifold.cube([.64,.64,11.54],True).translate([x,y,core_bottom+(3-8.54)/2])
q=em.to_mesh64();build('E_Straight_Header',[(q.vert_properties[:,:3],q.tri_verts)],'metal')
sockets=[]
for label,letters,sku in [('AC',['A','C'],'61303021821'),('BD',['B','D'],'61303021821'),('E',['E'],'61300821821')]:
    xy=np.array([v for k,v in pads.items() if k[0] in letters]);center=xy.mean(0);size=[38.6,5.08,8.5] if label!='E' else [5.08,10.66,8.5]
    m=manifold.Manifold.cube(size,True).translate([*center,carrier_top+4.25])
    for x,y in xy:
        m-=manifold.Manifold.cube([.74,.74,6.35],True).translate([x,y,carrier_top+8.5-6.35/2+.01])
        m+=manifold.Manifold.cube([.45,.3,3.1],True).translate([x,y,carrier_top-1.55])
    q=m.to_mesh64();build('Socket_'+label,[(q.vert_properties[:,:3],q.tri_verts)],'dark')
    sockets.append(dict(id=label,mpn=sku,body_xyz_mm=size,center_mm=[*center,carrier_top+4.25],tails_mm=3.1))

# Actual source-matched, numbered coordinates are checked; hole-set matching
# cannot excuse the old upside-down electrically wrong orientation.
audit=json.loads((PROJECT/'hardware/v1_2/reviews/weact_E_J3_20260930/weact_alignment_audit.json').read_text())
pin_errors=[dict(pin=x['pin'],error_mm=float(np.linalg.norm(pads[x['pin']]-np.array(x['world_xy_mm'])))) for x in audit['rows']]
static=[]
for n,a in new.items():
    for k,b in ss.items():
        if n==k or (k in new and k<n):continue
        if broad(a,b):
            volume=max(0,(a.m^b.m).volume())
            if volume>.02:static.append(dict(candidate=n,target=k,volume_mm3=volume))
pin_hole_diagnostics=[]
for idx,(vv,ff) in enumerate(solids):
    component=manifold.Manifold(manifold.Mesh64(np.array(vv),np.array(ff,dtype=np.uint64)))
    if component.status()!=manifold.Error.NoError:continue
    overlap=component^new['E_Straight_Header'].m
    if overlap.volume()>.0001:pin_hole_diagnostics.append(dict(source_solid_index_excluding_retired_E=idx,overlap_mm3=overlap.volume(),overlap_bounds_mm=overlap.bounding_box()))
motion=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for k,s in ss.items():
            if s.group not in ['yaw','pitch']:continue
            b=Solid(s.o,s,rigidtr(yaw,pitch if s.group=='pitch' else 0))
            for n,a in new.items():
                if broad(a,b):
                    volume=max(0,(a.m^b.m).volume())
                    if volume>.02:motion.append(dict(yaw=yaw,pitch=pitch,candidate=n,target=k,volume_mm3=volume))

out=dict(revision='M1.43 + received P5R7 candidate',source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),handoff_sha256=hashlib.sha256((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_bytes()).hexdigest(),main_updated=False,boards=details,core=dict(rotation=r.tolist(),translation_mm=t.tolist(),vendor_substrate_thickness_mm=thickness,carrier_top_mm=carrier_top,core_bottom_mm=core_bottom,board_face_gap_mm=11.04,header_moves=header_moves),sockets=sockets,numbered_pin_errors=pin_errors,static_collisions=static,motion_poses=130,motion_collisions=motion,fallbacks=fallbacks,status='BLOCKED' if static or motion else 'PASS',scope='Nominal candidate. Contact spring/insertion/retention and selected A-D header variant not measured. Mated plug routes, body order and tool paths must be rechecked before replacing main.',remaining=['Core USB, BOOT/RESET and SWD access','All P5R7 mated plugs and terminal wires','Full body-shell sequence with new core height','Exact socket contact retention and A-D header supply version'])
(HERE/'p5r7_fit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
out['pin_hole_diagnostics']=pin_hole_diagnostics
(HERE/'p5r7_fit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('P5R7_FIT',out['status'],'PINS',max(x['error_mm'] for x in pin_errors),'STATIC',static,'MOTION',motion[:3],flush=True)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='OBJECT';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for x in sc.objects:
    if x.type=='MESH':x.hide_render=True
for n in ['MCU_Motion','MCU_Carrier','Socket_AC','Socket_BD','Socket_E','E_Straight_Header','Rear_Interface_PCB','Load_Frame','Yaw_Base']:
    x=ss[n].o;x.hide_render=False;x.color=(.08,.32,.24,1) if n in ['MCU_Motion','MCU_Carrier','Rear_Interface_PCB'] else (.15,.16,.18,1) if n.startswith('Socket') else (.7,.74,.75,1)
camera('receipt_p5r7',(140,-190,235),(0,-32,129),120);sc.render.filepath=str(HERE/'p5r7_fit.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'p5r7_fit.blend'))
