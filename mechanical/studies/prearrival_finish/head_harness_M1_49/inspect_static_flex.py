"""Current-main endpoint, section and motion evidence for static head flexes.

No connector exit is inferred from a bounding box. No main model is saved.
"""
from pathlib import Path
import json, sys, time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / 'remaining_routes/static_flex'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'mechanical/scripts'))
from harness_context import Context, np, sha
from common import bpy, COLS, PREFIX, P, D
from validate import rigidtr
from render import camera

started = time.time()
ctx = Context()
assert ctx.source_hash == '89cb07f571367bf87b627c771998d0cc0c28b873be575afdb4002c9bcf5b499f'
refs = {'CAM_Mainboard': {'DISPLAY_FPC_18', 'CAMERA_FPC_24'},
        'Display_PCB': {'Connector_108'}}
ports = []
for name, selected in refs.items():
    o = ctx.ss[name].o
    for row in json.loads(o['component_reference_index']):
        if row['reference'] not in selected:
            continue
        a, b = row['vertices']
        v = np.array([o.matrix_world @ o.data.vertices[i].co for i in range(a, b)])
        ports.append(dict(object=name, reference=row['reference'], group=o.get('group'),
            evidence=row['evidence'], bounds_mm=[v.min(0).tolist(), v.max(0).tolist()],
            wire_exit_mm=None, contact_face=None, pin1_view=None,
            limitation='AABB locates a connector, not an insertion datum or cable exit.'))

names = ['Head_Front','Head_Rear','Head_Lower_Guard','Pitch_Cradle','Pitch_Yoke',
         'Display_Frame','CAM_Mainboard','Camera_PCB','Camera_Lens','Display_PCB',
         'Yaw_Servo','Pitch_Servo','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link']
absent_historical_names=[name for name in names if name not in ctx.ss]
names=[name for name in names if name in ctx.ss]
sections = []
for z in [225., 235., 245., 255., 265., 275.]:
    layers = {}
    for name in names:
        polys = ctx.ss[name].m.slice(z).to_polygons()
        if len(polys):
            layers[name] = [p.tolist() for p in polys]
    sections.append(dict(z_mm=z, axes=['X_right','Y_forward'], layers=layers))

positions = {f"{p['object']}/{p['reference']}": np.mean(p['bounds_mm'],axis=0) for p in ports}
positions['Camera_PCB/nominal_center']=(ctx.ss['Camera_PCB'].lo+ctx.ss['Camera_PCB'].hi)/2
poses = [(y,p) for y in range(-60,61,10) for p in range(-20,26,5)]
pairs=[('CAM_Mainboard/DISPLAY_FPC_18','Display_PCB/Connector_108'),
       ('CAM_Mainboard/CAMERA_FPC_24','Camera_PCB/nominal_center')]
checks=[]
for a,b in pairs:
    errors=[]
    original=float(np.linalg.norm(positions[b]-positions[a]))
    for y,p in poses:
        t=np.array(rigidtr(y,p)); aa=t[:3,:3]@positions[a]+t[:3,3];bb=t[:3,:3]@positions[b]+t[:3,3]
        errors.append(abs(float(np.linalg.norm(bb-aa))-original))
    checks.append(dict(endpoints=[a,b],same_rigid_group='pitch',samples=len(poses),
        nominal_center_distance_mm=original,max_distance_error_mm=max(errors),
        status='PASS' if max(errors)<1e-4 else 'FAIL',
        scope='Both endpoints share pitch transform. Routing remains BLOCKED.'))

scene=bpy.context.scene
for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
for name in names:
    o=ctx.ss[name].o
    if name not in ['Head_Front','Head_Rear','Head_Lower_Guard']:
        o.hide_render=False;o.color=(.63,.69,.72,1)
ctx.ss['CAM_Mainboard'].o.color=(.12,.42,.33,1)
ctx.ss['Display_PCB'].o.color=(.18,.43,.42,1)
ctx.ss['Camera_PCB'].o.color=(.73,.45,.12,1)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=False
scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD'
scene.world.color=(.91,.93,.95);scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
images=[]
for name,eye,target,scale in [('head_above',(-125,130,370),(0,5,244),118),
                             ('head_side',(-160,25,261),(0,5,245),118)]:
    camera('STATIC_FLEX_REVIEW_'+name,eye,target,scale)
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged()
report=dict(status='PASS',scope='Current main port locations, same-body motion and review sections only',
    revision=P['revision'],sources=ctx.sources,ports=ports,rigid_group_checks=checks,
    sections=sections,images=images,absent_historical_names=absent_historical_names,
    main_changed=False,full_flex_fit='BLOCKED',physical_validation='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'endpoints.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('STATIC_FLEX_ENDPOINTS',json.dumps({'status':report['status'],'checks':checks}),flush=True)
