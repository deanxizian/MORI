"""Vendor drawing + photo reconstruction; no physical measurement or print edits.

CAM datum: U right on SD face, V up, W outward. Official hole grid registers
photographs. Sources and per-feature uncertainty are in geometry.json.
"""
from common import *
from purchased_geometry import remove_generated
from native_electronics import aggregate,COLORS
from optics_mount import camera_transform
import hashlib
W=P.get('waveshare_detail',{})
COLORS.update(gold=(.72,.49,.13),blackpcb=(.028,.034,.033),glass=(.07,.09,.11),flex=(.64,.27,.055))

def block(size,center):return manifold.Manifold.cube(list(size),True).translate(list(center))
def cylinder(r,h,center):return manifold.Manifold.cylinder(h,r,r,48,True).translate(list(center))
def rounded_plate(w,h,t,r):
    m=block((w-2*r,h,t),(0,0,0))+block((w,h-2*r,t),(0,0,0))
    for x in [-w/2+r,w/2-r]:
        for y in [-h/2+r,h/2-r]:m+=cylinder(r,t,(x,y,0))
    return m

def source_solid(m,mat):
    assert m.status()==manifold.Error.NoError
    d=m.to_mesh64();return {'vertices_mm':d.vert_properties[:,:3].tolist(),'triangles':d.tri_verts.tolist(),'material':mat}

def item(ref,value,shapes,basis='PHOTO_ESTIMATED',detail='Official photograph registered to32.6mm hole grid. XY +/-0.4mm, height typically +/-0.5mm; not physical measurements.'):
    return {'reference':ref,'value':value,'evidence':basis,'dimension_basis':detail,'limitations':'No solder/tolerance/mating cable or purchased-revision qualification.','solids':[source_solid(m,c) for m,c in shapes]}

