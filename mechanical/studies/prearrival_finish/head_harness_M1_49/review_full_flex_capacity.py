"""Self-clearance, shell paths and editable views of the short-lead allocation."""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes'; FLEX=BASE/'static_flex'; FULL=FLEX/'full_route'; OUT=FULL/'review'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold,bpy,COLS
from render import camera
ctx=Context(); started=time.time(); label='L2_W10.5'; source=FULL/'short_lead/review.json'
previous=json.loads(source.read_text()); row=next(r for r in previous['rows'] if r['id']==label); assert row['status']=='PASS'
path=FULL/'short_lead'/(label+'.npz'); geom=np.load(path); params=row['parameters']
verts=geom['vertices_mm']; triangles=geom['triangles']; m=manifold.Manifold(manifold.Mesh64(verts,triangles))
error=params['polygonal_chord_error_bound_mm']; shell_rows=[]
for name,sign in [('Head_Front',1),('Head_Rear',-1)]:
    failures=[]; nearest=1.
    for d in np.linspace(0,68,273):
        shell=ctx.ss[name].m.translate([0,sign*float(d),0]); overlap=float((m^shell).volume()); gap=float(m.min_gap(shell,1.))
        nearest=min(nearest,gap)
        if overlap>1e-7 or gap<.3+error: failures.append(dict(translation_y_mm=sign*float(d),overlap_mm3=overlap,gap_mm=gap))
    shell_rows.append(dict(part=name,status='FAIL' if failures else 'PASS',samples=273,translation_y_mm=[0,68*sign],
        minimum_capped_gap_mm=nearest,gap_search_cap_mm=1.,failures=failures))
    print('FULL_FFC_SHELL',name,shell_rows[-1]['status'],flush=True)

def closed_segment(v):
    f=[]
    for i in range(len(v)//4-1):
        for j in range(4):
            a=4*i+j; b=4*i+(j+1)%4; f.extend([[a,b,b+4],[a,b+4,a+4]])
    f.extend([[0,2,1],[0,3,2]]); a=len(v)-4; f.extend([[a,a+1,a+2],[a,a+2,a+3]])
    f=np.asarray(f,dtype=np.uint64)
    if np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()<0: f=f[:,::-1].copy()
    result=manifold.Manifold(manifold.Mesh64(v,f)); assert result.status()==manifold.Error.NoError
    return result
segments=[]; cursor=0
for piece in params['pieces']:
    count=max(2 if piece['kind']=='arc' else 1,math.ceil(piece['length_mm']/.2))
    segments.append(closed_segment(verts[cursor*4:(cursor+count+1)*4])); cursor+=count
assert cursor+1==len(geom['points_mm'])
self_rows=[]
for i in range(len(segments)):
    for j in range(i+2,len(segments)):
        overlap=float((segments[i]^segments[j]).volume()); gap=float(segments[i].min_gap(segments[j],1.))
        self_rows.append(dict(piece_pair=[i,j],status='FAIL' if overlap>1e-7 or gap<.3+2*error else 'PASS',
            overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.))
camera_path=FLEX/'camera_corridor/terminal/T2_W6.6.npz'; cam=np.load(camera_path)
cm=manifold.Manifold(manifold.Mesh64(cam['vertices_mm'],cam['triangles']))
pair=dict(overlap_mm3=float((m^cm).volume()),gap_mm=float(m.min_gap(cm,1.)),gap_search_cap_mm=1.)
pair['status']='PASS' if pair['overlap_mm3']<1e-7 and pair['gap_mm']>=.3+error else 'FAIL'

scene=bpy.context.scene; tag='MORI_FULL_FLEX_CAPACITY__'; clones=[]
def mesh(name,v,f,color,category='PLACEHOLDER',evidence='ASSUMED'):
    me=bpy.data.meshes.new(tag+name); me.from_pydata(np.asarray(v).tolist(),[],np.asarray(f).tolist()); me.update()
    o=bpy.data.objects.new(tag+name,me); scene.collection.objects.link(o); o.color=color
    o['robot_part']=False; o['category']=category; o['data_status']=evidence
    o['scope']='Independent capacity review; not main or a fabrication part.'; clones.append(o); return o
for name,s in ctx.ss.items():
    if s.group not in ['yaw','pitch'] or name in ['Head_Front','Head_Rear']: continue
    color=(.56,.64,.68,1) if name not in ['CAM_Mainboard','Display_PCB'] else (.13,.36,.28,1)
    mesh(name,s.v,s.f,color,s.o.get('category','PLACEHOLDER'),s.o.get('data_status','ASSUMED'))
mesh('LCD_194mm_free_span_ASSUMED',verts,triangles,(.96,.54,.08,1))
mesh('CAMERA_FPC_corridor_BLOCKED',cam['vertices_mm'],cam['triangles'],(.65,.28,.8,1))
curves_path=BASE/'cam_side_fans/c6_join/candidate_curves.npz'; curves=np.load(curves_path)
for i in range(1,5):
    points=curves[f'CAM_{i}_y0_p0']; data=bpy.data.curves.new(tag+f'CAMwire{i}','CURVE'); data.dimensions='3D'
    data.bevel_depth=.3302; data.bevel_resolution=3; spline=data.splines.new('POLY'); spline.points.add(len(points)-1)
    for q,p in zip(spline.points,points): q.co=(*p,1.)
    obj=bpy.data.objects.new(tag+f'CAM_wire_candidate_{i}',data); scene.collection.objects.link(obj); obj.color=(.1,.52,.85,1)
    obj['robot_part']=False; obj['category']='PLACEHOLDER'; obj['data_status']='ASSUMED'; clones.append(obj)
for col in COLS.values(): col.hide_render=False; col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']: o.hide_render=True; o.hide_set(True)
for o in clones: o.hide_render=False; o.hide_set(False)
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.color_type='OBJECT'; scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=False; scene.display.shading.show_shadows=True; scene.display.shading.background_type='WORLD'
scene.world.color=(.91,.93,.95); scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; images=[]
for name,eye,target,scale in [('overview',(-125,135,345),(0,9,235),112),('rear_return',(-105,-100,300),(-15,-15,234),57),('top',(0,6,420),(0,6,235),113)]:
    camera(tag+name,eye,target,scale); scene.render.filepath=str(OUT/(name+'.png')); bpy.ops.render.render(write_still=True)
    images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged()
blend=OUT/'MORI_M1_49_full_FFC_capacity.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend)); ctx.assert_unchanged()
report=dict(status='PASS' if all(x['status']=='PASS' for x in shell_rows+self_rows+[pair]) else 'FAIL',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,path,camera_path,curves_path]},candidate=label,
    parameters=params,shell_paths=shell_rows,self_clearance=self_rows,camera_corridor_pair=pair,
    images=images,blend=blend.name,blend_sha256=sha(blend),main_changed=False,adopted=False,
    scope='Nonadjacent ribbon pieces, shell translation versus free span, and comparison renders only.',
    limitations=['Adjacent segments intentionally meet and are excluded from self-clearance.',
        'Unknown connector/stiffener lengths and material limits remain; cable anchoring and installation not established.',
        'Purple camera corridor has marginal frame clearance and unconfirmed FPC dimensions; not a qualified cable.',
        'Blue CAM wire paths are unadopted C6-dependent candidates.'],
    full_flex_fit='BLOCKED',full_harness='BLOCKED',physical_validation='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FULL_FLEX_CAPACITY_REVIEW_DONE',report['status'],flush=True)
