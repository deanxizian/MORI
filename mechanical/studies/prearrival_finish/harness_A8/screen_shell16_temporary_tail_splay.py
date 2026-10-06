"""Temporarily splay an unconnected free tail during CAM feed assembly.

Native body contacts, bridge and print geometry remain fixed. Rotation is of
the loose wire tail, not the head, bridge, connector pin order or printed guide.
The final return and upper assembly remain explicit follow-up requirements.
"""
from pathlib import Path
SPLAY16_SCRIPT=Path(__file__).resolve()
SPLAY16_HELPER=SPLAY16_SCRIPT.parent/'merge_shell16_back20_wires.py'
splay_source=SPLAY16_HELPER.read_text();splay_marker='\nfor k in range(21):'
__file__=str(SPLAY16_HELPER)
exec(compile(splay_source.split(splay_marker,1)[0],str(SPLAY16_HELPER),'exec'),globals())
__file__=str(SPLAY16_SCRIPT)
import copy
OUT=ORDER_OUT/'shell16_temporary_tail_splay';OUT.mkdir(exist_ok=True)
original_holds=copy.deepcopy(holds);splay_original_one=one
splay_loop='for k in range(21):'+splay_source.split(splay_marker,1)[1].split('\nnp.savez_compressed',1)[0]


def one(pin,p):
    angle=float(p.get('tail_yaw_deg',0.))
    if angle==0.:return splay_original_one(pin,p)
    original=specifications[pin]
    T=np.asarray(Matrix.Rotation(math.radians(angle),4,'Z'))
    specifications[pin]=dict(original,
        selected=dict(original['selected'],azimuth_deg=original['selected']['azimuth_deg']+angle),
        tail=transform_points(original['tail'],T))
    try:
        return splay_original_one(pin,p)
    finally:
        specifications[pin]=original


def blend_parameters(a,b,t):
    out={key:(1-t)*a[key]+t*b[key] for key in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']}
    out['tail_yaw_deg']=(1-t)*a.get('tail_yaw_deg',0.)+t*b.get('tail_yaw_deg',0.)
    assert a['family']==b['family'];out['family']=a['family'];return out


trials=[];chosen_splay=None;chosen_arrays={};chosen_records=[]
for splay_angle in [15.,30.,45.,-15.,-30.]:
    holds=copy.deepcopy(original_holds)
    holds[0][4]=[dict(starts[4],entry_azimuth_deg=-7.5,planar_radius_mm=8.)]
    holds[2][1]=[dict(starts[1],elevation_fraction=.5,tail_yaw_deg=splay_angle)]
    current={pin:dict(p) for pin,p in starts.items()};records=[];diagnostics=[];saved={};failure=None
    f,curves,pairs=evaluate(0.,current);assert not f,f
    for pin,c in curves.items():assert np.array_equal(c['points'],start_curves[f'pin{pin}_pose36'])
    store_record(0.,'initial',current,curves,pairs)
    exec(compile(splay_loop,str(SPLAY16_HELPER),'exec'),globals())
    row=dict(tail_yaw_deg=splay_angle,status='BLOCKED' if failure else 'PASS',
             passing_positions=len(records),furthest_back_mm=-records[-1]['bridge_y_mm'],
             failure=failure,diagnostics=diagnostics)
    trials.append(row)
    print('TAIL_SPLAY_TRIAL',splay_angle,row['status'],row['furthest_back_mm'],failure,flush=True)
    if not failure:
        chosen_splay=row;chosen_arrays=saved;chosen_records=records;break
np.savez_compressed(OUT/'curves.npz',**chosen_arrays)
report=dict(status='PASS' if chosen_splay else 'BLOCKED',
    scope='Finite four-wire shared rear motion with temporary free-tail yaw; final restoration not yet covered',
    script_sha256=sha(SPLAY16_SCRIPT),helper_sha256=sha(SPLAY16_HELPER),
    source_files={**graph['source_files'],str(graph_path.relative_to(PROJECT)):sha(graph_path),
                  str(rigid_all_path.relative_to(PROJECT)):sha(rigid_all_path)},
    protected_sources=protected,trials=trials,selected=chosen_splay,records=chosen_records,
    final_parameters=current if chosen_splay else None,curves_sha256=sha(OUT/'curves.npz'),
    body_wire_count=14,full_nominal_lengths_preserved=True,exact_initial_boundary_match=True,
    continuous_motion='NOT_TESTED',branch_continuity_audit='NOT_TESTED',
    vertical_continuation='NOT_TESTED',loose_tail_restoration='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('TAIL_SPLAY_DONE',report['status'],len(trials),round(time.time()-started,1),flush=True)