def component(row):
    u,v=row['center_uv_mm'];w=row['width_mm'];h=row['height_v_mm'];d=row['projection_mm'];sgn=1 if row['side']=='SD' else -1;t=W['cam']['pcb_thickness_mm']/2
    kind=row['kind'];shapes=[]
    def add(m,mat):
        # Build all packages on a +W board face, mirror thickness for IC side.
        if sgn<0:m=m.mirror([0,0,1])
        shapes.append((m.translate([u,v,0]),mat))
    def box(sz,c,mat):add(block(sz,c),mat)
    if kind=='sd':
        box((w,h,.3),(0,0,t+.15),'dark')
        box((w,h,.18),(0,0,t+d-.09),'metal')
        for x in [-w/2+.13,w/2-.13]:box((.26,h,d),(x,0,t+d/2),'metal')
        box((w,.35,d),(0,h/2-.18,t+d/2),'metal')
        for i in range(8):box((.45,1.0,.2),((i-3.5)*1.1,-h/2-.35,t+.12),'gold')
    elif kind=='fpc':
        # A visible slot, latch and individual contact fingers, not a solid box.
        box((w,h,.55),(0,0,t+.275),'dark')
        box((w,h*.52,d-.55),(0,h*.2,t+.55+(d-.55)/2),'ivory')
        box((w-.8,.6,.55),(0,-h*.36,t+d-.275),'dark')
        for x in [-w/2+.3,w/2-.3]:box((.6,h,d),(x,0,t+d/2),'ivory')
        pins=row['pins'];pitch=row['pitch_mm'];turn=row.get('turn_deg',0)
        # DISPLAY is rotated90deg in the board photograph.
        if turn:
            shapes=[];ww,hh=h,w
            for m,mat in [(block((ww,hh,.55),(0,0,t+.275)),'dark'),(block((ww,hh*.52,d-.55),(0,hh*.2,t+.55+(d-.55)/2)),'ivory'),(block((ww-.8,.6,.55),(0,-hh*.36,t+d-.275)),'dark')]:add(m.rotate([0,0,90]),mat)
            for x in [-ww/2+.3,ww/2-.3]:add(block((.6,hh,d),(x,0,t+d/2)).rotate([0,0,90]),'ivory')
            for i in range(pins):add(block((.2,1.3,.18),((i-(pins-1)/2)*pitch,-hh*.25,t+.65)).rotate([0,0,90]),'gold')
        else:
            for i in range(pins):box((.2,1.3,.18),((i-(pins-1)/2)*pitch,-h*.25,t+.65),'gold')
    elif kind=='socket':
        shell=block((w,h,d),(0,0,t+d/2))
        if row['mouth']=='normal':shell-=block((max(w-1.0,1),h-1.2,d),(0,0,t+d/2+.65))
        else:shell-=block((w-1.0,h,d-1.0),(0,-.7,t+d/2))
        add(shell,'ivory')
        for i in range(row['pins']):
            if row['mouth']=='normal':box((.28,.28,d-.7),(0,(i-(row['pins']-1)/2)*row['pitch_mm'],t+(d-.7)/2),'gold')
            else:box((.28,h-.5,.28),((i-(row['pins']-1)/2)*row['pitch_mm'],0,t+d/2),'gold')
    elif kind=='usb':
        shell=rounded_plate(w,d,h,.65).rotate([90,0,0]).translate([0,0,t+d/2])
        inside=rounded_plate(w-.5,d-.5,h+1,.45).rotate([90,0,0]).translate([0,0,t+d/2])
        add(shell-inside,'metal');box((w-2,h-.5,.65),(0,.2,t+d/2),'dark')
        for i in range(12):box((.22,h-1,.08),((i-5.5)*.5,0,t+d/2+.37),'gold')
    elif kind=='button':
        box((w,h,.5),(0,0,t+.25),'ivory');box((w-.3,h-.3,.15),(0,0,t+.58),'metal')
        add(cylinder(min(w,h)*.37,d-.65,(0,0,t+.65+(d-.65)/2)),'gold')
    elif kind=='ipex':
        box((w,h,.3),(0,0,t+.15),'ivory');outer=cylinder(1.0,d-.3,(0,0,t+.3+(d-.3)/2))-cylinder(.72,d,(0,0,t+.3+d/2));add(outer,'gold');add(cylinder(.22,.75,(0,0,t+.65)),'gold')
    elif kind in ['sot','soic']:
        box((w,h*.7,d),(0,0,t+d/2),'dark')
        pins=3 if kind=='sot' else 4
        for y in [-h*.44,h*.44]:
            for i in range(pins):box((.35,h*.23,.22),((i-(pins-1)/2)*w*.23,y,t+.15),'metal')
    elif kind in ['passive','led']:
        box((w*.7,h,d),(0,0,t+d/2),row.get('material','ivory'))
        for x in [-w*.425,w*.425]:box((w*.15,h,d),(x,0,t+d/2),'metal')
    else:
        box((w,h,d),(0,0,t+d/2),row.get('material','dark'))
    return item(row['reference'],row.get('value',kind),shapes,detail=json.dumps({k:row[k] for k in ['photo_center_px','side','xy_uncertainty_mm','height_uncertainty_mm','documented_fields'] if k in row},ensure_ascii=False))

def modeled(name,comps,r,t,label):
    cache={'components':comps,'source_revision':'Waveshare official photos; mechanical M1.33 reconstruction'}
    o,m,rows,bad=aggregate(name,cache,r,t,label,group='pitch')
    o['data_status']='ASSUMED';o['model_fidelity']='VENDOR_DIMENSIONS_PLUS_OFFICIAL_PHOTOS';o['dimension_source_ids']=['WAVESHARE_PHOTOS_M1_33'];o['source_geometry_type']='RECONSTRUCTION_NOT_OFFICIAL_CAD';o['unknown_dimensions']='Per-feature photo estimates and tolerances in geometry.json#/waveshare_detail; not MEASURED';o['note']='User authorized official dimensions plus photos. Geometry is a reconstruction; hardware arrival and revision confirmation required.';o['documented_fields']='See per-component evidence; only specifically dimensioned drawing fields are VENDOR_DOCUMENTED';o['mounting_release']=False
    return {'object':name,'bounds_xyz_mm':bounds(o),'components':rows,'collision_fallbacks':bad,'estimated':True}

