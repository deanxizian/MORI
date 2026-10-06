from pathlib import Path
import sys,json,hashlib
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'scripts'))
from convert_populated_pcbs import *
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
out={}
for filename in ['Waveshare_SC09_SC09_ARM.step','Waveshare_SC09_SC09-SERVO.step']:
 p=H/'sources'/filename;r=STEPControl_Reader();r.ReadFile(str(p));r.TransferRoots();shape=r.OneShape();rows=[];ex=TopExp_Explorer(shape,TopAbs_SOLID)
 while ex.More():
  solid=ex.Current()
  try:row=tessellate(solid)
  except ValueError as e:row={'cad_bounds_xyz_mm':bounds(solid),'cad_valid':BRepCheck_Analyzer(solid).IsValid(),'mesh_status':'BLOCKED','mesh_error':str(e)}
  cylinders=[];fe=TopExp_Explorer(solid,TopAbs_FACE)
  while fe.More():
   fa=BRepAdaptor_Surface(TopoDS.Face_s(fe.Current()))
   if fa.GetType()==GeomAbs_Cylinder:
    c=fa.Cylinder();loc=c.Location();axis=c.Axis().Direction();cylinders.append({'radius_mm':c.Radius(),'axis':[axis.X(),axis.Y(),axis.Z()],'origin_mm':[loc.X(),loc.Y(),loc.Z()],'uv_limits':[fa.FirstUParameter(),fa.LastUParameter(),fa.FirstVParameter(),fa.LastVParameter()]})
   fe.Next()
  row['cylinders']=cylinders;rows.append(row);ex.Next()
 out[filename]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'units':'mm','bounds':bounds(shape),'solids':rows,'status':'VENDOR_DOCUMENTED for SC09 only; SCS0009 compatibility NOT_TESTED'}
 print(filename,'solids',len(rows),'bounds',bounds(shape),flush=True)
(H/'SC09_CAD_inspection.json').write_text(json.dumps(out,separators=(',',':')))
(H/'SC09_CAD_dimensions.json').write_text(json.dumps({n:{**q,'solids':[{k:v for k,v in a.items() if k not in ['vertices_mm','triangles']} for a in q['solids']]} for n,q in out.items()},indent=2))
