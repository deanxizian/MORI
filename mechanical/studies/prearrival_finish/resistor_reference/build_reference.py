"""Independent AC05 documented maximum-envelope reference. No robot placement."""
from pathlib import Path
import bpy, math, hashlib, json, datetime
from mathutils import Vector
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = ROOT / 'hardware/v1_2/prearrival_20261002/sources/vishay_ac.pdf'
main = ROOT / 'mechanical/mori_v1_2.blend'
original = sha(main)
assert original == 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
# A new independent scene. Never open or save the main assembly.
scene = bpy.data.scenes.new('AC05_reference_ONLY_NOT_INSTALLED')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .001
scene.unit_settings.length_unit = 'MILLIMETERS'
scene['scope'] = 'Unselected brake resistor candidates; documented maximum body envelopes only'
scene['main_assembly_modified'] = False
scene['manufacturing_release'] = False
scene['source_pdf_sha256'] = sha(source)
scene['source_page'] = 10
scene['full_installed_envelope'] = 'BLOCKED: lead forming, insulation, mount, heat clearance and working point unselected'
scene['B_datum_note'] = 'B63+/-1 is the drawing reference between tape/lead datum lines. Do not infer final trimmed lead length or mounting pitch.'

body_mat = bpy.data.materials.new('UNSELECTED_AMBER')
body_mat.diffuse_color = (.76,.40,.12,1)
guard_mat = bpy.data.materials.new('ASSUMED_end_transition_guard')
guard_mat.diffuse_color = (.95,.66,.26,1)
rows=[]
for i, (identifier, mpn, resistance) in enumerate([
    ('WHEEL_BRAKE_CANDIDATE','AC05000005608JAC00',5.6),
    ('HEAD_BRAKE_CANDIDATE','AC05000001009JAC00',10.)]):
    collection=bpy.data.collections.new(identifier)
    scene.collection.children.link(collection)
    def move(obj):
        for c in list(obj.users_collection): c.objects.unlink(obj)
        collection.objects.link(obj)
        obj['part_class']='PLACEHOLDER'
        obj['evidence']='ASSUMED'
        obj['vendor']='Vishay Draloric'
        obj['candidate_mpn']=mpn
        obj['adopted']=False
        obj['source_pdf']=str(source.relative_to(ROOT))
        obj['source_sha256']=sha(source)
        obj['units']='mm'
    y=i*18
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=3.75,depth=18,location=(0,y,0),rotation=(0,math.pi/2,0))
    body=bpy.context.object;body.name=identifier+'_L18_D7p5_MAX_ENVELOPE'
    move(body);body.data.materials.append(body_mat)
    body['documented_fields']='Lmax18mm; Dmax7.5mm; nominal mass1.90g'
    body['geometry_note']='Bounding cylinder; actual end radii, waist and surface profile undimensioned. Not original vendor CAD.'
    bpy.context.view_layer.update()
    corners=[body.matrix_world @ Vector(v) for v in body.bound_box]
    dims=[max(v[axis] for v in corners)-min(v[axis] for v in corners) for axis in range(3)]
    assert max(abs(a-b) for a,b in zip(dims,[18.,7.5,7.5]))<1e-5,dims
    for side in [-1,1]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=3.75,depth=3,location=(side*10.5,y,0),rotation=(0,math.pi/2,0))
        guard=bpy.context.object;guard.name=identifier+('_minusX' if side<0 else '_plusX')+'_TRANSITION_GUARD_NOT_SHAPE'
        move(guard);guard.data.materials.append(guard_mat)
        guard.display_type='WIRE';guard.hide_render=True
        guard['documented_fields']='Axial extension xmax3mm each end'
        guard['assumed_fields']='Full body diameter used as conservative local planning guard; actual transition diameter/profile unknown'
    rows.append(dict(id=identifier,mpn=mpn,resistance_ohm=resistance,
        tolerance_percent=5,part_class='PLACEHOLDER',aggregate_evidence='ASSUMED',
        vendor_documented_fields=dict(body_length_max_mm=18,body_diameter_max_mm=7.5,
            lead_diameter_nominal_mm=.8,lead_diameter_tolerance_mm=.03,
            end_transition_axial_max_mm=3,B_datum_mm=63,B_datum_tolerance_mm=1,nominal_mass_g=1.9),
        body_representation='Bounding cylinder, not actual waist or rounded profile',
        end_transition_representation='Wire-display guard, radius conservatively allocated equal to body; not physical shape',
        lead_representation='Not modeled beyond transition: final lead forming/trim and support unknown',
        demonstration_translation_mm=[0,y,0],translation_is_robot_installation=False,
        complete_installed_envelope='BLOCKED',thermal_spacing_mm=None,mount_sku=None))

scene.world=bpy.data.worlds.new('Reference_World')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_location=(0,9,0)
            area.spaces.active.region_3d.view_distance=65
            area.spaces.active.shading.color_type='MATERIAL'
            area.spaces.active.clip_end=1000
scene['object_count']=len(scene.objects)
assert len(scene.objects)==6
out=HERE/'AC05_MAX_ENVELOPE_NOT_INSTALLED.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(out),check_existing=False)
assert sha(main)==original
report=dict(status='PASS',scope='Dimensional reference build only; not full installed fit or thermal qualification',
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),blender=bpy.app.version_string,
    source_pdf=str(source.relative_to(ROOT)),source_pdf_sha256=sha(source),
    source_url='https://www.vishay.com/docs/28730/ac_ac-at_ac-ni.pdf',source_revision='05-Dec-2024',source_page=10,
    source_hardware_handoff='hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json',
    body_objects=2,transition_guard_objects=4,units='mm',parts=rows,
    main_sha256=original,main_geometry_changed=False,purchased=False,manufacturing_release=False,
    output_blend=str(out.relative_to(ROOT)),output_blend_sha256=sha(out),
    script_sha256=sha(Path(__file__)),
    limits=['The same AC05 body envelope is shared by the two named electrical candidates.',
        'Wire diameter is documented but untrimmed straight ends, mounting pitch and final bend form are not selected.',
        'B63+/-1 must not be relabeled as final cut wire length or installed axial size.',
        'No thermal exclusion distance is invented from electrical wattage or nominal body size.',
        'Nominal1.90g per part is catalogue data, not physical weighing or computed envelope mass.',
        'Coordinates only separate the two candidates for inspection; neither is placed inside MORI.'])
(HERE/'reference.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('AC05_REFERENCE_PASS',out,'main unchanged')
