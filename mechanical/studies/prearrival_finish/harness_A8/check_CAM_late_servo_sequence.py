"""Test one deferred-servo sequence, retaining its failures as failures.

The earlier successful bare-yoke servo paths are replayed against the CAM
cradle and prescribed wires. These are finite placement checks, not complete
flexible wire formation or continuous tool/hand/assembly qualification.
"""
from pathlib import Path
LS_SCRIPT=Path(__file__).resolve();LS_ROOT=LS_SCRIPT.parent
LS_HELPER=LS_ROOT/'check_CAM_two_anchor_tool_access.py';__file__=str(LS_HELPER)
exec(compile(LS_HELPER.read_text().split('\nta_rows=[];',1)[0],str(LS_HELPER),'exec'),globals())
__file__=str(LS_SCRIPT)
LS_OUT=LS_ROOT/'cam_profiled_tool'
ls_deferred={n for n in ta_targets if n.startswith(('Head_Pitch_Ear_','Head_Yaw_Ear_'))}|{'Pitch_Servo','Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Lock_Screw'}
ls_bare={n:m for n,m in ta_targets.items() if n not in ls_deferred}
ls_tool=pt_tool.transform(ta_matrix);ls_sweep=pt_sweep.transform(ta_matrix);ls_tail=st_tail.transform(ta_matrix)
ls_work={'tool_fixture':st_hits(ls_sweep,ls_bare),'tool_wires':st_wire_hits(ls_sweep,0.),
         'tail_fixture':st_hits(ls_tail,ls_bare),'tail_wires':st_wire_hits(ls_tail,0.)}
ls_work['status']='PASS' if all(x['status']=='PASS' for x in ls_work.values()) else 'BLOCKED'

def ls_path(name,waypoints,targets):
    base=ta_targets[name];rows=[];failure=None
    # Waypoints are removal direction; reverse them to describe insertion.
    waypoints=list(reversed(waypoints));sample_count=0
    for seg,(a,b) in enumerate(zip(waypoints,waypoints[1:])):
        a=np.array(a,dtype=float);b=np.array(b,dtype=float)
        count=max(1,int(math.ceil(np.linalg.norm(b-a)/.5)))
        for t in np.linspace(0.,1.,count+1):
            shift=a+(b-a)*t;m=base.translate(shift.tolist());sample_count+=1
            fixture=st_hits(m,targets)
            wire=st_wire_hits(m,0.) if fixture['status']=='PASS' else {'status':'NOT_TESTED'}
            row={'offset_mm':shift.tolist(),'segment':seg,'fixture':fixture,'wires':wire,
                 'status':'PASS' if fixture['status']==wire['status']=='PASS' else 'BLOCKED'}
            rows.append(row)
            if row['status']!='PASS':failure=row;break
        if failure:break
    return {'status':'BLOCKED' if failure else 'PASS','part':name,'insertion_waypoints_mm':waypoints,
            'maximum_step_mm':.5,'checked_positions':sample_count,'rows':rows,'first_failure':failure,
            'continuous_path':'NOT_TESTED','full_pass_if_no_failure':not bool(failure)}

ls_pitch=ls_path('Pitch_Servo',[[0,0,0],[6,0,0],[6,6.5,0],[35,6.5,0],[35,6.5,65]],ls_bare)
ls_yaw=ls_path('Yaw_Servo',[[0,0,0],[0,0,50]],ls_bare|{'Pitch_Servo':ta_targets['Pitch_Servo']})
ls_result={'status':'PASS' if ls_work['status']==ls_pitch['status']==ls_yaw['status']=='PASS' else 'BLOCKED',
    'scope':'Conditional tie work with two servos deferred, followed by two explicit earlier bare-servo insertion paths with seated CAM/cradle and final prescribed CAM wires',
    'source_main_sha256':source_hash,'script_sha256':sha(LS_SCRIPT),'helper_sha256':sha(LS_HELPER),
    'deferred_parts':sorted(ls_deferred),'other_not_yet_fitted':wi_excluded,
    'tie_work':ls_work,'pitch_servo_path':ls_pitch,'yaw_servo_path':ls_yaw,
    'main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED',
    'wire_formation_tie_threading_hands':'NOT_TESTED','actual_horn_transmission':'BLOCKED',
    'screw_installation_in_this_new_order':'NOT_TESTED','other_possible_servo_paths':'NOT_TESTED'}
(LS_OUT/'late_servo_sequence.json').write_text(json.dumps(ls_result,ensure_ascii=False,indent=2)+'\n')
cache(LS_OUT/'connector_0_tool.npz',ls_tool);cache(LS_OUT/'connector_0_sweep.npz',ls_sweep);cache(LS_OUT/'connector_tail_corridor.npz',ls_tail)
assert sha(source)==source_hash
print('LATE_SERVO_DONE',ls_result['status'],'work',ls_work['status'],'pitch',ls_pitch['status'],ls_pitch['first_failure'],'yaw',ls_yaw['status'],ls_yaw['first_failure'],flush=True)
