"""Read-only P3 power CAD extraction. Run each stage in its indicated runtime.

inventory: KiCad Python; mesh: OCP Python; blend: Blender --background --python.
The output is an independent component review, not a qualified robot assembly.
"""
from pathlib import Path
import hashlib
import json
import sys
import subprocess
import time

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT/'mechanical/studies/power_P3_detail'
OUT.mkdir(parents=True, exist_ok=True)
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LIB = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inventory():
    import pcbnew
    source = PROJECT/'hardware/v1_2/kicad/MORI_power_P3/MORI_power_P3.kicad_pcb'
    source_hash = sha(source)
    snapshot = OUT/'MORI_power_P3_SOURCE_READONLY.kicad_pcb'
    snapshot.write_bytes(source.read_bytes())
    board = pcbnew.LoadBoard(str(snapshot))
    footprints = []
    for fp in board.GetFootprints():
        models = []
        for m in fp.Models():
            path = Path(str(m.m_Filename).replace('${KICAD10_3DMODEL_DIR}', str(LIB)))
            models.append({'path': str(m.m_Filename), 'resolved': str(path),
                           'exists': path.is_file(), 'sha256': sha(path) if path.is_file() else None})
        footprints.append({'reference': fp.GetReference(), 'value': fp.GetValue(),
                           'footprint': str(fp.GetFPID().GetLibItemName()),
                           'xy_mm': [fp.GetPosition().x/1e6, fp.GetPosition().y/1e6],
                           'rotation_deg': fp.GetOrientationDegrees(), 'side': 'B' if fp.IsFlipped() else 'F',
                           'models': models, 'attributes': int(fp.GetAttributes())})
    missing = [f for f in footprints if not any(m['exists'] for m in f['models'])
               and not f['reference'].startswith(('H', 'TP'))]
    target = OUT/'MORI_power_P3_POPULATED_PARTIAL.step'
    cmd = [CLI, 'pcb', 'export', 'step', '--force', '--no-dnp', '--user-origin', '0x0mm',
           '--define-var', f'KICAD10_3DMODEL_DIR={LIB}', '-o', str(target), str(snapshot)]
    t = time.time()
    run = subprocess.run(cmd, capture_output=True, text=True)
    (OUT/'export.log').write_text(run.stdout+'\n'+run.stderr)
    if run.returncode: raise RuntimeError(run.stderr)
    # Newer work-in-progress is inventoried, not silently promoted to a handoff.
    r1 = PROJECT/'hardware/v1_2/kicad/MORI_power_P3R1/MORI_power_P3R1.kicad_pcb'
    newer = {'exists': r1.exists(), 'adopted': False, 'reason': 'No P3R1 mechanical handoff found; keep P3 input explicit'}
    if r1.exists():
        b1 = pcbnew.LoadBoard(str(r1)); old = {f['reference']: f for f in footprints}; changes = []
        for f in b1.GetFootprints():
            a = old.get(f.GetReference())
            now = [f.GetPosition().x/1e6, f.GetPosition().y/1e6, f.GetOrientationDegrees(), 'B' if f.IsFlipped() else 'F']
            if a and now != a['xy_mm']+[a['rotation_deg'], a['side']]: changes.append(f.GetReference())
        newer.update({'source': str(r1.relative_to(PROJECT)), 'sha256': sha(r1), 'changed_placement_references': sorted(changes)})
    assert sha(source) == source_hash, 'Hardware source changed during extraction; repeat with a fresh snapshot'
    data = {'source': str(source.relative_to(PROJECT)), 'source_sha256': source_hash,
            'snapshot_sha256': sha(snapshot), 'step_sha256': sha(target),
            'kicad_version': subprocess.check_output([CLI, 'version'], text=True).strip(),
            'units': 'mm', 'board_thickness_mm': board.GetDesignSettings().GetBoardThickness()/1e6,
            'footprint_count': len(footprints), 'existing_model_references': sum(any(m['exists'] for m in f['models']) for f in footprints),
            'missing_component_references': [f['reference'] for f in missing], 'footprints': footprints,
            'newer_work_in_progress': newer, 'command': cmd, 'exit_code': run.returncode,
            'elapsed_s': round(time.time()-t, 1), 'hardware_source_unchanged': True,
            'limitations': ['Partial populated model from generic KiCad library solids, not measured hardware',
                           'No matching connector plugs, wire bends, solder or complete selected-SKU qualification',
                           'Native DNP attributes excluded; value text alone is not an assembly-option guarantee',
                           'P3 routing style was rejected by user; this mechanical reference does not approve that routing',
                           'Main MORI assembly and its geometry/contract remain unchanged']}
    (OUT/'inventory.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print('INVENTORY', data['footprint_count'], 'models', data['existing_model_references'], 'missing', data['missing_component_references'], flush=True)


def mesh():
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
    def bounds(shape):
        b = Bnd_Box(); BRepBndLib.AddOptimal_s(shape, b, False, False)
        xyz = b.Get(); return [[xyz[i], xyz[i+3]] for i in range(3)]
    def triangulate(solid):
        BRepMesh_IncrementalMesh(solid, .02, False, .12, False)
        verts = []; triangles = []; lookup = {}; faces = TopExp_Explorer(solid, TopAbs_FACE)
        while faces.More():
            face = TopoDS.Face_s(faces.Current()); loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(face, loc)
            if tri is None: raise ValueError('CAD face has no triangulation')
            mapping = {}
            for i in range(1, tri.NbNodes()+1):
                p = tri.Node(i).Transformed(loc.Transformation()); v = (p.X(), p.Y(), p.Z())
                key = tuple(round(x, 7) for x in v)
                if key not in lookup: lookup[key] = len(verts); verts.append(v)
                mapping[i] = lookup[key]
            for i in range(1, tri.NbTriangles()+1):
                a, b, c = tri.Triangle(i).Get()
                if face.Orientation() == TopAbs_REVERSED: b, c = c, b
                ids = [mapping[x] for x in [a, b, c]]
                if len(set(ids)) == 3: triangles.append(ids)
            faces.Next()
        return {'vertices_mm': verts, 'triangles': triangles, 'cad_valid': BRepCheck_Analyzer(solid).IsValid()}
    source = OUT/'MORI_power_P3_POPULATED_PARTIAL.step'
    assert 'SI_UNIT(.MILLI.,.METRE.)' in source.read_text()
    doc = TDocStd_Document(TCollection_ExtendedString('XCAF'))
    r = STEPCAFControl_Reader(); r.ReadFile(str(source)); r.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); roots = TDF_LabelSequence(); tool.GetFreeShapes(roots)
    assert roots.Length() == 1
    seq = TDF_LabelSequence(); tool.GetComponents_s(roots.Value(1), seq); components = []
    for i in range(1, seq.Length()+1):
        label = seq.Value(i); attribute = TDataStd_Name(); label.FindAttribute(TDataStd_Name.GetID_s(), attribute)
        name = attribute.Get().ToExtString()
        if name.startswith('=>'): name = 'PCB'
        shape = tool.GetShape_s(label); solids = []; ex = TopExp_Explorer(shape, TopAbs_SOLID)
        while ex.More(): solids.append(triangulate(ex.Current())); ex.Next()
        assert solids, name
        components.append({'reference': name, 'bounds_mm': bounds(shape), 'solids': solids})
    data = {'units': 'mm', 'scale': 1, 'source_sha256': sha(source), 'linear_deflection_mm': .02, 'components': components}
    (OUT/'mesh.json').write_text(json.dumps(data, separators=(',', ':')))
    check = {'components': len(components), 'solids': sum(len(c['solids']) for c in components),
             'all_solids_cad_valid': all(s['cad_valid'] for c in components for s in c['solids']),
             'pcb_bounds_mm': next(c['bounds_mm'] for c in components if c['reference'] == 'PCB'),
             'missing_components_not_silently_filled': True, 'scale': 1, 'units': 'mm'}
    (OUT/'conversion_check.json').write_text(json.dumps(check, indent=2))
    print('MESH_CHECK', check, flush=True)


