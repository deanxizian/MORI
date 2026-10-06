"""Independent editable vendor-part review scene, with rigid presentation offsets."""
from common import *
from optics_mount import camera_pupil
from render import camera

def add_waveshare_bench():
    if not P.get('waveshare_detail',{}).get('enabled'):return
    source=bpy.context.scene;bench=bpy.data.scenes.new('MORI_Waveshare_Bench');bench.unit_settings.system='METRIC';bench.unit_settings.scale_length=.001;bench.unit_settings.length_unit='MILLIMETERS';bench.world=source.world
    names=['Display_PCB','CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R','Camera_PCB','Camera_Lens'];mapping=[]
    for name in names:
        src=bpy.data.objects[PREFIX+name];coll=bpy.data.collections.new('WAVESHARE / '+name);bench.collection.children.link(coll)
        if name=='Display_PCB':center=Vector((0,45,230));target=Vector((-66,0,0));rot=Matrix.Rotation(math.pi,4,'Z')
        elif name.startswith('Camera_'):center=camera_pupil();target=Vector((51,0,0));rot=Matrix.Identity(4)
        else:center=Vector(P['layout']['cam_board_center_from_head_mm'])+Vector((0,0,D['head_z']));target=Vector((0,0,0));rot=Matrix.Rotation(math.pi,4,'Z')
        shift=Matrix.Translation(target)@rot@Matrix.Translation(-center)
        refs=json.loads(src['component_reference_index']);verts=np.array([tuple(v.co) for v in src.data.vertices]);faces=[list(p.vertices) for p in src.data.polygons]
        for row in refs:
            lo,hi=row['vertices'];a,b=row['faces'];me=bpy.data.meshes.new('WS '+row['reference']);me.from_pydata(verts[lo:hi].tolist(),[],[[i-lo for i in f] for f in faces[a:b]]);me.update();o=bpy.data.objects.new('WS '+name+' / '+row['reference'],me);coll.objects.link(o);o.matrix_world=shift@src.matrix_world
            for m in src.data.materials:me.materials.append(m)
            for x,y in zip(me.polygons,list(src.data.polygons)[a:b]):x.material_index=y.material_index
            o['reference']=row['reference'];o['value']=row['value'];o['evidence']=row['evidence'];o['dimension_basis']=row['dimension_basis'];o['limitations']=row['limitations'];o['source_board']=name;o['presentation_transform_only']=True;o['measured_unit']=False;mapping.append({'object':o.name,'source':src.name,'ref':row['reference'],'presentation_matrix':[list(r) for r in shift]})
    # Camera stock flex is a separate flat inspection reference, not an installed route.
    q=P['waveshare_detail']['camera'];coll=bpy.data.collections.new('WAVESHARE / OV3660 flat FPC (UNINSTALLED)');bench.collection.children.link(coll)
    from waveshare_detail import block,source_solid
    width=q['flat_fpc_width_mm'];length=q['flat_fpc_visible_length_mm'];th=q['flat_fpc_thickness_mm'];start=-q['carrier_xy_mm'][1]/2
    m=block((width,th,length),(51,-3.9,start-length/2))+block((12.5,th,2.2),(51,-3.9,start-length-1.1))
    s=source_solid(m,'flex');me=bpy.data.meshes.new('OV3660 flat FPC reference');me.from_pydata(s['vertices_mm'],[],s['triangles']);me.update();o=bpy.data.objects.new('WS OV3660 / Flat_FPC_UNINSTALLED_PHOTO_ESTIMATE',me);coll.objects.link(o);me.materials.append(material('ws_flat_flex',(.64,.27,.055)));o['evidence']='PHOTO_ESTIMATED';o['role']='uninstalled_reference';o['limits']='Only visible photo neck length estimated, folded/hidden tip length unknown. Not routed in assembly; no connector reach claim.'
    for ob in source.objects:
        if ob.type=='LIGHT':bench.collection.objects.link(ob)
    bpy.context.window.scene=bench
    camdata=bpy.data.cameras.new('Waveshare bench camera');cam=bpy.data.objects.new('Waveshare bench camera',camdata);bench.collection.objects.link(cam);cam.location=(55,210,130);cam.rotation_euler=(Vector((-17,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=160;camdata.clip_start=.1;bench.camera=cam
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.overlay.show_relationship_lines=False;sp.overlay.show_extras=False;sp.shading.color_type='MATERIAL';sp.region_3d.view_distance=165;sp.region_3d.view_location=(-17,0,0);sp.region_3d.view_rotation=Vector((55,210,130)).to_track_quat('Z','Y');sp.region_3d.view_perspective='ORTHO'
    bench['source_revision']=P['revision'];bench['coordinate_policy']='Rigid display offsets only; source assembly coordinates remain in MORI_PCB_Component_Detail';bench['accuracy']='LCD=original vendor CAD; CAM/camera=official dimensions+photo assumptions, not measured.'
    save_json(ROOT/'reports/waveshare_bench_manifest.json',{'revision':P['revision'],'parts':mapping,'uninstalled_flex':True})
