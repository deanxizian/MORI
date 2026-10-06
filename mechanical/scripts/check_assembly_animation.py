"""Read-back checks of the editable animation and the actual encoded video."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from assembly_animation import ANIM_OWNER,AP,OUT,SCENE_NAME,same_geometry,STAGES
source_scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=source_scene
bpy.context.view_layer.update()
source_matrices={o.name:o.matrix_world.copy() for o in source_scene.objects}
scene=bpy.data.scenes[SCENE_NAME];bpy.context.window.scene=scene
report=json.loads((OUT/'manifest.json').read_text())
actors={o.name.removeprefix(AP):o for o in scene.objects if o.get('presentation_actor')}
scene.frame_set(scene.frame_end);bpy.context.view_layer.update()
errors={}
for name,o in actors.items():
    src=bpy.data.objects[o['source_object']]
    assert same_geometry(o.data,src.data)
    errors[name]=float(np.max(np.abs(np.asarray(o.matrix_world)-np.asarray(source_matrices[src.name]))))
    assert not o.hide_render and not o.hide_viewport
assert set(actors)==set(report['part_stages'])
assert max(errors.values())<.0001
assert len(scene.timeline_markers)==report['stage_count']==len(STAGES)
assert all(o.animation_data and o.animation_data.action for o in actors.values())
assert all(o.get('export_candidate') is False for o in actors.values())
assert all(o.get('assembly_step')==report['part_stages'][name] for name,o in actors.items())
source=Path(report['source_blend']);assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_blend_sha256']
native=[]
for s in report['stages']:
    scene.frame_set(s['end']);bpy.context.view_layer.update()
    native.append({'step':s['index'],'frame':s['end'],'camera':scene.camera.name,'visible_actors':sum(not o.hide_render for o in actors.values())})
    assert scene.camera.name==AP+f'Camera_{s.get("source_step",s["index"]):02d}'
video=OUT/'MORI_assembly.mp4'
if report.get('body_sequence_kind')=='front_rear':
    from validate import Solid
    base={o.name.removeprefix(PREFIX):Solid(o) for o in source_scene.objects if o.type=='MESH' and o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
    inverse={n:source_matrices[o['source_object']].inverted() for n,o in actors.items()}
    def at(n):
        tr=np.asarray(actors[n].matrix_world@inverse[n])[:3,:]
        return base[n].m.transform(tr)
    def overlaps(m,others):
        bb=np.array(m.bounding_box());found=[]
        for n,t in others.items():
            obb=np.array(t.bounding_box())
            if np.any(bb[3:]<obb[:3]) or np.any(obb[3:]<bb[:3]):continue
            vol=max(0,(m^t).volume())
            if vol>.05:found.append(dict(fixed=n,overlap_mm3=vol))
        return found
    from check_body_split_animation import run as check_split
    report['body_sequence_readback']=check_split(scene,actors,report,base,at,overlaps)
elif report.get('body_sequence_evidence'):
    from validate import Solid
    base={o.name.removeprefix(PREFIX):Solid(o) for o in source_scene.objects if o.type=='MESH' and o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
    evidence=json.loads((ROOT/'reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']
    upper=set(evidence['moving']);bridge={'Yaw_Base','Yaw_Bearing','Yaw_Base_-1_Nut','Yaw_Base_1_Nut'}|{n for n in actors if n.startswith('Yaw_Keeper_Insert_')}
    bolts={'Yaw_Base_-1_Screw','Yaw_Base_1_Screw'}
    inverse={n:source_matrices[o['source_object']].inverted() for n,o in actors.items()}
    def at(n):
        tr=np.asarray(actors[n].matrix_world@inverse[n])[:3,:]
        return base[n].m.transform(tr)
    def overlaps(m,others):
        bb=np.array(m.bounding_box());found=[]
        for n,t in others.items():
            obb=np.array(t.bounding_box())
            if np.any(bb[3:]<obb[:3]) or np.any(obb[3:]<bb[:3]):continue
            vol=max(0,(m^t).volume())
            if vol>.05:found.append(dict(fixed=n,overlap_mm3=vol))
        return found
    rows=[];hits=[]
    for source_step in [19,8,20]:
        stage=next(s for s in report['stages'] if s.get('source_step')==source_step)
        count=0;local=[]
        for frame in np.arange(stage['start'],stage['end']+.01,.5):
            scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update();count+=1
            visible={n for n in base if n in actors and not actors[n].hide_render}
            assert upper|bridge <= visible
            fixed={n:at(n) for n in visible-upper-bridge-bolts if not n.startswith('Frame_Screw_')}
            uu={n:at(n) for n in upper};bb={n:at(n) for n in bridge}
            for n,m in uu.items():local.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(m,fixed|bb))
            for n,m in bb.items():local.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(m,fixed))
            for n in bolts & visible:local.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(at(n),fixed|uu|bb))
            if len(local)>20:break
        rows.append(dict(stage=stage['index'],source_step=source_step,samples=count,status='FAIL' if local else 'PASS',hits=local))
        hits.extend(local);print('BODY_SEQUENCE_READBACK',stage['index'],count,local[:2],flush=True)
    # The shell must stay raised until both bridge screws are home.
    stage=next(s for s in report['stages'] if s.get('source_step')==8)
    scene.frame_set(stage['end']);bpy.context.view_layer.update()
    assert abs(bpy.data.objects[AP+'Upper_Shell'].rotation_euler.x-math.radians(15))<1e-5
    assert max(abs(x) for row in bpy.data.objects[AP+'Fixed_Bridge'].matrix_world-Matrix.Identity(4) for x in row)<1e-5
    assert all(np.max(np.abs(np.asarray(actors[n].matrix_world)-np.asarray(source_matrices[actors[n]['source_object']])))<.0001 for n in bolts)
    # Also replay the corrected pitch-servo right-above→down→left path in
    # yoke coordinates. It must be installed while the yoke stays on the bench.
    stage=next(s for s in report['stages'] if s.get('source_step')==11)
    servo_hits=[];servo_count=0
    for frame in np.arange(stage['start'],stage['end']+.01,.5):
        scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update()
        assert abs(bpy.data.objects[AP+'Yaw_Group'].location.z-64)<1e-4
        fixture={'Pitch_Yoke':at('Pitch_Yoke')}
        if not actors['Pitch_Servo'].hide_render:
            servo_count+=1
            for n in ['Pitch_Servo','Pitch_Output']:servo_hits.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(at(n),fixture))
        if not actors['Yaw_Servo'].hide_render:
            fixture.update({n:at(n) for n in ['Pitch_Servo','Pitch_Output']})
            for n in ['Yaw_Servo','Yaw_Output']:servo_hits.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(at(n),fixture))
    shell=dict(status='FAIL' if hits or servo_hits else 'PASS',animation_revision=report['animation_revision'],body_stages=rows,samples=sum(r['samples'] for r in rows),hits=hits,servo_bench=dict(samples=servo_count,status='FAIL' if servo_hits else 'PASS',hits=servo_hits),method='Read saved animation matrices each half frame; independent upper shell vs level bridge and all visible nominal chassis parts; bridge screws included. No swept-volume/hand/fixture/harness qualification.',source_evidence=report['body_sequence_evidence'])
    save_json(OUT/'upper_shell_path_validation.json',shell);assert not hits and not servo_hits,(hits[:3],servo_hits[:3])
    report['body_sequence_readback']={'status':shell['status'],'samples':shell['samples'],'report':'upper_shell_path_validation.json'}
if P.get('head_axial_retention',{}).get('enabled'):
    # Check the actual saved presentation matrices for side-loading, paired
    # descent and the60deg access pose. No source parts are reshaped for film.
    retention_rows=[];retention_hits=[]
    paired={n for n,o in actors.items() if o.parent and o.parent.name in [AP+'Yaw_Group',AP+'Yaw_Turn']}
    for source_step in [10,21,22]:
        st=next(s for s in report['stages'] if s.get('source_step')==source_step);local=[];count=0
        for fr in np.arange(st['start'],st['end']+.01,.5):
            scene.frame_set(int(fr),subframe=float(fr%1));bpy.context.view_layer.update();count+=1
            visible={n for n in base if n in actors and not actors[n].hide_render}
            if source_step==10:
                if 'Yaw_Anti_Lift_Keeper' not in visible:continue
                movers={'Yaw_Anti_Lift_Keeper'};fixed=visible-movers
            elif source_step==21:
                movers={'Yaw_Anti_Lift_Keeper','Pitch_Yoke'};fixed=visible-paired-{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
            else:
                movers={n for n in visible if actors[n].parent and actors[n].parent.name==AP+'Yaw_Turn'}|({'Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'}&visible)
                assert 'Pitch_Output' in movers
                fixed=visible-movers
                # Installed inserts travel only with the bridge and never turn.
                assert abs(actors['Yaw_Anti_Lift_Keeper'].matrix_world.to_euler().z)<1e-5
                if st['start']+32<=fr<=st['start']+104:
                    assert abs(bpy.data.objects[AP+'Yaw_Turn'].rotation_euler.z-math.radians(60))<1e-5
            obstacles={n:at(n) for n in fixed}
            for n in movers:local.extend(dict(frame=float(fr),moving=n,**h) for h in overlaps(at(n),obstacles))
            if len(local)>20:break
        retention_rows.append(dict(source_step=source_step,samples=count,hits=local));retention_hits+=local
        print('RETENTION_ANIMATION_READBACK',source_step,count,local[:2],flush=True)
    rr=dict(status='FAIL' if retention_hits else 'PASS',stages=retention_rows,samples=sum(x['samples'] for x in retention_rows),hits=retention_hits,scope='Saved matrices at half frames. Keeper remains fixed while yaw turns60deg; head cradle fitted afterwards. No continuous sweep, physical threads, hand or harness qualification.')
    save_json(OUT/'head_retention_path_validation.json',rr)
    assert not retention_hits,retention_hits[:3]
    report['head_retention_readback']={'status':'PASS','samples':rr['samples'],'report':'head_retention_path_validation.json'}
if '--native-only' in sys.argv:
    result={'status':'PASS','revision':P['revision'],'animation_revision':report['animation_revision'],'source_is_unchanged':True,'readback_actor_count':len(actors),'all_actor_meshes_match_source':True,'final_matrix_max_error_mm':max(errors.values()),'editable_object_actions':len(actors),'timeline_markers':len(scene.timeline_markers),'stage_camera_and_visibility':native,'body_sequence_readback':report.get('body_sequence_readback'),'head_retention_readback':report.get('head_retention_readback'),'video':'NOT_REVALIDATED; existing MP4 has not been checked against this generated animation','continuous_collision_check':'NOT_TESTED','physical_assembly_process':'NOT_TESTED'}
    save_json(OUT/'validation.json',result);report['readback_validation']='animation/validation.json';report['animation_blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();save_json(OUT/'manifest.json',report)
    print('NATIVE_ANIMATION_VALIDATED',len(actors),flush=True);sys.exit(0)
assert video.exists() and video.stat().st_size>100_000
clip=bpy.data.movieclips.load(str(video));assert list(clip.size)==report['resolution'];assert clip.frame_duration==scene.frame_end
assert abs(clip.fps-report['fps'])<.01
result={'status':'PASS','animation_revision':report['animation_revision'],'source_is_unchanged':True,'readback_actor_count':len(actors),'all_actor_meshes_match_source':True,'final_matrix_max_error_mm':max(errors.values()),'editable_object_actions':len(actors),'timeline_markers':len(scene.timeline_markers),'stage_camera_and_visibility':native,'body_sequence_readback':report.get('body_sequence_readback'),'head_retention_readback':report.get('head_retention_readback'),'video':{'file':'MORI_assembly.mp4','bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'decoded_dimensions_px':list(clip.size),'decoded_frames':clip.frame_duration,'decoded_fps':clip.fps,'duration_seconds':clip.frame_duration/clip.fps},'continuous_collision_check':'NOT_TESTED','physical_assembly_process':'NOT_TESTED'}
save_json(OUT/'validation.json',result)
report['rendered_video']=True;report['video']=result['video'];report['readback_validation']='animation/validation.json';report['animation_blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();save_json(OUT/'manifest.json',report)
print('ANIMATION_VALIDATED',json.dumps(result,ensure_ascii=False))
