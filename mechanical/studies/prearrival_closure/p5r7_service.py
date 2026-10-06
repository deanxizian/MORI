"""P5R7 service envelope screening. No selected plugs/tools or CAD edits."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
exec(compile((HERE/'rigid_assembly_paths.py').read_text().split('# Parts are handled')[0],str(HERE/'rigid_assembly_paths.py'),'exec'))
from interface_completion import axial
from render import camera
fit=json.loads((HERE/'p5r7_fit.json').read_text());r=np.array(fit['core']['rotation']);t=np.array(fit['core']['translation_mm'])
c=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text())
components={}
for i,s in enumerate(c['solids']):
    if i in [32,159,160,161,162]:continue
    vv=np.array(s['vertices_mm'])@r.T+t;ff=np.array(s['triangles'],dtype=np.uint64)
    mm=manifold.Manifold(manifold.Mesh64(vv,ff))
    if mm.status()==manifold.Error.NoError:components['core_solid_'+str(i)]=mm
fixture={n:s.m for n,s in ss.items() if s.group=='body' and n not in ['MCU_Motion','Body_Upper','Body_Lower','Power_Switch','Rear_Interface_PCB','USB_Receptacle','Speaker','Speaker_Gasket'] and not n.startswith(('Speaker_','Rear_Interface_','Frame_','Shell_'))}
def hits(mm,parts):
    b=np.array(mm.bounding_box());out=[]
    for n,m in parts.items():
        bb=np.array(m.bounding_box())
        if np.any(b[3:]<bb[:3]) or np.any(bb[3:]<b[:3]):continue
        volume=max(0,(mm^m).volume())
        if volume>.02:out.append(dict(part=n,volume_mm3=volume))
    return out
rows=[]
# Three buttons all checked so uncertain CAD switch names do not omit one.
for idx in [29,30,31]:
    b=np.array(components['core_solid_'+str(idx)].bounding_box());pt=(b[:3]+b[3:])/2;pt[2]=b[5]+.05
    env=axial(1,45,pt+np.array([0,0,22.5]),[0,0,1])+axial(4,60,pt+np.array([0,0,75]),[0,0,1])
    rr=hits(env,fixture|{k:v for k,v in components.items() if k!='core_solid_'+str(idx)})
    rows.append(dict(id='core_button_'+str(idx),status='PASS' if not rr else 'BLOCKED',hits=rr,contact_mm=pt.tolist(),tool_allocation='2mm diameter45mm plastic rod +8mm diameter60mm handle; not selected product'))
# Rectangular space requirement outside official USB mouth. Plug not selected.
b=np.array(components['core_solid_163'].bounding_box());center=(b[:3]+b[3:])/2;mouth=b[3];usb=manifold.Manifold.cube([22,12,6],True).translate([mouth+11.05,center[1],center[2]])
rr=[]
for d in np.arange(0,20.01,.5):rr.extend(dict(travel_mm=float(d),**h) for h in hits(usb.translate([d,0,0]),fixture|components))
rows.append(dict(id='core_USB_service_allocation',status='PASS' if not rr else 'BLOCKED',hits=rr,opening_world_x_mm=mouth,body_xyz_mm=[22,12,6],insertion_travel_mm=20,samples=41,limit='Conservative trial outer space only; not a sourced plug, no internal metal insertion or wire bend check.'))
# E pads retain top pin stubs; a narrow temporary spring probe is possible.
inv=json.loads((HERE/'p5r7_receipt/inventory.json').read_text());from native_electronics import board_transform
mc=json.loads((HERE/'p5r7_receipt/motion_complete_mesh.json').read_text());mr,mt=board_transform('motion',mc)
pads=next(x for x in inv['boards']['motion']['footprints'] if x['reference']=='U100')['pads']
for pad in pads:
    if pad['number'] not in ['E2','E4','E6','E7','E8']:continue
    xy=mr@np.array([*pad['xy_mm'][:1],-pad['xy_mm'][1],0])+mt
    pt=np.array([xy[0],xy[1],fit['core']['core_bottom_mm']+3+.05]);env=axial(.5,8,pt+[0,0,4],[0,0,1])+axial(.9,30,pt+[0,0,23],[0,0,1])+axial(3,50,pt+[0,0,63],[0,0,1])
    rr=hits(env,fixture|components)
    rows.append(dict(id='SWD_probe_'+pad['number'],status='PASS' if not rr else 'BLOCKED',hits=rr,contact_mm=pt.tolist(),tool_allocation='tip1x8, shaft1.8x30, grip6x50mm; temporary tool only, not a retained connector or confirmed contact force'))
# Core withdrawal before reinstalling bridge. Full bridge removal is explicit.
check('core_and_E_withdraw_before_bridge',{'MCU_Motion','E_Straight_Header'},core-{'MCU_Motion','E_Straight_Header','Socket_AC','Socket_BD','Socket_E'},[0,0,1],30,.5)
# Vendor PCB hole geometry at E: report equivalent area and pin overlap without editing.
pcb=components['core_solid_0'];z=(pcb.bounding_box()[2]+pcb.bounding_box()[5])/2
loops=pcb.slice(z).to_polygons();hole_rows=[]
for pad in pads:
    if not pad['number'].startswith('E'):continue
    pt=mr@np.array([pad['xy_mm'][0],-pad['xy_mm'][1],0])+mt
    candidates=[]
    for lp in loops:
        q=np.array(lp);mn=q.min(0);mx=q.max(0)
        if all(pt[:2]>=mn) and all(pt[:2]<=mx) and max(mx-mn)<2:
            candidates.append(q)
    if not candidates:continue
    q=min(candidates,key=len);area=abs(float(np.dot(q[:,0],np.roll(q[:,1],1))-np.dot(q[:,1],np.roll(q[:,0],1))))/2
    hole_rows.append(dict(pin=pad['number'],bbox_xy_mm=(q.max(0)-q.min(0)).tolist(),equivalent_circle_diameter_mm=2*math.sqrt(area/math.pi),loop_vertices=len(q),limitation='Tessellated STEP cross-section, not manufacturer finished-hole tolerance.'))
out=dict(candidate_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),source_main_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),service_envelopes=rows,core_withdrawal=results,E_vendor_holes=hole_rows,status='PASS' if all(x['status']=='PASS' for x in rows+results) else 'BLOCKED',prerequisites='Remove rotating head and upper shell before service; remove fixed bridge before extracting core. Needle/probe and USB envelopes are design requirements, not selected procurement items.',limits=['No installed SWD female connector qualification; temporary spring contact requires fixture and electrical approval.','Do not change native footprints or shrink documented square0.64mm pins to hide STEP-hole disagreement.'])
(HERE/'p5r7_receipt/service.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('P5R7_SERVICE',out['status'],[(x['id'],x['status']) for x in rows],hole_rows,flush=True)
# Three current-source views make the independent bridge/shell sequence reviewable.
upper=set(json.loads((PROJECT/'mechanical/reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']['moving'])
bridge={'Yaw_Base','Yaw_Bearing','Yaw_Base_-1_Nut','Yaw_Base_1_Nut'}
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True
sc.render.resolution_x=1100;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
origin=Vector((0,0,D['body_z']));base={n:s.o.matrix_world.copy() for n,s in ss.items()}
for index,(a,z,bz) in enumerate([(15,14,18),(15,14,0),(0,0,0)],1):
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=True
    trU=Matrix.Translation((0,0,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
    trB=Matrix.Translation((0,0,bz))
    for n in core|drive|upper|bridge:
        if n not in ss:continue
        o=ss[n].o;o.matrix_world=base[n].copy();o.hide_render=False
        tr=trU if n in upper else trB if n in bridge else Matrix.Identity(4)
        # Project mesh coordinates and validation transforms are both in mm.
        o.matrix_world=tr@base[n]
    bpy.context.view_layer.update();camera('body_order_'+str(index),(250,-300,240),(0,-5,113),220)
    sc.render.filepath=str(HERE/('body_sequence_'+str(index)+'.png'));bpy.ops.render.render(write_still=True)
