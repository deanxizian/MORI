"""Read-only diagnostic: separate real thin webs from functional lead-ins."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts(True)}
audit=json.loads((ROOT/'reports/interface_printability.json').read_text());out=[]
for row in audit['rows']:
 if row['id'] not in ['Pitch_Yoke','Motor_Retainer','Yaw_Reaction_Link']:continue
 s=ss[row['id']];points=np.array([r[1] for r in row['critical_samples']]);sections=[]
 for axis in range(3):
  coords=sorted(set(round(float(p[axis]),2) for p in points))
  ij=[i for i in range(3) if i!=axis];tr=np.zeros((3,4));tr[0,ij[0]]=1;tr[1,ij[1]]=1;tr[2,axis]=1
  if np.linalg.det(tr[:,:3])<0:tr[0,ij[0]]=-1
  m=s.m.transform(tr)
  for d in coords[:4]:
   polys=m.slice(d).to_polygons();sections.append(dict(axis=axis,coordinate_mm=d,plane_axes=ij,x_sign=int(tr[0,ij[0]]),polygons=[p.tolist() for p in polys]))
 out.append(dict(id=row['id'],bounds=[s.lo.tolist(),s.hi.tolist()],critical=row['critical_samples'],sections=sections))
report=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),rows=out,status='NOT_TESTED',scope='Diagnostic exact sections; no structural acceptance or edits')
(HERE/'thin_sections.json').write_text(json.dumps(report,indent=2)+'\n')
print('THIN_SECTIONS',[(r['id'],len(r['sections'])) for r in out])
