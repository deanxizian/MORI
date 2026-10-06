"""Independent order study; no model, source hardware, or fastener changes.

Keep the mounted CAM and its four candidate wires in place while installing
the pitch servo. Retain failed path trials and distinguish removed screws
from genuinely absent geometric obstacles.
"""
from pathlib import Path
SL_SCRIPT=Path(__file__).resolve();SL_ROOT=SL_SCRIPT.parent
SL_HELPER=SL_ROOT/'check_CAM_board_last.py';__file__=str(SL_HELPER)
exec(compile(SL_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(SL_HELPER),'exec'),globals())
__file__=str(SL_SCRIPT)
SL_OUT=SL_ROOT/'cam_servo_last';SL_OUT.mkdir(exist_ok=True)
sl_all=bl_fixture|bl_board|bl_deferred|{'CAM_catalogue_housing':bl_plug}
for n in ['Pitch_Output','Yaw_Output']:
    sl_all[n]=ss[n].m
sl_core,sl_tails,sl_meta=bl_curves(0.,0.)
sl_wires=[(f'core_{i}',sl_core+[xx[i]-xx[0],0.,0.],sl_meta['core_error_mm']) for i in range(4)]
sl_wires += [(f'tail_{i}',sl_tails[i],sl_meta['tail_error_mm']) for i in range(4)]

def sl_hits(m,fixture):
    hits=[]
    for n,t in fixture.items():
        if not overlap_boxes(m,t,.001):continue
        v=max(0.,float((m^t).volume()))
        if v>1e-4:hits.append({'obstacle':n,'intersection_mm3':v})
    return hits

def sl_path(label,moving,removed,path,step=.5):
    fixture={n:m for n,m in sl_all.items() if n not in set(moving)|set(removed)}
    points=[]
    for a,b in zip(path,path[1:]):
        a,b=np.array(a,float),np.array(b,float)
        p=np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
        points.extend(p if not points else p[1:])
    hits=[];checked=0
    for d in points:
        checked+=1
        for n in moving:
            m=sl_all[n].translate(d.tolist())
            hits.extend({'moving':n,'displacement_mm':d.tolist(),**h} for h in sl_hits(m,fixture))
            target=pw_obstacle(n,'tool',m)
            for wire,p,e in sl_wires:
                hit=check_one(p,e,target[3],target[4],m,target[5])
                if hit:hits.append({'moving':n,'displacement_mm':d.tolist(),'wire':wire,**hit})
        if hits:break
    row={'id':label,'status':'BLOCKED' if hits else 'PASS','moving':moving,
         'removed':sorted(removed),'fixed':sorted(fixture),'withdrawal_waypoints_mm':path,
         'maximum_step_mm':step,'checked_positions':checked,'hits':hits,
         'continuous_path':'NOT_TESTED','direction':'reverse for insertion'}
    print('SERVO_LAST_PATH',label,row['status'],hits[:3],flush=True)
    return row

if __name__=='__main__':
    started=time.time();rows=[]
    pitch_bolts={n for n in sl_all if n.startswith('Head_Pitch_Ear_')}
    yaw_parts={n for n in sl_all if n.startswith(('Yaw_Servo','Yaw_Output','Yaw_Lock_Screw','Head_Yaw_Ear_'))}
    pitch=['Pitch_Servo','Pitch_Output']
    variants=[
      ('right_then_down',[[0,0,0],[6,0,0],[6,0,-3],[35,0,-3],[35,0,65]]),
      ('right_then_front',[[0,0,0],[6,0,0],[6,6.5,0],[35,6.5,0],[35,6.5,65]]),
      ('front_exit',[[0,0,0],[6,0,0],[6,32,0],[6,32,70]]),
      ('front_low_exit',[[0,0,0],[6,0,0],[6,0,-3],[6,32,-3],[6,32,70]]),
    ]
    for yaw_first in [True,False]:
        removed=pitch_bolts if yaw_first else pitch_bolts|yaw_parts
        for label,path in variants:
            rows.append(sl_path(('yaw_present_' if yaw_first else 'yaw_later_')+label,pitch,removed,path))
    out={'status':'PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
         'scope':'Rigid pitch-servo order trials with final CAM core/tail candidate wires. Not a complete assembly sequence.',
         'rows':rows,'source_main_sha256':source_hash,'script_sha256':sha(SL_SCRIPT),'helper_sha256':sha(SL_HELPER),
         'subsequent_servo_fasteners':'NOT_TESTED','servo_harness':'NOT_TESTED','whole_harness':'BLOCKED',
         'main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
    (SL_OUT/'screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    assert sha(source)==source_hash
    print('SERVO_LAST_DONE',out['status'],flush=True)
