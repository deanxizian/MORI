"""Render actual MORI mesh geometry. --views preview | all | front,side,..."""
import sys, math, argparse, hashlib, struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def camera(name,loc,target,scale,res=None):
    n=PREFIX+'Camera_'+name
    o=bpy.data.objects.get(n)
    if not o:
        d=mark(bpy.data.cameras.new(n)); o=mark(bpy.data.objects.new(n,d)); COLS['CAMERAS_LIGHTS'].objects.link(o)
    o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type='ORTHO'; o.data.ortho_scale=scale; o.data.clip_start=.1; o.data.clip_end=5000
    bpy.context.scene.camera=o
    return o

def annotation_line(name,a,b,r=.23):
    d=Vector(b)-Vector(a)
    o=cyl(name,(Vector(a)+Vector(b))/2,r,d.length,'Z',12)
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); o.data.materials.append(MATS['annotation'])
    move_collection(o,'ANNOTATIONS'); o['role']='annotation'; return o

def annotation_text(name,text,loc,size=4):
    cu=mark(bpy.data.curves.new(PREFIX+name,'FONT')); cu.body=text; cu.size=size; cu.align_x='CENTER'
    cu.space_character=1.05; cu.extrude=.005
    o=mark(bpy.data.objects.new(PREFIX+name,cu)); COLS['ANNOTATIONS'].objects.link(o)
    o.location=loc; o.rotation_euler=(math.pi/2,0,0); o.data.materials.append(MATS['annotation']); o['role']='annotation'
    return o

def dimensions():
    for o in list(COLS['ANNOTATIONS'].objects): bpy.data.objects.remove(o,do_unlink=True)
    material('annotation',(.035,.1,.14),0,.6)
    y=-118; gc=P['ground_clearance_mm']; side=P['body_side_cut_x_mm']; inner=side+P['wheel_body_gap_mm']
    annotation_line('ground_datum',(-94,y,0),(94,y,0),.18)
    for z in [0,gc]:
        annotation_line('belly_extension',(0,y,z),(-27,y,z),.16)
        annotation_line('belly_tick',(-24,y,z-1),(-20,y,z+1),.2)
    annotation_line('belly_dimension',(-22,y,0),(-22,y,gc),.22)
    annotation_text('belly_readout',f'{gc:.2f} mm',(-36,y-1,8),4.2)
    # A closest-point witness on the actual planar side and tire annulus, at y=0,z=84.
    zz=D['wheel_z']+36.5
    annotation_line('gap_dimension',(side,y,zz),(inner,y,zz),.23)
    for x in [side,inner]: annotation_line('gap_tick',(x,y,zz-3),(x,y,zz+3),.2)
    annotation_line('gap_leader',((side+inner)/2,y,zz+3),(79,y,107),.18)
    annotation_text('gap_readout',f'{P["wheel_body_gap_mm"]:.2f} mm',(81,y-1,109),4.2)
    annotation_text('front_axis','FRONT -Y',(0,y-1,253),4)
    # Actual assembled bbox readout, not a copied reference dimension.
    ps=parts(); bb=[bounds(o) for o in ps]
    width=max(b[0][1] for b in bb)-min(b[0][0] for b in bb)
    height=max(b[2][1] for b in bb)-min(b[2][0] for b in bb)
    annotation_text('bbox_readout',f'{width:.2f} x {height:.2f} mm',(0,y-1,244),4)

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(); parser.add_argument('--views',default='all'); parser.add_argument('--resolution',type=int); parser.add_argument('--samples',type=int)
    a=parser.parse_args(args)
    bpy.context.window.scene=bpy.data.scenes['MORI_Assembly']; load_collections(); assembled()
    sc=bpy.context.scene
    sc.render.engine=P['render']['engine']; sc.cycles.samples=a.samples or P['render']['samples']; sc.cycles.use_denoising=True
    size=a.resolution or P['render']['resolution']; sc.render.resolution_x=size; sc.render.resolution_y=size
    sc.render.resolution_percentage=100
    views={
        'front':((0,-650,118),(0,0,118),270),
        'side':((650,0,118),(0,0,118),270),
        'rear':((0,650,118),(0,0,118),270),
        'top':((0,0,750),(0,0,0),190),
        'bottom':((0,0,-650),(0,0,110),190),
        '45_assembled':((400,-400,285),(0,0,116),282),
        'exploded':((360,-520,330),(0,0,145),430),
        'internal':((350,-470,330),(0,0,120),280),
        'engineering':((0,-700,122),(0,0,122),286),
        'engineering_gap_detail':((58,-700,88),(58,0,88),67)
    }
    wanted=['45_assembled','internal'] if a.views=='preview' else (list(views) if a.views=='all' else a.views.split(','))
    initial={o.name:o.hide_render for o in sc.objects}
    digest=hashlib.sha256()
    for o in sorted(parts(),key=lambda o:o.name):
        digest.update(o.name.encode())
        for v in o.data.vertices: digest.update(struct.pack('<3f',*v.co))
        for f in o.data.polygons: digest.update(str(tuple(f.vertices)).encode())
    geometry_digest=digest.hexdigest(); render_records=[]
    for name in wanted:
        for o in sc.objects:
            if o.name in initial: o.hide_render=initial[o.name]
        assembled(); COLS['ANNOTATIONS'].hide_render=True
        ground=bpy.data.objects.get(PREFIX+'Studio_Ground'); ground.hide_render=name not in ['45_assembled']
        if name=='exploded': sc.frame_set(80)
        if name=='internal':
            for key in ['Body_Upper_Shell','Body_Lower_Shell','Head_Front_Shell','Head_Rear_Shell']:
                bpy.data.objects[PREFIX+key].hide_render=True
        if name.startswith('engineering'):
            dimensions(); COLS['ANNOTATIONS'].hide_render=False
            if name.endswith('detail'):
                for o in COLS['ANNOTATIONS'].objects:
                    if any(t in o.name for t in ['belly','front_axis','bbox_readout','ground_datum']): o.hide_render=True
        camera(name,*views[name]); bpy.context.view_layer.update()
        sc.render.filepath=str(ROOT/'renders'/f'{name}.png')
        print('MORI RENDER '+name,flush=True); bpy.ops.render.render(write_still=True)
        render_records.append(dict(view=name,frame=sc.frame_current,geometry_digest=geometry_digest,camera=list(sc.camera.location),ortho_scale_mm=sc.camera.data.ortho_scale,
                                   hidden_meshes=[o.name.removeprefix(PREFIX) for o in parts() if o.hide_render]))
    # Retain all generated cameras/dimensions, but save a clean assembled model as the default.
    for o in sc.objects:
        if o.name in initial: o.hide_render=initial[o.name]
    COLS['ANNOTATIONS'].hide_render=True; assembled(); camera('45_assembled',*views['45_assembled'])
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/MORI_assembly.blend'))
    previous=ROOT/'reports/render_run.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        if old.get('params_sha256')==sc.get('params_sha256'):
            render_records=[r for r in old.get('records',[]) if r['view'] not in wanted and r.get('geometry_digest')==geometry_digest]+render_records
    save_json(previous,dict(blender=bpy.app.version_string,views=[r['view'] for r in render_records],records=render_records,params_sha256=sc.get('params_sha256'),resolution=size,samples=sc.cycles.samples,source='models/MORI_assembly.blend; identical geometry, visibility/frame/camera changes only'))

if __name__=='__main__': main()
