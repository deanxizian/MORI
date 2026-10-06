"""Render the verified higher-entry lower proposal without changing main CAD."""
from pathlib import Path
import sys, json
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
variant = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('--route-set=')), 'nine_higher')
assert variant in ['nine_higher', 'nine_higher_directed', 'nine_higher_stagger', 'nine_higher_lift']
OUT = HERE / 'remaining_routes' / variant / 'combined'
sys.path.insert(0, str(PROJECT/'mechanical/scripts'))
from harness_context import Context, np, sha
from common import *
from render import camera

ctx = Context()
report_file = OUT/'lower_nine_screen.json'
report = json.loads(report_file.read_text())
assert report['status'] == 'PASS'
for name, digest in {**report['sources'], **report['inputs']}.items():
    assert sha(PROJECT/name) == digest, name
data_file = OUT/'lower_nine_candidates.npz'
data = np.load(data_file)
assert sha(data_file) == report['curve_sha256']
lane_file = HERE/'remaining_routes/higher_entry/neck_candidates.npz'
lane = np.load(lane_file)
lane_report = json.loads((lane_file.parent/'neck_screen.json').read_text())
assert sha(lane_file) == lane_report['curve_sha256']
full_file = OUT/'cam_rejoined/cam_joined_screen.json'
full_data = None
inputs = {str(report_file.relative_to(PROJECT)): sha(report_file),
          str(lane_file.relative_to(PROJECT)): sha(lane_file)}
if full_file.exists():
    full_report = json.loads(full_file.read_text())
    if full_report['status'] == 'PASS':
        for name, digest in {**full_report['sources'], **full_report['inputs']}.items():
            assert sha(PROJECT/name) == digest, name
        file = full_file.parent/'cam_joined_candidates.npz'
        assert sha(file) == full_report['curve_sha256']
        full_data = np.load(file)
        inputs.update({str(full_file.relative_to(PROJECT)): sha(full_file),
                       str(file.relative_to(PROJECT)): sha(file)})

tag = 'MORI_NINE_HIGHER_149__'
for ob in list(bpy.data.objects):
    if ob.name.startswith(tag):
        bpy.data.objects.remove(ob, do_unlink=True)
wires = []
def wire(label, points, radius, color, role):
    cu = bpy.data.curves.new(tag+label, 'CURVE')
    cu.dimensions = '3D'; cu.bevel_depth = radius
    cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for vertex, point in zip(sp.points, points):
        vertex.co = (*point, 1)
    ob = bpy.data.objects.new(tag+label, cu)
    bpy.context.scene.collection.objects.link(ob); ob.color = color
    ob['category'] = 'PLACEHOLDER'; ob['data_status'] = 'ASSUMED'
    ob['robot_part'] = False; ob['full_harness'] = 'BLOCKED'
    ob['scope'] = role; ob['not_supplier_cut_length'] = True
    wires.append(ob)

palette = {
    'P_J9_1': (.06, .43, .58, 1), 'P_J9_2': (.04, .63, .52, 1),
    'P_J9_3': (.22, .66, .79, 1), 'P_J18_1': (.45, .22, .69, 1),
    'P_J18_2': (.69, .34, .71, 1), 'CAM_1': (.81, .22, .18, 1),
    'CAM_2': (.86, .48, .06, 1), 'CAM_3': (.64, .37, .15, 1),
    'CAM_4': (.8, .68, .21, 1)}
for row in report['selected']:
    name = row['endpoint']; points = data[name+'_y0']
    role = 'Verified finite lower geometry; upper endpoints and anchors absent'
    if full_data is not None and name.startswith('CAM_'):
        points = full_data[f'pin{name[-1]}_y0_p0']
        role = 'CAM continuous estimate, jointly checked with five lower wires; crimp geometry and anchors remain unknown'
    wire(name, points, row['OD_mm']/2, palette[name], role)
spare = sorted(set(range(11)) - {r['slot'] for r in report['selected']})
for slot in spare:
    wire('SPK_local_'+str(slot), lane[f'z{report["z0_mm"]}_wire{slot}_y0'],
         .5842, (.95, .62, .16, 1), 'Local capacity reservation only; neither speaker endpoint connected')

for collection in COLS.values():
    collection.hide_viewport = False; collection.hide_render = False
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
shade = scene.display.shading
shade.color_type = 'OBJECT'; shade.light = 'STUDIO'; shade.show_cavity = True
shade.cavity_type = 'BOTH'; shade.show_shadows = True
shade.show_specular_highlight = False; shade.background_type = 'WORLD'
scene.world.color = (.81, .85, .87); scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = False
scene.render.resolution_x = 1400; scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
records = []
def view(name, keep, eye, target, scale):
    for ob in scene.objects:
        if ob.type in ['MESH', 'CURVE', 'FONT']: ob.hide_render = True
    for part, solid in ctx.ss.items():
        solid.o.hide_render = part not in keep
        if solid.o.get('category') == 'PRINTABLE': solid.o.color = (.54, .62, .64, 1)
    for ob in wires: ob.hide_render = False; ob.hide_set(False)
    camera_ob = camera('Nine149_'+name, eye, target, scale)
    camera_ob.data.clip_start = .1
    scene.render.filepath = str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    records.append(dict(file=name+'.png', sha256=sha(OUT/(name+'.png')),
                        visible_native_parts=sorted(keep)))

boards = {'Power_Module', 'MCU_Carrier', 'MCU_Motion', 'Load_Frame',
          'Yaw_Bearing', 'CAM_Mainboard', 'Yaw_Servo', 'Pitch_Servo'}
view('nine_overview', boards|{'Yaw_Base','Yaw_Anti_Lift_Keeper','Pitch_Yoke'},
     (190,-270,270), (0,-4,175), 166)
view('nine_exposed', {'Power_Module','MCU_Carrier','Yaw_Bearing','CAM_Mainboard'},
     (-170,-220,255), (0,-12,169), 148)
view('body_routes', {'Power_Module','MCU_Carrier','Yaw_Bearing'},
     (-160,-220,285), (0,-14,140), 100)
bpy.context.view_layer.update(); ctx.assert_unchanged()
destination = OUT/'MORI_M1_49_nine_wire_candidate.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
ctx.assert_unchanged()
manifest = dict(status='PASS', scope='Verified partial wire proposal preview; full harness incomplete',
                source_blend_sha256=ctx.source_hash, inputs=inputs,
                images=records, blend_sha256=sha(destination), main_changed=False,
                continuous_CAM_included=full_data is not None, full_harness='BLOCKED',
                script_sha256=sha(Path(__file__)))
(OUT/'render_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