def blend():
    import bpy
    from mathutils import Vector
    data = json.loads((OUT/'mesh.json').read_text()); inv = json.loads((OUT/'inventory.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene; scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = .001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    def mat(name, color, metal=0):
        m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value = (*color, 1)
        bsdf.inputs['Metallic'].default_value = metal; bsdf.inputs['Roughness'].default_value = .42
        return m
    green = mat('PCB', (.035, .27, .18)); dark = mat('Packages', (.075, .085, .10)); connector = mat('Connectors', (.70, .71, .65))
    copper = mat('Metal', (.55, .56, .59), .6); amber = mat('Missing CAD labels only', (1, .33, .04))
    actual = bpy.data.collections.new('P3_LIBRARY_GEOMETRY_PARTIAL'); scene.collection.children.link(actual)
    for c in data['components']:
        for i, s in enumerate(c['solids']):
            ref = c['reference']; me = bpy.data.meshes.new(ref+f'_{i}'); me.from_pydata(s['vertices_mm'], [], s['triangles']); me.update()
            o = bpy.data.objects.new(ref+f'_{i}', me); actual.objects.link(o)
            material = green if ref == 'PCB' else connector if ref.startswith(('J','P')) else dark
            if i > 0 and ref != 'PCB': material = copper
            me.materials.append(material)
            o['source_reference'] = ref; o['data_status'] = 'NATIVE_DESIGN_LIBRARY_NOT_MEASURED'; o['units'] = 'mm'
    labels = bpy.data.collections.new('MISSING_MODELS_POSITION_MARKERS_NOT_COMPONENTS'); scene.collection.children.link(labels)
    for f in inv['footprints']:
        if f['reference'] not in inv['missing_component_references']: continue
        cu = bpy.data.curves.new('Missing '+f['reference'], 'FONT'); cu.body = '? '+f['reference']; cu.size = 1.8
        o = bpy.data.objects.new('MISSING_'+f['reference'], cu); labels.objects.link(o)
        o.location = (f['xy_mm'][0], -f['xy_mm'][1], 2.0); cu.materials.append(amber)
        o['role'] = 'annotation_only_no_dimensions'; o['value'] = f['value']
    scene['review_scope'] = 'Partial P3 populated library reference; no whole-robot fit approval'
    scene['missing_component_references'] = ', '.join(inv['missing_component_references'])
    world = bpy.data.worlds.new('Studio'); scene.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.16, .19, .23, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .55
    target = Vector((40, -27.5, 4))
    def aim(o): o.rotation_euler = (target-o.location).to_track_quat('-Z', 'Y').to_euler()
    for n, pos, energy, size in [('Key', (40,-10,110), 400, 95), ('Fill', (-60,-45,60), 220, 80), ('Rim', (100,-100,70), 300, 70)]:
        ld = bpy.data.lights.new(n, 'AREA'); ld.energy = energy; ld.shape = 'DISK'; ld.size = size
        o = bpy.data.objects.new(n, ld); scene.collection.objects.link(o); o.location = pos; aim(o)
    cd = bpy.data.cameras.new('Camera'); cam = bpy.data.objects.new('Camera', cd); scene.collection.objects.link(cam)
    cd.type = 'ORTHO'; cd.ortho_scale = 105; scene.camera = cam
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 32; scene.cycles.use_denoising = True
    scene.render.resolution_x = 1300; scene.render.resolution_y = 1000; scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    # Light power compensates for using explicit millimetre coordinates.
    for ld in bpy.data.lights: ld.energy *= 1000
    for name, pos in [('oblique', (119,-121,107)), ('top', (40,-27.5,170))]:
        cam.location = pos; aim(cam); scene.render.filepath = str(OUT/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    cam.location = (119,-121,107); aim(cam)
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_distance = 140
            area.spaces.active.region_3d.view_location = target
            area.spaces.active.clip_end = 2000
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MORI_power_P3_detail.blend'))
    (OUT/'blender_check.json').write_text(json.dumps({'blender': bpy.app.version_string,
        'mesh_objects': len(actual.objects), 'missing_position_markers': len(labels.objects),
        'scale_length': scene.unit_settings.scale_length, 'source_mesh_sha256': sha(OUT/'mesh.json'),
        'blend_sha256': sha(OUT/'MORI_power_P3_detail.blend'), 'renders': ['oblique.png', 'top.png']}, indent=2))
    print('BLEND_REFERENCE_COMPLETE', flush=True)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    {'inventory': inventory, 'mesh': mesh, 'blend': blend}[argv[0]]()
