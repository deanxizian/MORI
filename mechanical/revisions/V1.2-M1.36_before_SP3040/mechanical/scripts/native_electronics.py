"""M1.23 actual native PCB placements and source-backed populated meshes.

Only mechanical geometry is written. Never mutate native KiCad/hardware contracts.
Source vertices retained; per-component groups keep each package selectable.
"""
from common import *
import hashlib
from mathutils import Euler
from purchased_geometry import remove_generated,finish_reference
from monocoque_structure import obj,source_build
from layout_cleanup import mm_mesh
from structural_simplification import hardware

E=P.get('native_electronics',{})
COLORS={'pcb':(.035,.25,.16),'dark':(.055,.065,.075),'ivory':(.8,.8,.72),'metal':(.52,.57,.60),'yellow':(.92,.60,.035)}

def rotation(degrees):return np.asarray(Euler(tuple(math.radians(v) for v in degrees),'XYZ').to_matrix(),dtype=float)

def source_mesh(path):
    data=json.loads((PROJECT/path).read_text())
    if data.get('source_native_file'):
        assert hashlib.sha256((PROJECT/data['source_native_file']).read_bytes()).hexdigest()==data['source_native_sha256'],data['source_native_file']
    if data.get('source_file'):
        assert hashlib.sha256((PROJECT/data['source_file']).read_bytes()).hexdigest()==data['source_sha256'],data['source_file']
    return data

def board_transform(kind,cache=None):
    s=E['boards'][kind];c=cache or source_mesh(s['mesh']);pcb=next(v for v in c['components'] if v['reference']=='PCB')
    r=rotation(s['rotation_xyz_deg']);bb=pcb['bounds_xyz_mm'];mid=np.array([(bb[0][0]+bb[0][1])/2,(bb[1][0]+bb[1][1])/2,0])
    t=np.array([*s['board_center_xy_mm'],s['substrate_reference_z_mm']])-r@mid
    return r,t

def solid_from(v,f,label,fallbacks):
    m=manifold.Manifold(manifold.Mesh64(v,np.asarray(f,dtype=np.uint64)))
    if m.status()!=manifold.Error.NoError:
        fallbacks.append({'component':label,'error':str(m.status()),'method':'Conservative per-solid AABB for checks only; original triangles retained'})
        lo=v.min(0)-.001;hi=v.max(0)+.001;m=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
    return m

