"""Replay the saved front/rear-shell movie transforms, not source endpoints."""
from common import *


def run(scene, actors, report, base, at, overlaps):
    from assembly_animation import AP
    modules={
        'front':{n for n,o in actors.items() if o.parent and o.parent.name==AP+'Front_Shell'},
        'rear':{n for n,o in actors.items() if o.parent and o.parent.name==AP+'Rear_Shell'},
        'bridge':{n for n,o in actors.items() if o.parent and o.parent.name==AP+'Fixed_Bridge'}}
    rows=[];all_hits=[]
    bench=next(s for s in report['stages'] if s.get('source_step')==15)
    scene.frame_set(bench['end']+1);bpy.context.view_layer.update()
    for name,sign in [('Front_Shell',1),('Rear_Shell',-1)]:
        root=bpy.data.objects[AP+name]
        assert max(abs(v) for v in root.rotation_euler)<1e-6
        assert np.max(np.abs(np.array(root.location)-[0,sign*220,0]))<1e-6
    for source_step in [19,8,16,20]:
        stage=next(s for s in report['stages'] if s.get('source_step')==source_step)
        local=[];count=0
        for frame in np.arange(stage['start'],stage['end']+.01,.5):
            scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update();count+=1
            visible={n for n in base if n in actors and not actors[n].hide_render}
            if source_step in [19,8]:
                assert not (modules['front']|modules['rear']) & visible
                moving=modules['bridge']|({'Yaw_Base_-1_Screw','Yaw_Base_1_Screw'}&visible)
                # Installed screws engage the bridge's named nuts. Their
                # own nominal connection is not an unrelated collision.
                targets=visible-moving
            else:
                moving=modules['front' if source_step==16 else 'rear']
                targets=visible-moving-{n for n in visible if n.startswith('Frame_Screw_')}
            fixed={n:at(n) for n in targets}
            for n in moving&visible:
                local.extend(dict(frame=float(frame),moving=n,**hit) for hit in overlaps(at(n),fixed))
            if source_step==20:
                for n in visible:
                    if not n.startswith('Frame_Screw_'):continue
                    assert max(abs(x) for x in bpy.data.objects[AP+'Front_Shell'].location)<1e-5
                    assert max(abs(x) for x in bpy.data.objects[AP+'Rear_Shell'].location)<1e-5
                    others={k:at(k) for k in visible if k!=n and not k.startswith('Frame_Screw_')}
                    local.extend(dict(frame=float(frame),moving=n,**hit) for hit in overlaps(at(n),others))
            if len(local)>20:break
        rows.append(dict(source_step=source_step,display_step=stage['index'],samples=count,
                         status='FAIL' if local else 'PASS',hits=local))
        all_hits+=local
        print('FRONT_REAR_ANIMATION_READBACK',source_step,count,local[:2],flush=True)
    # Preserve the previously checked, unchanged servo bench motion too.
    stage=next(s for s in report['stages'] if s.get('source_step')==11)
    servo_hits=[];count=0
    for frame in np.arange(stage['start'],stage['end']+.01,.5):
        scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update();count+=1
        assert abs(bpy.data.objects[AP+'Yaw_Group'].location.z-64)<1e-4
        fixture={'Pitch_Yoke':at('Pitch_Yoke')}
        if not actors['Pitch_Servo'].hide_render:
            for n in ['Pitch_Servo','Pitch_Output']:
                servo_hits.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(at(n),fixture))
        if not actors['Yaw_Servo'].hide_render:
            fixture.update({n:at(n) for n in ['Pitch_Servo','Pitch_Output']})
            for n in ['Yaw_Servo','Yaw_Output']:
                servo_hits.extend(dict(frame=float(frame),moving=n,**h) for h in overlaps(at(n),fixture))
    result=dict(status='FAIL' if all_hits or servo_hits else 'PASS',animation_revision=report['animation_revision'],
        stages=rows,samples=sum(r['samples'] for r in rows),hits=all_hits,
        servo_bench=dict(samples=count,hits=servo_hits),
        shell_bench_presentation='Interior-facing display cut restores the exact neutral +/-220mm module pose before the checked insertion steps; not a physical in-place rotation path.',
        method='Saved animation matrices each half frame; current solid body modules and all visible rigid parts. Full soft-wire motion, hands, torque and continuous proof NOT_TESTED.')
    save_json(ROOT/'animation/front_rear_path_validation.json',result)
    assert result['status']=='PASS',(all_hits[:3],servo_hits[:3])
    return dict(status='PASS',samples=result['samples'],report='front_rear_path_validation.json')
