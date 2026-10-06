import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from interface_completion import repair_quantized_triangles
from export import topology
load_collections();assembled();s=Solid(bpy.data.objects[PREFIX+'Body_Lower']);q=P['assembly_issue_fixes']['body_seam'];raw=s.m
for x,y in q['xy_mm']:
 lead=q['lower_recess_mouth_lead_mm'];top=q['lower_recess_center_z_mm']+q['lower_recess_length_mm']/2;r=q['lower_recess_radius_mm'];raw-=manifold.Manifold.cylinder(lead+.01,r+lead+.01,r-.001,96).translate([x,y,top-lead])
for tol in [.00001,.00005,.0001,.0005]:
 m=raw.set_tolerance(tol).simplify(tol);d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64);v,f,ops,bad=repair_quantized_triangles(v,f);print('MOUTH_CLEAN',tol,'bad',len(bad),'operations',len(ops),'topology',topology(v,f),flush=True)
 if not bad:
  (ROOT/'studies/interface_completion/mouth_finish_candidate_geometry.json').write_text(json.dumps(dict(vertices_mm=v.tolist(),triangles=f.tolist(),tol=tol)));break