def aggregate(name,cache,r,t,label,exclude=(),only=None,group='body'):
    remove_generated(name);remove_generated(name+'_Proxy')
    comps=cache.get('components',[{'reference':'VENDOR_ASSEMBLY','solids':cache.get('solids',[]),'evidence':'VENDOR_CAD'}])
    verts=[];faces=[];materials=[];components=[];solids=[];fallbacks=[]
    for c in comps:
        ref=c['reference']
        if ref in exclude or (only and ref not in only):continue
        start=len(verts);fs=len(faces);cms=[]
        for i,s in enumerate(c['solids']):
            v=np.asarray(s['vertices_mm'],dtype=float)@r.T+t;f=np.asarray(s['triangles'],dtype=np.uint64)
            cm=solid_from(v,f,f'{name}/{ref}/{i}',fallbacks);solids.append(cm);cms.append(cm)
            faces.extend((f+len(verts)).tolist());verts.extend(v.tolist());materials.extend([s.get('material','pcb')]*len(f))
        components.append({'reference':ref,'value':c.get('value',''),'evidence':c.get('evidence','VENDOR_CAD'),'vertices':[start,len(verts)],'faces':[fs,len(faces)],
            'bounds_xyz_mm':[[min(m.bounding_box()[i] for m in cms),max(m.bounding_box()[i+3] for m in cms)] for i in range(3)],
            'dimension_basis':c.get('dimension_basis',''),'limitations':c.get('limitations',cache.get('library_limit',cache.get('limit','')))})
    m=manifold.Manifold.batch_boolean(solids,manifold.OpType.Add);assert m.status()==manifold.Error.NoError,(name,m.status())
    proxy=mm_mesh(name+'_Proxy',m);finish(proxy,'KEEP_OUT',label+' / 实体检查','keepout',group,False,role='validation_proxy')
    data=m.to_mesh64();file=ROOT/'reports'/('solid_'+name+'.json');save_json(file,{'vertices_mm':data.vert_properties[:,:3].tolist(),'triangles':data.tri_verts.tolist(),'coordinate_frame':'assembly zero mm','fallbacks':fallbacks})
    o=mesh(name,verts,faces);o['preserve_vendor_tessellation']=True
    finish_reference(o,label,'NATIVE_DESIGN_WITH_SOURCE_BACKED_PACKAGES' if cache.get('source_native_file') else 'VENDOR_CAD',['NATIVE_ELECTRONICS_M1_23'],group,'pcb')
    o['data_status']='ASSUMED' if cache.get('source_native_file') else 'VENDOR_DOCUMENTED'
    o['source_scale_factor']=1.;o['source_revision']=cache.get('source_revision','Manufacturer family CAD')
    o['validation_proxy']=proxy.name;o['validation_solid_source']=str(file.relative_to(PROJECT))
    o['source_rotation']=r.tolist();o['source_translation_mm']=t.tolist();o['component_reference_index']=json.dumps(components,ensure_ascii=False)
    o['component_count']=len(components);o['source_native_sha256']=cache.get('source_native_sha256','');o['unknown_dimensions']='See per-component evidence; no physical measurements, full solder/tolerance/mating-cable qualification.'
    o.data.materials.clear()
    names=list(COLORS)
    for k,col in COLORS.items():o.data.materials.append(material('electronics_'+k,col,metallic=.65 if k=='metal' else 0,roughness=.45))
    for poly,mat in zip(o.data.polygons,materials):poly.material_index=names.index(mat)
    for c in components:o.vertex_groups.new(name=c['reference']).add(list(range(*c['vertices'])),1.,'REPLACE')
    return o,m,components,fallbacks

