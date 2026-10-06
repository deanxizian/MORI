"""Read-only M1.41 interface inventory. No generated or native geometry changed."""
import sys, json, hashlib, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from mathutils.bvhtree import BVHTree

load_collections()
for c in bpy.data.collections:
    if c.get('mori_owner')==OWNER: c.hide_viewport=False
assembled();bpy.context.view_layer.update()
classify=json.loads((ROOT/'reports/manufacturing_classification.json').read_text())
ids={n for k,v in classify['categories'].items() if k!='auxiliary_print' for n in v}
solids={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids if bpy.data.objects.get(PREFIX+n)}
prints={n:s for n,s in solids.items() if s.o.get('category')=='PRINTABLE'}
bvhs={n:BVHTree.FromPolygons(s.v.tolist(),s.f.tolist(),all_triangles=True) for n,s in prints.items()}

def axis_data(s):
    tri=s.v[s.f];cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cr,axis=1)/2
    ns=cr/np.maximum(2*ar[:,None],1e-12);groups={}
    for n,a in zip(ns,ar):
        if n[np.argmax(abs(n))]<0:n=-n
        k=tuple(np.round(n,4));groups[k]=groups.get(k,0)+a
    axis=np.array(max(groups,key=groups.get));axis/=np.linalg.norm(axis)
    mid=(s.lo+s.hi)/2;proj=(s.v-mid)@axis
    return axis,mid,float(proj.max()-proj.min())

inserts=[]
for name in sorted(solids):
    if 'Insert' not in name:continue
    s=solids[name];axis,mid,length=axis_data(s)
    m3=name.startswith(('Frame_Insert','Shell_Insert'))
    # Manufacturer W is measured from the PILOT bore, not the insert crest OD.
    pilot,wallmin=(4.0,1.6) if m3 else (3.2,1.3)
    u=np.cross(axis,[1,0,0] if abs(axis[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u)
    candidates=[]
    for pn,ps in prints.items():
        if np.any(mid<ps.lo-8) or np.any(mid>ps.hi+8):continue
        rays=[]
        for dz in [-length*.3,0,length*.3]:
            for th in np.arange(0,360,10):
                d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th))
                hit,normal,idx,dist=bvhs[pn].ray_cast(Vector(mid+dz*axis),Vector(d),15)
                if hit is None or dist>4 or np.dot(np.array(normal),d)>0:continue
                out,nn,j,dd=bvhs[pn].ray_cast(hit+Vector(d)*.001,Vector(d),25)
                if out is not None and np.dot(np.array(nn),d)>0:rays.append(float(dist+.001+dd-pilot/2))
        if rays:candidates.append({'host':pn,'samples':len(rays),'min_pilot_wall_mm':min(rays)})
    host=max(candidates,key=lambda x:x['samples']) if candidates else None
    inserts.append({'id':name,'center_mm':mid.tolist(),'axis':axis.tolist(),'length_mm':length,
      'reference':'SL-M3x4' if m3 else 'SL-M2x3','reference_pilot_diameter_mm':pilot,
      'minimum_pilot_wall_mm':wallmin,'screen':host,
      'status':'PASS' if host and host['min_pilot_wall_mm']>=wallmin-.005 else 'FAIL',
      'scope':'Finite radial wall screen only. Blind depth, installation access and material coupon remain separate.'})

walls=[]
for name,s in sorted(prints.items()):
    tri=s.v[s.f];cr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cr,axis=1)/2;ns=cr/np.maximum(2*ar[:,None],1e-12)
    indices=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),20002)[1:-1]));samples=[]
    for i in indices:
        p=tri[i].mean(0);n=ns[i];hit,hn,j,d=bvhs[name].ray_cast(Vector(p-n*1e-4),Vector(-n),300)
        if hit is not None and j!=i and float(n@np.array(hn))<-.95 and d>.02:samples.append((float(d+.0001),p.tolist()))
    samples.sort();walls.append({'id':name,'samples':len(samples),'minimum_mm':samples[0][0] if samples else None,'under_1mm':sum(x[0]<1 for x in samples),'critical_samples':samples[:12], 'scope':'Opposed normal rays; functional edges/lead-ins must be classified. Not proof of global minimum or strength.'})

geometry={n:{'bounds_mm':[s.lo.tolist(),s.hi.tolist()],'volume_mm3':s.m.volume(),'group':s.o.get('group'),'category':s.o.get('category'),'label':s.o.get('label_zh')} for n,s in sorted(solids.items())}
for n in ['Yaw_Horn','Pitch_Horn','Pitch_Trunnion_L','Pitch_Trunnion_R','Yaw_Bearing','Pitch_Bearing_L','Pitch_Bearing_R','MCU_Motion']:
    if n in solids:
        s=solids[n];geometry[n]['vertices_mm']=s.v.tolist();geometry[n]['triangles']=s.f.tolist()
record={'revision':P['revision'],'blender':bpy.app.version_string,'hardware_sha256':hashlib.sha256((PROJECT/'contracts/components.json').read_bytes()).hexdigest(),
 'geometry_changed':False,'native_files_changed':False,'inserts':inserts,'walls':walls,'geometry':geometry,
 'head_transmission':'User 2026-09-29 retains SCS0009 and defers horn interface until manufacturer data; no substitution or inferred mating dimensions.'}
(HERE/'baseline_audit.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print('CURRENT_AUDIT',len(prints),'prints',len(inserts),'inserts',[(a['id'],round(a['screen']['min_pilot_wall_mm'],3)) for a in inserts if a['status']=='FAIL'],flush=True)
