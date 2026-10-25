"""Tessellate current published PCB assemblies, retaining component references.
Run with OCP Python. All lengths are mm; no hardware resizing or healing.
"""
import hashlib
import json
from pathlib import Path
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box

OUT=Path(__file__).resolve().parents[1]/'sources/populated_P5'
def bounds(shape):
    b=Bnd_Box(); BRepBndLib.AddOptimal_s(shape,b,False,False)
    xyz=b.Get(); return [[xyz[i],xyz[i+3]] for i in range(3)]

def tessellate(solid):
    BRepMesh_IncrementalMesh(solid,.015,False,.12,False)
    verts=[]; triangles=[]; lookup={}; faces=TopExp_Explorer(solid,TopAbs_FACE)
    while faces.More():
        face=TopoDS.Face_s(faces.Current()); loc=TopLoc_Location()
        t=BRep_Tool.Triangulation_s(face,loc)
        if t is None: raise ValueError('Missing tessellation; do not silently drop CAD faces')
        mapping={}
        for i in range(1,t.NbNodes()+1):
            p=t.Node(i).Transformed(loc.Transformation());v=(p.X(),p.Y(),p.Z())
            key=tuple(round(x,7) for x in v)
            if key not in lookup:lookup[key]=len(verts);verts.append(v)
            mapping[i]=lookup[key]
        for i in range(1,t.NbTriangles()+1):
            a,b,c=t.Triangle(i).Get()
            if face.Orientation()==TopAbs_REVERSED:b,c=c,b
            tri=[mapping[j] for j in (a,b,c)]
            if len(set(tri))==3:triangles.append(tri)
        faces.Next()
    return {'vertices_mm':verts,'triangles':triangles,'cad_valid':BRepCheck_Analyzer(solid).IsValid(),
            'cad_bounds_xyz_mm':bounds(solid)}

if __name__=='__main__':
    for kind in ['motion','imu','power','rear']:
        source=OUT/f'{kind}.step'
        assert 'SI_UNIT(.MILLI.,.METRE.)' in source.read_text()
        doc=TDocStd_Document(TCollection_ExtendedString('XCAF'))
        r=STEPCAFControl_Reader();r.ReadFile(str(source));r.Transfer(doc)
        tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());roots=TDF_LabelSequence();tool.GetFreeShapes(roots)
        assert roots.Length()==1
        sequence=TDF_LabelSequence();tool.GetComponents_s(roots.Value(1),sequence)
        components=[]
        for i in range(1,sequence.Length()+1):
            label=sequence.Value(i);attribute=TDataStd_Name();label.FindAttribute(TDataStd_Name.GetID_s(),attribute)
            name=attribute.Get().ToExtString()
            if name.startswith('=>'):name='PCB'
            shape=tool.GetShape_s(label); solids=[]; explorer=TopExp_Explorer(shape,TopAbs_SOLID)
            while explorer.More():
                solids.append(tessellate(explorer.Current()));explorer.Next()
            assert solids,(kind,name,'No solids')
            components.append({'reference':name,'bounds_xyz_mm':bounds(shape),'solids':solids})
        result={'board':kind,'source_step_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'units':'mm','linear_deflection_mm':.015,'angular_deflection_rad':.12,'scale_factor':1,
                'components':components,'limits':'Library geometry; does not certify all selected supplier variants or installed leads.'}
        (OUT/f'{kind}_mesh.json').write_text(json.dumps(result,separators=(',',':')))
        print('CONVERTED',kind,len(components),sum(len(c['solids']) for c in components),flush=True)