def mount_rear(c,r,t):
    """Mount the received holes; keep its switch-placement defect visible."""
    s=E['rear_mount'];shell=obj('Body_Upper');deck=obj('Load_Frame');b=source_build()
    inv=json.loads((PROJECT/E['inventory']).read_text())['boards']['rear']
    pcb=next(v for v in c['components'] if v['reference']=='PCB')
    bottom=float((r@np.array([0,0,pcb['bounds_xyz_mm'][2][0]])+t)[2]);top=bottom+c['nominal_board_thickness_mm']
    rows=[]
    for i,f in enumerate(sorted([f for f in inv['footprints'] if f['reference'] in ['H1','H2']],key=lambda f:f['reference'])):
        x,y,_=r@np.array([f['xy_mm'][0],-f['xy_mm'][1],0])+t
        # Plain rectangular inward shell ledges; no external ears or tool slots.
        end=y+s['support_width_mm']/2;start=-82
        ledge=box('rear_native_ledge',(x,(start+end)/2,top+s['seat_height_mm']/2),(s['support_width_mm'],end-start,s['seat_height_mm']))
        intersect(ledge,b.body_outer('native_ledge_outer_limit'));union(shell,ledge)
        boolean(shell,cyl('rear_native_pilot',(x,y,top+2.25),s['pilot_diameter_mm']/2,4.6))
        for stem in ['Rear_Interface_Insert_','Rear_Interface_Screw_']:remove_generated(stem+str(i))
        ins=ring('Rear_Interface_Insert_'+str(i),(x,y,top+.2+s['insert_length_mm']/2),s['insert_outer_diameter_mm']/2,1.05,s['insert_length_mm'])
        hardware(ins,'P5后接口板M2试配嵌件 / 原生孔位')
        screw=cyl('Rear_Interface_Screw_'+str(i),(x,y,bottom+s['screw_length_mm']/2),.95,s['screw_length_mm'])
        union(screw,cyl('rear_M2_head',(x,y,bottom-s['screw_head_height_mm']/2),s['screw_head_diameter_mm']/2,s['screw_head_height_mm']));hardware(screw,'P5后接口板M2×6 / 底面操作')
        rows.append({'ref':f['reference'],'source_xy_mm':f['xy_mm'],'world_xy_mm':[x,y],'board_bottom_z_mm':bottom,'board_top_z_mm':top})
    boolean(deck,box('native_rear_service_opening',s['frame_clearance_center_mm'],s['frame_clearance_xyz_mm'],2))
    # USB opening follows the received connector, not the retired idealized box.
    ub=np.asarray(bounds(obj('USB_Receptacle')));sz=np.asarray(bounds(obj('Power_Switch')))
    uz=float(ub[2].mean());boolean(shell,box('native_USB_shell_open',(0,-76,uz),s['usb_opening_xyz_mm'],.3))
    # Only an access/review aperture: the received short stem cannot reach it.
    swz=float(top+2.55);boolean(shell,box('native_switch_review_open',(0,-76,swz),(6,30,3.2),.3))
    remove_generated('Interface_Lead')
    record={'revision':P['revision'],'status':'NATIVE_P5_GEOMETRY_SWITCH_REACH_BLOCKED','PCB_nominal_xy_mm':[24,25],
      'PCB':bounds(obj('Rear_Interface_PCB')),'sites':rows,'shell_integral_mounts':2,'new_printed_brackets':0,'fasteners':2,
      'board_top_z_mm':top,'board_bottom_z_mm':bottom,'USB_axis_z_mm':uz,'switch_actuator_axis_z_mm':swz,
      'USB_mouth_y_mm':float(ub[1,0]),'switch_stem_tip_y_mm':float(sz[1,0]),
      'stem_behind_USB_mouth_mm':float(sz[1,0]-ub[1,0]),'USB_and_switch_toward':'-Y rear',
      'screw_access_direction':'-Z on detached upper shell','removal_direction':'-Z then +Y on detached upper shell',
      'limits':[s['switch_access_status'],'J3 mating plug approaches motion carrier; actual mating shell and harness remain to be checked.','No native electrical footprints moved. No charger/PD electronics invented.']}
    save_json(ROOT/'reports/rear_interface_geometry.json',record)
    return record

def mount_buck(name,s,r,t):
    q=E['buck_mount'];deck=obj('Load_Frame');rows=[]
    zs=[float((r@np.array([0,0,z])+t)[2]) for z in s['pcb_source_z_mm']];bottom=min(zs);top=max(zs);ceiling=P['layout']['deck_z_mm']-P['layout']['deck_thickness_mm']/2
    for i,(x0,y0) in enumerate(s['mount_holes_source_xy_mm']):
        x,y,_=r@np.array([x0,y0,0])+t;fast=i in s['fastened_hole_indices']
        union(deck,cyl('buck_integral_seat',(x,y,(top+ceiling+.15)/2),q['seat_diameter_mm']/2,ceiling+.15-top))
        if fast:
            pilot_low=top-.1;pilot_high=bottom+q['screw_length_mm']+.2
            boolean(deck,cyl('buck_blind_insert_pilot',(x,y,(pilot_low+pilot_high)/2),q['pilot_diameter_mm']/2,pilot_high-pilot_low))
            ins=ring(name+'_Insert_'+str(i),(x,y,top+.2+q['insert_length_mm']/2),q['insert_outer_diameter_mm']/2,1.05,q['insert_length_mm']);hardware(ins,name+' M2试配短嵌件')
            bolt=cyl(name+'_Screw_'+str(i),(x,y,bottom+q['screw_length_mm']/2),.95,q['screw_length_mm']);union(bolt,cyl('buck_head',(x,y,bottom-q['screw_head_height_mm']/2),q['screw_head_diameter_mm']/2,q['screw_head_height_mm']));hardware(bolt,name+' 底面M2×6')
        else:boolean(deck,cyl('buck_unused_mount_hole',(x,y,top+.6),1.1,1.3))
        rows.append({'index':i,'source_xy_mm':[x0,y0],'world_xy_mm':[x,y],'PCB_bottom_z_mm':bottom,'PCB_top_z_mm':top,'fastened':fast})
    return rows

