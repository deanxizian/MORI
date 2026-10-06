"""Read the unmodified vendor STEP B-rep; no mesh healing or CAD alteration."""
from pathlib import Path
import json, hashlib, math, sys
import OCP
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCP.TopoDS import TopoDS
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Section
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRep import BRep_Tool
from OCP.gp import gp_Pnt, gp_Pln, gp_Dir

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SOURCE=ROOT/'hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 3D.step'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bounds(shape):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape,b,False,False)
    return list(b.Get())
def volume(shape):
    props=GProp_GProps();BRepGProp.VolumeProperties_s(shape,props)
    return props.Mass()
def common(a,b):
    op=BRepAlgoAPI_Common(a,b);op.Build()
    assert op.IsDone()
    return op.Shape()
source_hash=digest(SOURCE)
reader=STEPControl_Reader();reader.ReadFile(str(SOURCE));reader.TransferRoots()
ex=TopExp_Explorer(reader.OneShape(),TopAbs_SOLID);solids=[]
while ex.More():solids.append(ex.Current());ex.Next()
assert len(solids)==224
pcb=solids[0];header=solids[32];pb=bounds(pcb)
faces=TopExp_Explorer(pcb,TopAbs_FACE);cylinders=[]
while faces.More():
    surf=BRepAdaptor_Surface(TopoDS.Face_s(faces.Current()))
    if surf.GetType()==GeomAbs_Cylinder:
        c=surf.Cylinder();p=c.Location();d=c.Axis().Direction()
        if abs(d.Z())>.99999:
            cylinders.append({'xy_mm':[p.X(),p.Y()],'diameter_mm':2*c.Radius()})
    faces.Next()
audit=json.loads((HERE.parent/'weact_alignment_audit.json').read_text())
rows=[]
for row in audit['rows']:
    if not row['pin'].startswith('E'):continue
    xw,yw=row['world_xy_mm'];target=[yw+160.078,61.016-xw]
    hole=min(cylinders,key=lambda c:math.dist(c['xy_mm'],target))
    assert math.dist(hole['xy_mm'],target)<.005
    x,y=hole['xy_mm'];z0,z1=pb[2],pb[5]
    localbox=BRepPrimAPI_MakeBox(gp_Pnt(x-.8,y-.8,z0),1.6,1.6,z1-z0).Shape()
    pin=common(header,localbox);bb=bounds(pin)
    section=BRepAlgoAPI_Section(pin,gp_Pln(gp_Pnt(0,0,(z0+z1)/2),gp_Dir(0,0,1)),False)
    section.Build();assert section.IsDone()
    vertices=[];ve=TopExp_Explorer(section.Shape(),TopAbs_VERTEX)
    while ve.More():
        p=BRep_Tool.Pnt_s(TopoDS.Vertex_s(ve.Current()))
        q=[p.X(),p.Y()]
        if not any(math.dist(q,v)<1e-6 for v in vertices):vertices.append(q)
        ve.Next()
    pin_center=[(bb[0]+bb[3])/2,(bb[1]+bb[4])/2]
    ideal=BRepPrimAPI_MakeBox(gp_Pnt(x-.32,y-.32,z0),.64,.64,z1-z0).Shape()
    rows.append({'pin':row['pin'],'STEP_hole':hole,'source_header_clip_bounds_mm':bb,
        'source_header_mid_section_vertices_xy_mm':vertices,
        'source_header_section_bbox_xy_mm':[bb[3]-bb[0],bb[4]-bb[1]],
        'source_header_section_corner_circle_mm':2*max(math.dist(pin_center,p)for p in vertices),
        'source_header_pin_center_mm':pin_center,'pin_to_hole_model_offset_mm':math.dist(pin_center,hole['xy_mm']),
        'original_pin_PCB_overlap_mm3':volume(common(pin,pcb)),
        'ideal_square_064_PCB_overlap_mm3':volume(common(ideal,pcb))})
whole=[]
for name,idx in [('E/P5',32),('D/P4',159),('C/P3',160),('B/P2',161),('A/P1',162)]:
    whole.append({'connector':name,'solid_index':idx,'original_STEP_PCB_overlap_mm3':volume(common(solids[idx],pcb))})
assert digest(SOURCE)==source_hash
result={'date':'2026-10-01','source':str(SOURCE.relative_to(ROOT)),'source_sha256':source_hash,
    'tool':{'python':sys.version,'OCP':OCP.__version__},'source_solid_count':len(solids),'PCB_bounds_mm':pb,
    'scope':'Exact source B-rep model inspection only. Not a manufacturer drill/finished-hole specification, actual measurement or approval.',
    'E_pin_rows':rows,'original_header_intersections':whole,
    'ideal_square_pin_calculation':{'nominal_width_mm':.64,'nominal_diagonal_mm':.64*math.sqrt(2),'source_model_hole_diameter_mm':.812,
        'nominal_diametral_interference_mm':.64*math.sqrt(2)-.812,'largest_sharp_square_side_without_clearance_mm':.812/math.sqrt(2)},
    'physical_measurement':'NOT_TESTED','core_finished_hole_specification':'BLOCKED'}
(HERE/'step_inspection.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'source_header_sections':[r['source_header_section_bbox_xy_mm']for r in rows],
    'source_pin_overlap_total_mm3':sum(r['original_pin_PCB_overlap_mm3']for r in rows),
    'ideal_064_overlap_total_mm3':sum(r['ideal_square_064_PCB_overlap_mm3']for r in rows),
    'original_header_intersections':whole},indent=2))
