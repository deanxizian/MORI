"""Render actual candidate geometry, including the bottom locating interfaces."""
from pathlib import Path
import sys,json,math
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,manifold
from render import camera
from body_shell_split import boxm
ctx=Context();sc=bpy.context.scene
for o in sc.objects:o.hide_render=True
sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=1200;sc.render.resolution_y=850;sc.render.resolution_percentage=100
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_object_outline=True
sh.background_type='WORLD';sc.world.color=(.9,.92,.93);sc.view_settings.view_transform='Standard';sc.render.film_transparent=False
forms={}
for n in ['Body_Front','Body_Rear']:
 a=np.load(OUT/(n+'_candidate.npz'));forms[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
def show(n,m,color):
 a=m.to_mesh64();mesh=bpy.data.meshes.new('SPLIT_LOCATOR_'+n);mesh.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());mesh.update()
 o=bpy.data.objects.new('SPLIT_LOCATOR_'+n,mesh);sc.collection.objects.link(o);o.color=color;return o
images=[]
for name in ['bottom_locators_open','bottom_locators_closed_section','body_closed']:
 shown=[]
 for n,m in forms.items():
  if name.startswith('bottom'):
   m=m^boxm([-44,-22,0],[44,22,35])
   if name.endswith('open'):m=m.translate([0,10 if n=='Body_Front' else -10,0])
   if 'section' in name:m=m^boxm([-20,-30,0],[44,30,35])
  shown.append(show(n,m,(.55,.78,.85,1) if n=='Body_Front' else (.90,.82,.65,1)))
 if name=='body_closed':camera('BODY_SPLIT_'+name,[240,300,190],[0,0,103],230)
 else:camera('BODY_SPLIT_'+name,[95,105,105],[0,0,27],110 if name.endswith('open') else 95)
 p=OUT/(name+'.png');sc.render.filepath=str(p);bpy.ops.render.render(write_still=True);images.append(dict(file=p.name,sha256=sha(p)))
 for o in shown:bpy.data.objects.remove(o,do_unlink=True)
ctx.assert_unchanged()
(OUT/'candidate_render.json').write_text(json.dumps(dict(images=images,source=ctx.sources,main_changed=False,presentation='Bottom images cut at Z35 and show declared section/explosion only; geometry from saved candidate arrays'),indent=2)+'\n')
