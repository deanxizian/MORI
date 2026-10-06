"""Prove bounded connector separation without modifying faulty vendor meshes."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
c=json.loads((ROOT/P['display']['vendor_mesh_source']).read_text());display=bpy.data.objects[PREFIX+'Display_PCB']
# Current display retains original concatenated vertex order; recover and verify a
# rigid 1:1 registration from the first source solid, including current optics tilt.
vv=np.array(c['solids'][0]['vertices_mm']);sel=np.linspace(0,len(vv)-1,120,dtype=int)
a=vv[sel];b=np.array([display.matrix_world@display.data.vertices[int(i)].co for i in sel]);ac=a.mean(0);bc=b.mean(0)
u,s,vt=np.linalg.svd((a-ac).T@(b-bc));rot=vt.T@u.T
if np.linalg.det(rot)<0:raise RuntimeError('Unexpected reflection')
off=bc-rot@ac;err=float(np.max(abs(a@rot.T+off-b)));assert err<.001,err
ids={r['id'] for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text()) if r['group'] not in ('coupon','dock') and r['id']!='Display_PCB'}
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids if bpy.data.objects.get(PREFIX+n)}
rows=[]
for i in [107,108]:
 item=c['solids'][i];bb=np.array(item['cad_bounds_xyz_mm']);lo=bb[:,0]-.001;hi=bb[:,1]+.001
 m=manifold.Manifold.cube((hi-lo).tolist(),True).translate(((hi+lo)/2).tolist()).transform(np.c_[rot,off])
 raw=np.array(item['vertices_mm']);inside=bool(np.all(raw>=lo-.001) and np.all(raw<=hi+.001));collisions=[];nearest={'gap_mm_capped_at_5':5.}
 for y in range(-60,61,10):
  for p in range(-20,26,5):
   t=np.array(rigidtr(y,p));mm=m.transform(t[:3,:]);bbox=np.array(mm.bounding_box())
   for name,base in ss.items():
    tt=np.array(rigidtr(y,p if base.group=='pitch' else 0)) if base.group in ['yaw','pitch'] else np.eye(4)
    other=base.m.transform(tt[:3,:]);otherbox=np.array(other.bounding_box())
    if np.any(bbox[3:]+5<otherbox[:3]) or np.any(otherbox[3:]+5<bbox[:3]):continue
    volume=max(0,(mm^other).volume())
    if volume>.001:collisions.append({'yaw':y,'pitch':p,'other':name,'volume_mm3':round(volume,6)})
    gap=float(mm.min_gap(other,5))
    if gap<nearest['gap_mm_capped_at_5']:nearest={'gap_mm_capped_at_5':gap,'other':name,'yaw':y,'pitch':p}
 rows.append({'source_solid':i,'source_BRep_valid':True,'all_cached_vertices_in_inflated_source_bounds':inside,'cad_bbox_mm':bb.tolist(),'bbox_inflation_mm':.001,'poses':130,'status':'PASS' if inside and not collisions else 'FAIL','nominal_overlap_samples':collisions,'nearest':nearest})
report={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','source_sha256':c['source_sha256'],'source_registration_max_error_mm':err,'source_registration_det':float(np.linalg.det(rot)),'checks':rows,'exact_connector_mesh_repaired':False,'main_geometry_changed':False,'scope':'Conservative separation of two complete documented CAD bounding boxes at130 discrete nominal poses. Source BRep validity from OCP diagnosis. It can prove nominal separation where boxes do not intersect; cannot prove detailed mating, plug fit, manufacturing tolerances or inter-sample motion. Original exact tessellation remains nonmanifold and no all-as-built fit is asserted.'}
(HERE/'lcd_connector_bounds_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('LCD_BOUNDS_COMPLETE',report['status'],[(r['source_solid'],r['nearest']) for r in rows],flush=True)