def apply_native_electronics():
    if not E.get('enabled'):return
    result={'revision':P['revision'],'hardware_handoff':E['handoff'],'boards':{},'modules':{},'measured':False,'print_release':False,'source_config':'config/geometry.json#/native_electronics'}
    for kind,s in E['boards'].items():
        c=source_mesh(s['mesh']);r,t=board_transform(kind,c);ex=['SW1','USB1'] if kind=='rear' else []
        o,m,refs,fallbacks=aggregate(s['object'],c,r,t,c['source_revision']+' / 原生装件与板框',exclude=ex)
        o['documented_mass_g']={'motion':12,'imu':3,'power':30,'rear':3}[kind];o['mass_status']='BUDGET_ASSUMPTION_NOT_MEASURED'
        result['boards'][kind]={'object':s['object'],'source':s['mesh'],'source_native':c['source_native_file'],'source_sha256':c['source_native_sha256'],'components':refs,'fallbacks':fallbacks,'rotation':r.tolist(),'translation_mm':t.tolist(),'bounds_xyz_mm':bounds(o),'nominal_pcb_thickness_mm':c['nominal_board_thickness_mm']}
        if kind=='rear':
            for ref,name in [('SW1','Power_Switch'),('USB1','USB_Receptacle')]:
                extra,_,rows,bad=aggregate(name,c,r,t,f'{ref} 原生位置 / 厂图重建',only=[ref]);result['boards'][kind]['components']+=rows;result['boards'][kind]['fallbacks']+=bad
            result['rear_mount']=mount_rear(c,r,t)
    for name,s in E.get('modules',{}).items():
        c=source_mesh(s['mesh']);r=rotation(s['rotation_xyz_deg']);t=np.array(s['destination_center_mm'])-r@np.array(s['source_center_mm'])
        o,m,refs,falls=aggregate(name,c,r,t,s['selected_reference']+' / 原厂CAD')
        o['selection_status']='ENGINEERING_REFERENCE_NOT_PURCHASE_RELEASE';o['mount_status']=s['mount_status'];o['documented_mass_g']=7 if name=='Wheel_Buck' else 2.3
        result['modules'][name]={'source':s['mesh'],'bounds_xyz_mm':bounds(o),'rotation':r.tolist(),'translation_mm':t.tolist(),'fallbacks':falls,'mount_status':s['mount_status']}
        result['modules'][name]['mount_sites']=mount_buck(name,s,r,t)
    cam=obj('CAM_Mainboard');cam['unknown_dimensions']='Official outline37x37 and32.6mm hole grid only. Exact PCB thickness, populated depth, component/connector coordinates and camera FPC absent. Remains ASSUMED, not a precise populated CAD.'
    result['unresolved']={'CAM33700':'Original complete CAD unavailable; official outline and photo-estimated packages modeled at1:1; physical dimensions remain unqualified','charger':'Required3S charger/PD module unselected; no invented real board','WeAct_socket':'Native U100 pin grid documented; actual mating socket model/insertion depth pending','mating_cables':'Not included in bare-board solids'}
    result['unresolved']['rear_switch']='Native switch stem recessed behind USB mouth; external operability BLOCKED, electrical-owner layout feedback required.'
    # Refresh inherited labels without changing any fastener or PCB geometry.
    # The old P2/P4 names describe construction seeds, not the received boards.
    for i in range(4):
        obj('Carrier_Screw_'+str(i))['label_zh']=result['boards']['motion']['source_native'].split('/')[-1].replace('.kicad_pcb','')+' 基板M2试配螺钉'
    for ref in P['layout_cleanup']['power_bay']['local_mount']['fastened_hole_refs']:
        obj('Power_Board_'+ref+'_Screw')['label_zh']='电源板对角M2×6 / '+result['boards']['power']['source_native'].split('/')[-1].replace('.kicad_pcb','')+'原生孔位'
        for suffix in ['Screw','Insert']:
            part=obj('Power_Board_'+ref+'_'+suffix)
            part['interface_status']='Trial M2 hardware at unchanged received native holes; nominal populated geometry checked, thread/insert fit and physical strength not qualified.'
            part['functional_purpose']=part['interface_status']
    obj('Load_Frame')['power_board_mount']='Four short integral seats and two diagonal trial M2x6 screws at received native holes. Install before fixed yaw bridge/head; coupon and load qualification pending.'
    weact=json.loads((ROOT/'reports/vendor_weact_import.json').read_text())
    weact['carrier_stack']='Received native carrier integrated at1:1;6mm mating socket height remains an unselected assumption.'
    save_json(ROOT/'reports/vendor_weact_import.json',weact)
    # The earlier report describes a historical seed. Publish the actual final
    # transforms and inventory here without modifying hardware-owned contracts.
    im=result['boards']['imu'];save_json(ROOT/'reports/imu_mount_transform.json',{'native_board_revision':result['boards']['imu']['source_native'].split('/')[-1].replace('.kicad_pcb',''),'native_pcb_xy_mm':[20,16],'native_to_assembly_rotation':im['rotation'],'native_to_assembly_translation_mm':im['translation_mm'],'PCB_front_normal_body':[0,0,-1],'components_face':'down','mount':'two existing rigid Load_Frame bosses; native holes unchanged','IMU_sensor_to_PCB_axes':'Use the received native footprint rotation and datasheet. This mechanical transform is not firmware die-axis calibration.'})
    plan=json.loads((ROOT/'reports/module_assembly.json').read_text());plan['revision']=P['revision'];plan['native_electronics']=E['received_hardware_revision']+' handoff; actual per-board source revisions recorded in native_electronics_geometry.json; four nominal1.6mm boards, source-backed or generic package data';plan['buck_assembly']=E['buck_mount']['prerequisite'];plan['power_board_assembly']='Received populated native power board at1:1 on existing four seats, two diagonal M2x6; mating connectors and thermal behavior remain unqualified.';plan['limits']='Nominal source geometry, trial fastening and straight-shank access only. Complete mated connectors, thread fits, hand access, thermal performance and rear-switch operability remain unqualified.';save_json(ROOT/'reports/module_assembly.json',plan)
    from structural_simplification import volume
    changes=json.loads((ROOT/'reports/structure_changes.json').read_text())
    for n in changes['after']:
        if bpy.data.objects.get(PREFIX+n):changes['after'][n]={'volume_mm3':volume(obj(n)),'bounds_xyz_mm':bounds(obj(n))}
    save_json(ROOT/'reports/structure_changes.json',changes)
    con=json.loads((ROOT/'reports/part_consolidation.json').read_text());con['fasteners_after']=sum(any(k in o.name.removeprefix(PREFIX) for k in ['Screw','Nut','Insert','Washer']) and not o.name.startswith(PREFIX+'Coupon') for o in parts());con['native_electronics_mounting']='No extra PCB brackets; wheel9V and head6V engineering-reference modules retain four M2 screws/four trial inserts. The two5V converters are already on Power_Module and are not separate boards.';save_json(ROOT/'reports/part_consolidation.json',con)
    save_json(ROOT/'reports/native_electronics_geometry.json',result)
    print('NATIVE_ELECTRONICS_COMPLETE',flush=True)