def lcd_detail():
    o=bpy.data.objects[PREFIX+'Display_PCB'];cache=json.loads((PROJECT/P['display']['vendor_mesh_source']).read_text());vs=fs=0;rows=[]
    o.data.materials.clear();keys=['dark','pcb','metal','ivory','gold']
    for k in keys:o.data.materials.append(material('waveshare_lcd_'+k,COLORS[k],metallic=.65 if k in ['gold','metal'] else 0,roughness=.45))
    for s in cache['solids']:
        i=s['index'];nv=len(s['vertices_mm']);nf=len(s['triangles']);bb=np.asarray(s['cad_bounds_xyz_mm']);size=bb[:,1]-bb[:,0]
        mat='metal' if min(size)<.32 else 'dark'
        if i==0:mat='dark'
        elif i==1:mat='pcb'
        elif i in [2,3]:mat='flex' if False else 'gold'
        elif i in [107,108,109]:mat='ivory'
        elif i>=109:mat='gold'
        name={0:'LCD_and_cover',1:'PCB',2:'FPC_L',3:'FPC_R',107:'Connector_107',108:'Connector_108'}.get(i,'CAD_solid_'+str(i))
        for poly in list(o.data.polygons)[fs:fs+nf]:poly.material_index=keys.index(mat)
        rows.append({'reference':name,'value':'Waveshare original CAD solid '+str(i),'evidence':'VENDOR_CAD','vertices':[vs,vs+nv],'faces':[fs,fs+nf],'dimension_basis':'Original manufacturer STEP, mm, source solid index '+str(i),'limitations':o['validation_proxy_limit'] if i in [107,108] else 'Vendor nominal CAD; purchased revision/tolerance pending'})
        o.vertex_groups.new(name=name).add(list(range(vs,vs+nv)),1.0,'REPLACE');vs+=nv;fs+=nf
    assert vs==len(o.data.vertices) and fs==len(o.data.polygons),(vs,fs,len(o.data.vertices),len(o.data.polygons))
    o['component_reference_index']=json.dumps(rows,ensure_ascii=False);o['component_count']=len(rows)
    return {'source_solids':len(rows),'vertices_preserved':vs,'faces_preserved':fs,'geometry_change':'NONE','source_sha256':cache['source_sha256'],'exact_connector_solids':'NOT_TESTED107/108'}

