"""Actual previous/current models with the same cameras; no geometry changes."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
from render import camera

out=c.ROOT/'renders/appearance';out.mkdir(parents=True,exist_ok=True)
views={'front':((0,650,145),(0,0,145),325),
       'side':((650,0,145),(0,0,145),325),
       'oblique':((380,500,325),(0,0,145),340)}
records=[]
for version in ['before','after']:
    model=c.PROJECT/c.P['structure']['comparison_baseline']['blend'] if version=='before' else c.ROOT/'mori_v1_2.blend'
    c.bpy.ops.wm.open_mainfile(filepath=str(model))
    c.bpy.context.window.scene=c.bpy.data.scenes['MORI_V1_Assembly'];c.load_collections();c.assembled()
    sc=c.bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    for collection in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:c.COLS[collection].hide_render=True
    for o in sc.objects:
        if o.get('role') in ['part','routing','display_content']:o.hide_render=False
    for view,args in views.items():
        c.bpy.data.objects[c.PREFIX+'Studio_Ground'].hide_render=view!='oblique'
        camera('appearance_'+version+'_'+view,*args)
        path=out/f'{version}_{view}.png';sc.render.filepath=str(path)
        c.bpy.ops.render.render(write_still=True)
        records.append({'version':version,'view':view,'file':str(path.relative_to(c.ROOT)),
                        'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
                        'camera':args,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
c.save_json(c.ROOT/'reports/appearance_comparison.json',{'before_revision':c.P['structure']['comparison_baseline']['revision'],
    'after_revision':c.P['revision'],'records':records,'method':'Actual immutable before .blend and delivered current .blend; same camera and scale. No scene saved or geometry changed.'})
print('APPEARANCE_COMPARISON_COMPLETE',flush=True)
