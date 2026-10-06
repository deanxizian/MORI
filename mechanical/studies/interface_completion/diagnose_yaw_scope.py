"""Inspect candidate-only differences without repeating motion sampling."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from interface_completion import axial
def read(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
 return Solid(bpy.data.objects[PREFIX+'Pitch_Yoke'])
before=read(ROOT/'mori_v1_2.blend');after=read(HERE/'yaw_nut_open_candidate.blend')
seat=202.0500030517578;center=np.array([0,-8.550000190734863,198.65]);lo=np.array([-2.4,center[1],seat-4.501]);hi=np.array([2.4,-6.14,seat-2.6]);cut=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
pc=np.array([center[0],center[1],seat-3.6]);padlo=np.array([-5.5,-17.5,seat-4.5]);padhi=np.array([5.5,-6.15,seat]);restore=axial(2.56,2.02,pc,[0,0,1],segments=6)^manifold.Manifold.cube((padhi-padlo).tolist()).translate(padlo.tolist());through=axial(1.1,12,[center[0],center[1],seat-3],[0,0,1],segments=64)
scope_lo=np.array([-2.562,center[1]-2.562,seat-4.503]);scope_hi=np.array([2.562,-6.138,seat-2.578]);scope=manifold.Manifold.cube((scope_hi-scope_lo).tolist()).translate(scope_lo.tolist())+axial(1.102,12.004,[center[0],center[1],seat-3],[0,0,1],segments=64)
residual=((before.m-after.m)+(after.m-before.m))-scope
rows=[]
for p in residual.to_mesh64().vert_properties[:,:3]:
 b=before.bvh().find_nearest(Vector(p));a=after.bvh().find_nearest(Vector(p))
 rows.append({'p':p.tolist(),'before_distance':b[3],'after_distance':a[3],'before_nearest':list(b[0]),'after_nearest':list(a[0])})
rows.sort(key=lambda r:max(r['before_distance'],r['after_distance']),reverse=True)
out={'residual_volume':residual.volume(),'components':[{'volume':c.volume(),'bbox':list(c.bounding_box())} for c in residual.decompose()],'largest_distance_points':rows[:30]}
(HERE/'yaw_scope_diagnostic.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
