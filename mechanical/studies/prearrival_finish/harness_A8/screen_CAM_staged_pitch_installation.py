"""Explicit pitch assembly stages on the latest unadopted neck candidate.

Kinematic ownership is not assembly membership: the servo's Pitch_Output is
installed with its servo even though it rotates with the pitch joint. All
later shafts, locking screws, optics and shells are named rather than hidden.
"""
from pathlib import Path
PST_SCRIPT=Path(__file__).resolve();PST_A8=PST_SCRIPT.parent
PST_HELPER=PST_A8/'screen_CAM_split_head_assembly.py'
__file__=str(PST_HELPER)
exec(compile(PST_HELPER.read_text().split('\n# These are reverse',1)[0],str(PST_HELPER),'exec'),globals())
__file__=str(PST_SCRIPT)
PST_OUT=SPLIT_OUT/'pitch_stages';PST_OUT.mkdir(exist_ok=True)
yaw=yaw|{'Pitch_Output'};pitch=pitch-{'Pitch_Output'}
cradle={'Pitch_Cradle','CAM_Mainboard'}|{n for n in pitch if n.startswith(('CAM_Mount_','Onboard_MIC_','Head_Cradle_Insert_'))}
horn={'Pitch_Horn'};shafts={'Pitch_Trunnion_L','Pitch_Trunnion_R'};lock={'Pitch_Lock_Screw'}
optics={'Display_Frame','Display_PCB'}|{n for n in pitch if n.startswith('LCD_Mount_') or n.startswith('Face_Joint_') and n.endswith('_Nut')}
camera={'Camera_PCB','Camera_Lens'}
face_screws={n for n in pitch if n.startswith('Face_Joint_') and n.endswith('_Screw')}
front={'Head_Front'}|{n for n in pitch if n.startswith('Head_Seam_Insert_')}
rear={'Head_Rear'}
shell_screws={n for n in pitch if n.startswith(('Head_Cradle_Screw_','Head_Seam_Screw_'))}
pitch_groups=dict(cradle_CAM=cradle,horn=horn,shafts=shafts,axial_lock=lock,optics=optics,
                  camera=camera,face_screws=face_screws,front_shell=front,rear_shell=rear,shell_screws=shell_screws)
assert set.union(*pitch_groups.values())==pitch
assert sum(len(v) for v in pitch_groups.values())==len(pitch)
rows=[];started=time.time()
check('complete_yaw_including_servo_output',[(trans(z=float(z)),) for z in np.arange(0,90.01,.5)],
      [yaw],fixture|upper|bridge,'Pitch_Output travels with its physical servo. All 21 yaw-stage pieces included.')
base=fixture|upper|bridge|yaw|keeper_screws|reaction_retainer
check('cradle_CAM_before_horn_and_shafts',[(trans(z=float(z)),) for z in np.arange(0,70.01,.5)],
      [cradle],base,f'{len(cradle)}-piece source CAM/cradle module; horn and both short shafts remain loose.')
check('cradle_CAM_with_horn',[(trans(z=float(z)),) for z in np.arange(0,70.01,.5)],
      [cradle|horn],base,'Diagnostic for the old animation grouping; horn is not silently omitted.')

def xtr(x):
    t=I.copy();t[0,3]=float(x);return t
for side,sign in [('L',-1),('R',1)]:
    moving={f'Pitch_Trunnion_{side}'}
    check('short_shaft_'+side,[(xtr(sign*d),) for d in np.arange(0,28.01,.5)],
          [moving],base|cradle,'Nominal placeholder shaft only; actual manufacturer interface is still unresolved.')
check('pitch_horn_from_left',[(xtr(-d),) for d in np.arange(0,28.01,.5)],
      [horn],base|cradle|shafts,'Current placeholder horn; pending vendor evidence, not a qualified transmission.')
check('pitch_axial_lock_from_left',[(xtr(-d),) for d in np.arange(0,25.01,.5)],
      [lock],base|cradle|shafts|horn,'Nominal lock screw, physical engagement/tool not certified.')
fixed=base|cradle|shafts|horn|lock
check('optical_frame_front_entry',[(trans(y=float(y)),) for y in np.arange(0,70.01,.5)],
      [optics],fixed,'Vendor LCD plus all three mount screws; four frame nuts remain with the optical fork.')
check('camera_along_optical_axis',[(trans(y=float(y),z=float(y*math.tan(math.radians(10)))),) for y in np.arange(0,24.01,.5)],
      [camera],fixed|optics,'Current camera reference and integral capture seat; front shell not yet fitted.')
for sign in [-1,1]:
    ids={n for n in face_screws if n.startswith('Face_Joint_'+str(sign)+'_')}
    check('face_screws_'+str(sign),[(xtr(sign*d),) for d in np.arange(0,25.01,.5)],
          [ids],fixed|optics|camera,'Screw translation only; tool turning remains a separate check.')
fixed|=optics|camera|face_screws
check('head_front_shell',[(trans(y=float(y)),) for y in np.arange(0,68.01,.5)],
      [front],fixed,'Head front and its seam inserts; camera capture closes at final position.')
check('head_rear_shell',[(trans(y=float(-y)),) for y in np.arange(0,68.01,.5)],
      [rear],fixed|front,'Rear shell with front already placed; shell screws remain loose.')

report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite full-member staged rigid assembly diagnostics; includes current placeholder transmission but does not qualify it',
    script_sha256=sha(PST_SCRIPT),helper_sha256=sha(PST_HELPER),source_main_sha256=source_hash,
    source_split_report_sha256=sha(SPLIT_OUT/'screen.json'),protected_sources=protected,
    substituted_unadopted_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacements.items()},
    source_objects=209,yaw_members=sorted(yaw),pitch_membership={n:sorted(v) for n,v in pitch_groups.items()},
    rows=rows,rigid_intersection_threshold_mm3=1e-5,continuous_motion='NOT_TESTED',
    full_wire_material_and_connectors='NOT_TESTED',tools_and_hand_support='NOT_TESTED',
    transmission_interfaces='BLOCKED_PENDING_VENDOR',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-started)
(PST_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('STAGED_PITCH_DONE',report['status'],round(time.time()-started,2),flush=True)
