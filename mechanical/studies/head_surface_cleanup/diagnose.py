"""Read the saved model and compare its display normals with the face planes."""
import sys,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera

sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
out=Path(__file__).parent
rows=[]
for name in ['Pitch_Cradle','Pitch_Yoke','Display_Frame']:
    o=bpy.data.objects[PREFIX+name];me=o.data;me.update()
    corners=me.corner_normals
    deviations=[]
    for p in me.polygons:
        if max(abs(v) for v in p.normal)>.99999 and p.area>.5:
            d=max(math.degrees(p.normal.angle(corners[k].vector,0)) for k in p.loop_indices)
            if d>.1:deviations.append({'polygon':p.index,'area_mm2':p.area,'normal':list(p.normal),'center_local_mm':list(p.center),'max_corner_normal_deviation_deg':d})
    rows.append({'id':name,'vertices':len(me.vertices),'faces':len(me.polygons),'smooth_faces':sum(p.use_smooth for p in me.polygons),'sharp_edges':sum(e.use_edge_sharp for e in me.edges),'has_custom_normals':me.has_custom_normals,'planar_faces_with_interpolated_normals':deviations})
save_json(out/'diagnosis.json',{'source_blend':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'parts':rows})
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True
sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
mat=material('surface_diagnosis',(.24,.32,.35),roughness=.55)
for name in ['Pitch_Cradle','Pitch_Yoke','Display_Frame']:
    o=bpy.data.objects[PREFIX+name];o.data.materials.clear();o.data.materials.append(mat)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
views={'cradle':('Pitch_Cradle',(240,240,320),(43,2,231),68),
       'yoke':('Pitch_Yoke',(220,340,285),(0,-7,194),130),
       'front_seat':('Pitch_Yoke',(150,330,238),(0,20,194),62)}
for key,(name,loc,aim,scale) in views.items():
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name!=PREFIX+name
    o=bpy.data.objects[PREFIX+name];camera('surface_'+key,loc,aim,scale)
    flags=[p.use_smooth for p in o.data.polygons]
    for mode in ['before','flat_trial']:
        if mode=='flat_trial':
            for p in o.data.polygons:p.use_smooth=False
            o.data.update()
        sc.render.filepath=str(out/(mode+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
    for p,flag in zip(o.data.polygons,flags):p.use_smooth=flag
    o.data.update()
print('SURFACE_DIAGNOSIS_COMPLETE')
