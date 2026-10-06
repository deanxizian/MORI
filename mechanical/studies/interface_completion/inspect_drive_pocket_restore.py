"""Check old Blender hex clearance restoration against current nut slots."""
import sys,json,math
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'scripts'))
from common import *
from validate import Solid
from assembly_issue_fixes import boxm,replace
from interface_completion import axial
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH'}
m=ss['Drive_Bridge'].m;old=m;q=P['assembly_issue_fixes']['drive_nuts']
for n in q['ids']:
 c=(ss[n].lo+ss[n].hi)/2;mid=c.copy();mid[2]=62.;depth=2.1
 zone=boxm([mid[0]-4,mid[1]-4,59.675],[mid[0]+4,mid[1]+4,63.425])
 m+=axial(2.901,3.7,[mid[0],mid[1],61.55],[0,0,1],96)^(m^zone).hull()
 m-=axial(4.2/math.sqrt(3),depth+.03,mid,[0,0,1],6)
 m-=axial(1.2,24,c,[0,0,1]);ys=sorted([c[1],math.copysign(18,c[1])])
 m-=boxm([c[0]-2.5,ys[0],c[2]-.95],[c[0]+2.5,ys[1],c[2]+.95])
out={'added_mm3':(m-old).volume(),'removed_mm3':(old-m).volume(),'static_collisions':[]}
for n,s in ss.items():
 if n=='Drive_Bridge':continue
 v=max(0,((m-old)^s.m).volume())
 if v>.02:out['static_collisions'].append([n,v])
replace('Drive_Bridge',m)
s=Solid(bpy.data.objects[PREFIX+'Drive_Bridge']);tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cross,axis=1)/2;ns=cross/np.maximum(ar[:,None]*2,1e-15);indices=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),20002)[1:-1]));rays=[];tree=s.bvh()
for i in indices:
 p=tri[i].mean(0);n=ns[i];h,hn,j,d=tree.ray_cast(Vector(p-n*.0001),Vector(-n),300)
 if h is not None and j!=i and n@np.array(hn)<-.95 and d>.02:rays.append((float(d+.0001),p.tolist()))
rays.sort();out['minimum_mm']=rays[0][0];out['lowest']=rays[:10];out['under_1mm']=sum(r[0]<1 for r in rays)
(H/'drive_pocket_restore_inspection.json').write_text(json.dumps(out,indent=2))
print('DRIVE_RESTORE',out,flush=True)