def apply_waveshare_detail():
    if not W.get('enabled'):return
    source=json.loads((PROJECT/W['source_manifest']).read_text())
    for row in source['sources']:assert hashlib.sha256((PROJECT/row['file']).read_bytes()).hexdigest()==row['sha256']
    c=W['cam'];r=np.array([[1.,0,0],[0,0,-1.],[0,1.,0]])
    t=np.array(P['layout']['cam_board_center_from_head_mm']);t[2]+=D['head_z']
    pcb=rounded_plate(*c['pcb_outline_xy_mm'],c['pcb_thickness_mm'],c['corner_radius_mm']);padshapes=[]
    for x in [-c['hole_grid_mm']/2,c['hole_grid_mm']/2]:
        for y in [-c['hole_grid_mm']/2,c['hole_grid_mm']/2]:
            hole=cylinder(c['hole_diameter_mm']/2,c['pcb_thickness_mm']+2,(x,y,0));pcb-=hole
            for z in [-c['pcb_thickness_mm']/2-.02,c['pcb_thickness_mm']/2+.02]:padshapes.append((cylinder(1.9,.035,(x,y,z))-cylinder(c['hole_diameter_mm']/2,.1,(x,y,z)),'gold'))
    comps=[item('PCB','37x37 R2.25; thickness/holes estimated',[(pcb,'blackpcb')],detail='Outline37x37,R2.25,32.6mm grid VENDOR_DOCUMENTED. Hole diameter2.7+/-0.3 and thickness1.6+/-0.4 ASSUMED'),item('Mount_hole_annuli','Photo annuli; no screws added',padshapes)]
    comps += [component(row) for row in c['parts']]
    result={'revision':P['revision'],'sources':source,'CAM':modeled('CAM_Mainboard',comps,r,t,'微雪33700 / 官方尺寸＋照片重建 / 待实物复核')}
    mic=c['microphone'];mt=c['pcb_thickness_mm']/2
    for sign,side in [(-1,'L'),(1,'R')]:
        u=sign*mic['center_abs_u_mm'];v=mic['center_v_mm'];d=mic['depth_mm'];sz=[mic['width_mm'],mic['height_mm'],d]
        body=block(sz,(u,v,mt+d/2));port=cylinder(mic['port_diameter_mm']/2,.5,(u,v+mic['port_v_offset_mm'],mt+d-.1));body-=port
        modeled('Onboard_MIC_'+side,[item('MEMS_'+side,'Onboard MEMS; package/model unknown',[(body,'metal')])],r,t,'板载MEMS '+side+' / 照片外形与声孔')
    # Independent camera assembly at the retained optical-axis/pupil datum.
    q=W['camera'];rot=np.array(camera_transform().to_3x3())@r
    pupil=np.array(P['camera']['pupil_from_head_mm'])+np.array([0,0,D['head_z']])
    # Camera local W points optically forward (+Y), local V points down to keep a proper rotation.
    rc=np.array(camera_transform().to_3x3())@np.array([[1.,0,0],[0,0,1.],[0,-1.,0]])
    carrier=block([*q['carrier_xy_mm'],q['carrier_thickness_mm']],(0,0,q['carrier_back_from_pupil_mm']+q['carrier_thickness_mm']/2))
    result['camera_carrier']=modeled('Camera_PCB',[item('OV3660_carrier','Sensor carrier / FPC stiffener',[(carrier,'flex')],detail='Official OV3660 photo. XY+/-0.6mm, depth+/-1mm; no measured sample.')],rc,pupil,'OV3660 感光模组基座 / 照片重建')
    back=q['carrier_back_from_pupil_mm']+q['carrier_thickness_mm'];base=block([*q['lens_base_xy_mm'],q['lens_base_depth_mm']],(0,0,back+q['lens_base_depth_mm']/2))
    barrel=cylinder(q['barrel_diameter_mm']/2,q['barrel_depth_mm'],(0,0,-q['barrel_depth_mm']/2))
    glass=cylinder(q['glass_diameter_mm']/2,.08,(0,0,-.08))
    result['camera_lens']=modeled('Camera_Lens',[item('Lens_base','OV3660 square lens base',[(base,'dark'),(barrel-cylinder(q['glass_diameter_mm']/2,1.0,(0,0,-.25)),'dark'),(glass,'glass')],detail='Compact square module from exact OV3660 variant photo; all housing depths estimated +/-1mm, focal length3.2mm is NOT used as mechanical length.')],rc,pupil,'OV3660 方形镜头座 / 原光轴位置')
    result['LCD']=lcd_detail();result['wiring']='DEFERRED_BY_USER; camera FPC flat reference in detail scene only, no installed route or new holes';result['printed_structure_change']='NONE';result['mounting_release']=False
    # Retire the older invented USB solid as a hidden reserve only; the physical socket is now inside CAM aggregate.
    old=bpy.data.objects.get(PREFIX+'CAM_USB_Connector')
    if old:old['label_zh']='CAM USB旧插接包络 / 非实体连接器';old['role']='keepout';move_collection(old,'KEEP_OUT');old.hide_render=True
    result['CAM']['flat_board_populated_depth_mm']=sum([c['pcb_thickness_mm'],max(p['projection_mm'] for p in c['parts'] if p['side']=='SD'),max(p['projection_mm'] for p in c['parts'] if p['side']=='IC')])
    native_path=ROOT/'reports/native_electronics_geometry.json';native=json.loads(native_path.read_text());native['unresolved']['CAM33700']='Official outline plus photo-reconstructed double-sided population now modeled; physical heights, connector revisions, flex reach and mount retention remain unqualified.';save_json(native_path,native)
    save_json(ROOT/'reports/waveshare_geometry.json',result)
    print('WAVESHARE_DETAIL_COMPLETE',len(comps),'CAM component groups / 111 original LCD solids',flush=True)
