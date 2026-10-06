"""Render known outlet directions; never use the illustrative slots as datums."""
from pathlib import Path
import json,sys,hashlib
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex/connector_faces/correction'
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import bpy,np,PREFIX,load_collections
from render import camera
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
scene=bpy.context.scene
load_collections()
before=bpy.data.objects[PREFIX+'CAM_Mainboard']
after=bpy.data.objects['MORI_CAM_FPC_CORRECTED__CAM_Mainboard']
scene.render.resolution_x=1200;scene.render.resolution_y=900
views=[('camera_entry',[-.06,-24.8,226.76],[5,-24,15],21),
       ('display_entry',[-15.56,-21.2,234.81],[-22,18,10],18)]
images=[]
for state,board in [('before',before),('corrected',after)]:
    for o in [before,after]:o.hide_render=True;o.hide_set(True)
    board.hide_render=False;board.hide_set(False)
    for label,target,offset,scale in views:
        target=np.asarray(target);camera('MORI_FPC_CLOSE_'+label,target+np.asarray(offset),target,scale)
        file=state+'_'+label+'.png';scene.render.filepath=str(OUT/file);bpy.ops.render.render(write_still=True)
        images.append(dict(file=file,sha256=sha(OUT/file)))
report=dict(status='PASS',scope='Outlet-facing renders only; no new geometry or fit qualification',images=images,
    main_changed=False,script_sha256=sha(Path(__file__)),
    inputs={str((OUT/'MORI_M1_49_CAM_corrected_entries.blend').relative_to(ROOT)):sha(OUT/'MORI_M1_49_CAM_corrected_entries.blend')})
(OUT/'closeup_review.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAM_FPC_ENTRY_VIEWS_DONE',flush=True)
