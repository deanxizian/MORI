"""Inspect the distributor-hosted STEP without importing into the robot."""
from pathlib import Path
import json, hashlib, re
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.STEPControl import STEPControl_Reader

HERE = Path(__file__).resolve().parent
source = HERE/'sources/SCS009-20230110-S.stp'
text = source.read_text()
assert 'SI_UNIT(.MILLI.,.METRE.)' in text
doc = TDocStd_Document(TCollection_ExtendedString('XCAF'))
reader = STEPCAFControl_Reader()
reader.ReadFile(str(source)); reader.Transfer(doc)
tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
roots = TDF_LabelSequence(); tool.GetFreeShapes(roots)
rows = []

def walk(label, path=''):
    attr = TDataStd_Name()
    name = attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else '?'
    referred = TDF_Label()
    shape_label = label
    if tool.IsReference_s(label):
        tool.GetReferredShape_s(label, referred)
        shape_label = referred
    children = TDF_LabelSequence(); tool.GetComponents_s(shape_label, children)
    if children.Length():
        for i in range(1, children.Length()+1): walk(children.Value(i), path+'/'+name)
        return
    shape = tool.GetShape_s(label)
    box = Bnd_Box(); BRepBndLib.AddOptimal_s(shape, box, False, False)
    bounds = list(box.Get())
    count=0; ex=TopExp_Explorer(shape,TopAbs_SOLID)
    while ex.More(): count+=1; ex.Next()
    row={'path':path, 'name':name, 'bounds_mm':bounds, 'size_mm':[bounds[i+3]-bounds[i] for i in range(3)], 'solid_count':count, 'valid':BRepCheck_Analyzer(shape).IsValid()}
    # This local part view is only for inspecting the supplied file.
    # No assumptions about robot placement or purchased variant are made.
    BRepMesh_IncrementalMesh(shape, .025, False, .15, True)
    filename='REFERENCE_ONLY_part_'+str(len(rows))+'.stl'
    writer=StlAPI_Writer(); writer.ASCIIMode=False; writer.Write(shape,str(HERE/filename))
    row['inspection_stl']=filename
    rows.append(row)

for i in range(1,roots.Length()+1):walk(roots.Value(i))
flat = STEPControl_Reader(); flat.ReadFile(str(source)); flat.TransferRoots()
world = flat.OneShape(); box = Bnd_Box(); BRepBndLib.AddOptimal_s(world, box, False, False)
world_bounds = list(box.Get()); world_rows=[]
ex = TopExp_Explorer(world, TopAbs_SOLID)
while ex.More():
    shape=ex.Current(); box=Bnd_Box(); BRepBndLib.AddOptimal_s(shape,box,False,False)
    filename=f'REFERENCE_ONLY_world_part_{len(world_rows)}.stl'
    BRepMesh_IncrementalMesh(shape,.025,False,.15,True)
    writer=StlAPI_Writer(); writer.ASCIIMode=False; writer.Write(shape,str(HERE/filename))
    world_rows.append({'bounds_mm':list(box.Get()),'stl':filename})
    ex.Next()
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':'mm','scale_factor':1,'part_class':'PURCHASED_REFERENCE','evidence_status':'ASSUMED','matching_horn_included':False,'source_class':'DISTRIBUTOR_HOSTED_CAD; manufacturer provenance and exact purchased revision not yet confirmed','parts_local_coordinates':rows,'world_bounds_mm':world_bounds,'world_parts':world_rows,'products':re.findall(r"PRODUCT\s*\([^;]+",text),'main_model_modified':False}
(HERE/'servo_step_inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for row in rows:print(json.dumps(row,ensure_ascii=False))
