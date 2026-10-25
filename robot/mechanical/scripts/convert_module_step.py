"""Read-only conversion of the manufacturer's WeAct STEP into a mm mesh cache.

Run with Python + cadquery-ocp==7.8.1.1.post1. Blender uses the checked-in cache;
it does not require OCP. No part is rescaled, trimmed, or fitted to the robot.
"""
import hashlib
import json
import importlib.metadata
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.ShapeFix import ShapeFix_Shape

import sys
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'sources/populated_P5/vendor'
STEP=SOURCE/(sys.argv[1]+'.step')
reader = STEPControl_Reader()
assert 'SI_UNIT(.MILLI.,.METRE.)' in ''.join(STEP.read_text().split()), 'Unverified source units'
assert reader.ReadFile(str(STEP)) == IFSelect_RetDone
reader.TransferRoots()
shape = reader.OneShape()
explorer = TopExp_Explorer(shape, TopAbs_SOLID)
solids = []
while explorer.More():
    solid = explorer.Current()
    cad_valid = BRepCheck_Analyzer(solid).IsValid()
    if False:
        fixer = ShapeFix_Shape(solid)
        fixer.SetPrecision(1e-5)
        fixer.SetMinTolerance(1e-7)
        fixer.SetMaxTolerance(1e-4)
        fixer.Perform()
        solid = fixer.Shape()
    # Very small connector fillets need finer tessellation than the round glass.
    fine_connector = False
    BRepMesh_IncrementalMesh(solid, 0.001 if fine_connector else 0.015,
                            False, 0.04 if fine_connector else 0.12, False)
    vertices, triangles, lookup = [], [], {}
    removed_degenerate = 0
    faces = TopExp_Explorer(solid, TopAbs_FACE)
    while faces.More():
        face = TopoDS.Face_s(faces.Current())
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        if triangulation is None:
            props = GProp_GProps()
            BRepGProp.SurfaceProperties_s(face, props)
            if abs(props.Mass()) < 1e-9:
                removed_degenerate += 1
                faces.Next()
                continue
            raise ValueError(f'CAD solid {len(solids)} face has no triangulation; area={props.Mass()} mm2')
        mapping = {}
        for i in range(1, triangulation.NbNodes() + 1):
            pt = triangulation.Node(i).Transformed(loc.Transformation())
            v = (pt.X(), pt.Y(), pt.Z())
            key = tuple(round(x, 7) for x in v)
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(v)
            mapping[i] = lookup[key]
        for i in range(1, triangulation.NbTriangles() + 1):
            a, b, c = triangulation.Triangle(i).Get()
            if face.Orientation() == TopAbs_REVERSED:
                b, c = c, b
            tri = [mapping[j] for j in (a, b, c)]
            if len(set(tri)) != 3:
                removed_degenerate += 1
                continue
            triangles.append(tri)
        faces.Next()
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(solid, box, False, False)
    lo, hi = box.CornerMin(), box.CornerMax()
    solids.append({'cad_valid':cad_valid,'index': len(solids), 'vertices_mm': vertices, 'triangles': triangles,
                   'degenerate_tessellation_faces_removed': removed_degenerate,
                   'cad_bounds_xyz_mm': [[lo.X(), hi.X()], [lo.Y(), hi.Y()], [lo.Z(), hi.Z()]]})
    explorer.Next()
    if len(solids) % 25 == 0:
        print('STEP solids', len(solids), flush=True)
cache={'source_file':str(STEP.relative_to(ROOT.parent)),'source_sha256':hashlib.sha256(STEP.read_bytes()).hexdigest(),'units':'mm','scale_factor':1.0,'linear_deflection_mm':.015,'solid_count':len(solids),'solids':solids,'bounds_xyz_mm':[[min(x['cad_bounds_xyz_mm'][i][0] for x in solids),max(x['cad_bounds_xyz_mm'][i][1] for x in solids)] for i in range(3)],'status':'VENDOR_CAD_NOT_MEASURED','limit':'Family model; SKU resistor setting is not electrically verified. No wire or loose mating connectors.'}
path=SOURCE/(sys.argv[1]+'_mesh.json');path.write_text(json.dumps(cache,separators=(',',':')));print('POL_CAD',len(solids),cache['bounds_xyz_mm'],flush=True)
