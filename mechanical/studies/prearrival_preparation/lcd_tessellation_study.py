"""Read-only STEP tessellation diagnosis; all candidates stay in this study."""
import json, hashlib, time
from pathlib import Path
from collections import Counter
import numpy as np
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepCheck import BRepCheck_Analyzer

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STEP=ROOT/'mechanical/sources/v1_2_verified_dimensions/1.85inch_touch_lcd_module-3d.stp'
reader=STEPControl_Reader(); reader.ReadFile(str(STEP)); reader.TransferRoots()
e=TopExp_Explorer(reader.OneShape(),TopAbs_SOLID); solids=[]
while e.More(): solids.append(e.Current()); e.Next()
results=[]
for idx in (107,108):
    s=solids[idx]; p=GProp_GProps(); BRepGProp.VolumeProperties_s(s,p)
    cadvol=p.Mass()
    for linear,angular in [(0.015,0.12),(0.001,0.04),(0.0002,0.015)]:
        BRepTools.Clean_s(s)
        BRepMesh_IncrementalMesh(s,linear,False,angular,False)
        rawv=[]; rawf=[]; face_stats=[]; faces=TopExp_Explorer(s,TopAbs_FACE)
        while faces.More():
            face=TopoDS.Face_s(faces.Current()); loc=TopLoc_Location()
            tri=BRep_Tool.Triangulation_s(face,loc)
            if tri is not None:
                start=len(rawv)
                for n in range(1,tri.NbNodes()+1):
                    pt=tri.Node(n).Transformed(loc.Transformation()); rawv.append((pt.X(),pt.Y(),pt.Z()))
                for n in range(1,tri.NbTriangles()+1):
                    a,b,c=tri.Triangle(n).Get()
                    if face.Orientation()==TopAbs_REVERSED: b,c=c,b
                    rawf.append((a-1+start,b-1+start,c-1+start))
                face_stats.append({'orientation':str(face.Orientation()),'triangles':tri.NbTriangles()})
            faces.Next()
        for digits in (7,6,5,4):
            lookup={}; verts=[]; mapping=[]
            for v in rawv:
                k=tuple(round(c,digits) for c in v)
                if k not in lookup: lookup[k]=len(verts); verts.append(v)
                mapping.append(lookup[k])
            tris=[]; seen=set(); deg=0; dupl=0
            for f in rawf:
                t=tuple(mapping[i] for i in f)
                if len(set(t))<3: deg+=1; continue
                key=tuple(sorted(t))
                if key in seen: dupl+=1; continue
                seen.add(key); tris.append(t)
            edges=Counter(tuple(sorted((t[j],t[(j+1)%3]))) for t in tris for j in range(3))
            ec=Counter(edges.values()); v=np.array(verts); f=np.array(tris)
            volume=float(np.sum(np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])))/6)
            out={'index':idx,'linear_mm':linear,'angular_rad':angular,'weld_decimals':digits,
                 'source_valid':BRepCheck_Analyzer(s).IsValid(),'source_volume_mm3':cadvol,
                 'mesh_volume_mm3':volume,'volume_delta_mm3':volume-cadvol,
                 'vertices':len(verts),'triangles':len(tris),'edge_multiplicity':dict(ec),
                 'degenerate_removed':deg,'duplicate_removed':dupl,'face_orientations':dict(Counter(x['orientation'] for x in face_stats))}
            results.append(out); print(json.dumps(out),flush=True)
            if set(ec)=={2}:
                path=HERE/f'lcd_solid_{idx}_{linear}_{digits}.json'
                path.write_text(json.dumps({'index':idx,'vertices_mm':verts,'triangles':tris,'study':out},separators=(',',':')))
    (HERE/'lcd_tessellation_diagnosis.json').write_text(json.dumps({'source_sha256':hashlib.sha256(STEP.read_bytes()).hexdigest(),'results':results},indent=2))
