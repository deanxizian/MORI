import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=900;sc.render.resolution_y=750;sc.render.resolution_percentage=100
camera('speaker_front_diagnostic',(340,510,320),(0,64,135),80)
for show_gasket in [True,False]:
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in ({'Speaker','Speaker_Gasket'} if show_gasket else {'Speaker'})
 for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[n].hide_render=True
 sc.render.filepath=str(Path(__file__).parent/('diagnostic_with_gasket.png' if show_gasket else 'diagnostic_without_gasket.png'))
 bpy.ops.render.render(write_still=True)
gasket=bpy.data.objects[PREFIX+'Speaker_Gasket'];gasket.hide_render=False
me=gasket.data
for p in me.polygons:p.use_smooth=False
normals=[(0,0,0)]*len(me.loops)
for p in me.polygons:
 for k in p.loop_indices:normals[k]=p.normal[:]
me.normals_split_custom_set(normals);me.update()
sc.render.filepath=str(Path(__file__).parent/'diagnostic_flat_gasket.png');bpy.ops.render.render(write_still=True)
from speaker_geometry import front_ring,speaker_transform
from belly_relayout import relocate
gasket.hide_render=True;m=P['speaker_mount']
MATS['tire']=gasket.data.materials[0]
fresh=front_ring('diagnostic_fixed_gasket',0,m['gasket_thickness_mm'],m['gasket_outer_xz_mm'],m['gasket_inner_xz_mm'])
finish(fresh,'PURCHASED_REFERENCE','Diagnostic gasket','tire','body',False);relocate(fresh,speaker_transform());fresh.hide_render=False
sc.render.filepath=str(Path(__file__).parent/'diagnostic_fixed_gasket.png');bpy.ops.render.render(write_still=True)
records={}
tr=speaker_transform();length,height=m['gasket_inner_xz_mm']
for name,o in [('before',gasket),('fixed',fresh)]:
 o.data.calc_loop_triangles();v=np.array([tuple(v) for v in vertices_world(o)],dtype=np.float64)
 loc=(np.c_[v,np.ones(len(v))]@np.array(tr.inverted()).T)[:,:3]
 f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64);c=loc[f].mean(axis=1)
 d=np.hypot(np.maximum(abs(c[:,0])-(length-height)/2,0),c[:,2])
 records[name]={'interior_triangles':int(np.sum(d<height/2-.05)),'total_triangles':len(f)}
save_json(Path(__file__).parent/'gasket_aperture_regression.json',records)
