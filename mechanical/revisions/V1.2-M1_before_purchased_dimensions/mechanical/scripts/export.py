"""Export each approved candidate in assembly coordinates; binary STL values in mm.
Uses a small self-contained STL writer/reader to make the unit contract explicit.
"""
import sys, struct, math, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def triangles(o):
    o.data.calc_loop_triangles(); vs=vertices_world(o)
    return [(vs[t.vertices[0]],vs[t.vertices[1]],vs[t.vertices[2]]) for t in o.data.loop_triangles]

def write_stl(o,path):
    tris=triangles(o)
    with path.open('wb') as f:
        f.write(b'MORI V1 millimetres; ASSEMBLED frame 1; prototype candidate'.ljust(80,b'\0'))
        f.write(struct.pack('<I',len(tris)))
        for a,b,c in tris:
            normal=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*normal,*a,*b,*c,0))

def read_stl(path):
    data=path.read_bytes(); n=struct.unpack_from('<I',data,80)[0]
    if len(data)!=84+n*50: raise ValueError('Binary STL length mismatch')
    vertices=[]; faces=[]; lookup={}; normals=[]
    for k in range(n):
        row=struct.unpack_from('<12fH',data,84+k*50); face=[]; normals.append(row[:3])
        for i in range(3):
            co=tuple(row[3+3*i:6+3*i]); key=tuple(round(v,5) for v in co)
            if key not in lookup: lookup[key]=len(vertices); vertices.append(co)
            face.append(lookup[key])
        faces.append(face)
    return vertices,faces,normals

def topology(vertices,faces,normals=None):
    edges={}; oriented={}; degenerate=0; volume=0.0; bad_normals=0
    for i,ids in enumerate(faces):
        a,b,c=[Vector(vertices[j]) for j in ids]; cross=(b-a).cross(c-a)
        if cross.length<1e-8 or len(set(ids))<3: degenerate+=1
        volume+=a.dot(b.cross(c))/6
        if normals and cross.length and cross.normalized().dot(Vector(normals[i]))<.999: bad_normals+=1
        for j in range(3):
            e=(ids[j],ids[(j+1)%3]); key=tuple(sorted(e)); edges[key]=edges.get(key,0)+1
            oriented[key]=oriented.get(key,0)+(1 if e==key else -1)
    return dict(vertices=len(vertices),triangles=len(faces),boundary_edges=sum(n==1 for n in edges.values()),
                nonmanifold_edges=sum(n!=2 for n in edges.values()),inconsistent_edges=sum(v!=0 for v in oriented.values()),
                degenerate_triangles=degenerate,signed_volume_mm3=volume,inconsistent_stl_normals=bad_normals)

def main():
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly']; load_collections(); COLS['DOCK'].hide_viewport=False; COLS['COUPONS'].hide_viewport=False; assembled()
    out=ROOT/'exports/stl'; out.mkdir(parents=True,exist_ok=True)
    candidates=sorted([o for o in parts(True) if o.get('export_candidate')],key=lambda o:o.name)
    items=[]
    # Remove only paths from our previous export manifest; never clear arbitrary user files.
    oldpath=ROOT/'reports/export_manifest.json'
    if oldpath.exists():
        old=json.loads(oldpath.read_text())
        new_names={o.name.removeprefix(PREFIX)+'.stl' for o in candidates}
        for item in old.get('parts',[]):
            p=ROOT/item['file']
            if p.parent==out and p.name not in new_names and p.exists(): p.unlink()
    for o in candidates:
        name=o.name.removeprefix(PREFIX); path=out/(name+'.stl'); write_stl(o,path)
        v,fa,no=read_stl(path); top=topology(v,fa,no)
        bb=[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]; orig=bounds(o)
        err=max(abs(bb[i][j]-orig[i][j]) for i in range(3) for j in range(2))
        ok=err<.01 and all(top[k]==0 for k in ['nonmanifold_edges','inconsistent_edges','degenerate_triangles','inconsistent_stl_normals']) and top['signed_volume_mm3']>0
        # Only printable geometry passes into the deliverable directory.
        if not ok:
            quarantine=ROOT/'reports/quarantined_stl'; quarantine.mkdir(exist_ok=True)
            path.rename(quarantine/path.name); file=str((quarantine/path.name).relative_to(ROOT))
        else: file=str(path.relative_to(ROOT))
        # Re-import every passed STL through Blender's actual STL operator at scale 1.
        importer=None
        if ok:
            before=set(bpy.data.objects)
            bpy.ops.wm.stl_import(filepath=str(path),global_scale=1.0,use_scene_unit=False,forward_axis='Y',up_axis='Z')
            imported=[ob for ob in bpy.data.objects if ob not in before]
            bpy.context.view_layer.update()
            bb2=bounds(imported[0]); imp_err=max(abs(bb2[i][j]-orig[i][j]) for i in range(3) for j in range(2))
            importer={'operator':'bpy.ops.wm.stl_import','global_scale':1.0,'use_scene_unit':False,'max_bbox_error_mm':imp_err,'status':'PASS' if imp_err<.01 else 'FAIL'}
            ok=ok and imp_err<.01
            for ob in imported:
                me=ob.data; bpy.data.objects.remove(ob,do_unlink=True)
                if me.users==0: bpy.data.meshes.remove(me)
        items.append(dict(id=name,file=file,blender_reimport=importer,status='PASS' if ok else 'FAIL',bbox_mm=bb,dimensions_mm=[b-a for a,b in bb],
                          max_roundtrip_coordinate_error_mm=err,topology=top,sha256=hashlib.sha256((ROOT/file).read_bytes()).hexdigest()))
        print('MORI STL',name,'PASS' if ok else 'FAIL',flush=True)
    result=dict(units='mm; scale factor 1.0; scene display scale_length 0.001',frame=1,yaw_deg=0,wheel_spin_deg=0,
                candidate_count=len(candidates),exported_count=sum(i['status']=='PASS' for i in items),parts=items,
                limitations='Candidate topology/roundtrip only. No slicer certification, exact all-pairs self intersection or complete minimum wall proof.')
    save_json(ROOT/'reports/export_manifest.json',result)

if __name__=='__main__': main()
