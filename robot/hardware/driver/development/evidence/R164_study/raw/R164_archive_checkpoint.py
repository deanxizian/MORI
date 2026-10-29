"""Preserve seven R164 native studies and exact failures; do not adopt them."""
import collections
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
dev=Path('robot/hardware/driver/development')
src=dev/'native'
study=dev/'evidence/R164_study'
board='MORI_Interface_C3.kicad_pcb'
expected='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert not study.exists() and sha(src/board)==expected
status=read(dev/'STATUS.json')
assert status['revision']=='C3 R159H' and status['unconnected_items']==22
members={r['member']:r['sha256'] for r in read(dev/'evidence/R159H/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(src/n)==h for n,h in members.items())
source_all={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()}
va=read(b/'R164A-verification/result.json')
vg=read(b/'R164G-verification/result.json')
da=read(b/'R164A-planned-delta.json')
dg=read(b/'R164G-planned-delta.json')
ia=read(b/'R164A-inspection.json')
ig=read(b/'R164G-inspection.json')
aa=read(b/'R164A-verification/regression.json')
ag=read(b/'R164G-verification/regression.json')
assert tuple(va[k] for k in ['unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps'])==(22,2,0,0,0)
assert tuple(vg[k] for k in ['unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps'])==(22,1,0,0,2)
assert da['errors']==['all_prior_pad_connections']
assert dg['errors']==['all_prior_pad_connections','power_width','new_reference_copper']
assert len(aa['power_width'])==50 and all(r['status']=='PASS' for r in aa['power_width'])
assert [r['net'] for r in aa['lost_pad_connections']]==['/13 {slash} Head_Fault_Delay/HEAD_UV_N']
assert [r['net'] for r in ag['lost_pad_connections']]==['MOTION_3V3']
for i,a,v in [(ia,aa,va),(ig,ag,vg)]:
    assert i['source_ground_vias_preserved']==114 and not i['same_face_nominal_body_hits']
    assert len(a['GND_groups'])==1 and len(a['GND_groups'][0])==155
    assert not a['retained_trace_reference_loss']
    assert v['historical_transition_flags']==6 and v['ina300_rlimit_return_screen']=='PASS'

def write(p, data):
    with p.open('x') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')

view_paths=sorted((b/'R164-local-views').glob('*.png'))
assert len(view_paths)==4
write(b/'R164-local-view-review.json',{
    'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),
    'method':'Four native geometry diagnostic PNGs actually viewed; not KiCad GUI screenshots and not a whole-board review.',
    'images':[{'path':p.relative_to(b).as_posix(),'sha256':sha(p)} for p in view_paths],
    'observations':[
        'A B view shows the right-edge bias pair with outward ENABLE escape, a straight intermediate-node connection and a direct local ground connection. The restored ENABLE In3 branch is visible in the companion layer view.',
        'G F view shows the J101.30 filled-ground lobe next to the new (42.1,28.6) transfer and the unchanged BAT_ADC route. Native DRC still reports two spokes touching dead copper; visual continuity through the pad does not waive this failure.',
        'G In3 view shows the shortened divider path close to two existing UV transfers. The separate In4 reference audit reports two uncovered portions; the In3 image alone cannot prove reference coverage.'
    ],
    'same_face_nominal_body_screen':{'R164A':0,'R164G':0},
    'whole_board_visual':'NOT_TESTED','manufacturer_thermal_coupling':'NOT_TESTED',
    'physical':'NOT_TESTED','adopted':False})

study.mkdir()
payloads=[];omitted=[];trials=[]
def preserve(p,rel):
    data=p.read_bytes();compress=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288
    dest=study/rel
    if compress:dest=dest.with_name(dest.name+'.gz')
    dest.parent.mkdir(parents=True,exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
    payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),
        'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})

roots=[b/('R164'+s) for s in 'ABCDEFG']
for top in sorted(b.glob('R164*')):
    files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
    for p in files:
        omit=False
        for root in roots:
            if p.is_relative_to(root):
                rel=p.relative_to(root).as_posix()
                if rel in members and sha(p)==members[rel]:
                    omitted.append({'local_path':p.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(p)})
                    omit=True
                break
        if not omit:preserve(p,Path('raw')/p.relative_to(b))
for name in ['build_trial.py','footprint_side_change.py','review_planned_delta.py','zone_expansion.py',
             'copper_geometry.py','audit_candidate.py','verify_trial.py','audit_ina300_return.py',
             'plan_layered_route.py','plan_existing_copper.py']:
    preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R162_inspection.py',
             'R161R_inspection.py','R161_power_aware_search.py','R163_divider_assignment.py',
             'R163F-plan.json','R140_width_restore.py','R151_power_region_bridge.py','R151_power_region_bridge_v2.py']:
    preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R164.json'))
for root in roots:
    rev=root.name;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    trials.append({'revision':rev,'board_sha256':sha(root/board),'adopted':False,
        **{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
        'DRC_types':dict(collections.Counter(x['type'] for x in d['violations'])),
        'old_connection_losses':[x['net'] for x in a['lost_pad_connections']],
        'power_width_failures':[{'net':x['net'],'width_mm':x['width_mm'],'lost_pair_count':len(x['lost_pairs'])} for x in a['power_width'] if x['status']!='PASS'],
        'old_reference_losses':len(a['retained_trace_reference_loss']),
        'new_reference_gaps':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review'])})

summary={
    'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
    'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    'source_revision':'R159H','source_sha256':expected,'remote_main':'aa94dddebcc8ca40cc4b63616147f81448ef087f',
    'adopted_revision':None,'continuation_preparation':'R164A',
    'A_full_verification':va,'G_full_verification':vg,
    'planned_delta':{'A':{'checks':len(da['checks']),'errors':da['errors']},'G':{'checks':len(dg['checks']),'errors':dg['errors']}},
    'candidates':trials,'source_ground_vias_preserved':114,'ground_pads_in_one_group':155,
    'progress':[
        'A restores the R1311/R1312 ENABLE bias branch using its original right-side transfer and original two In3 segments. R1311 B (68.8,18.25), R1312 B (68.8,21.25), both 90 degrees; native values, pads and nets unchanged.',
        'A preserves all 50 power-width checks and new/old reference screens, but UV_N remains broken. It is 22 opens plus two dangling items, not an adopted 22-open replacement.',
        'B/C/D upper-left UV escape trials fail the required four-spoke J702 ground thermal; moving the comparator also causes local supply/clearance regressions. Do not reuse these as accepted placements.',
        'E shortens the divider inner-layer loop and opens a route for UV_N. F/G join UV_N, but their In3 path splits MOTION_3V3 into 49 and 7 pads. The seven affected pads are C1101.1,C1304.1,C402.1,U1101.5,U1302.5,U1302.6,U402.14.',
        'F introduces J101.30 ground thermal failures on F/In1/In4. G moves the new transfer from (43.7,29.1) to (42.1,28.6), restores both inner-layer thermals, but still has one F-layer dead-copper thermal error.',
        'E/F/G also have two new divider reference gaps: 0.217009184879615 and 0.009822809698615364 square mm. The preliminary inspection of a nonexistent status field missed these; that interpretation was corrected. Old reference losses remain zero, which does not imply new routes pass.'
    ],
    'search_limits':[
        'The old R140 width-only helper rejected pad anchors before searching; its AssertionError is a tool-scope limitation, not a board feasibility result.',
        'The existing region helper supporting both pad and via anchors found no fixed-layout 0.50 mm bridge preserving foreign power fill at the 0.48 mm gate. No new-via mode ran. This bounded miss does not prove the board unroutable.'
    ],
    'next_actions':[
        'Continue from R164A, rebuilt using the full explicit plan against R159H. Keep its restored ENABLE pair and retain the R159H UPS/INA300 changes.',
        'Jointly rework the UV middle-node loop, UV transfer positions and power corridor. Do not adopt the E/F/G shortened loop with its known reference gaps or the UV trace that splits the 3V3 supply.',
        'The new left output transfer requires native four-spoke checking on all layers. G still fails F.Cu despite passing both ground reference planes. Native keepouts and all source GND vias remain fixed.',
        'After a clean candidate, rerun complete native/planned/power/reference/INA checks and extend actual layer/manufacturer/thermal/coupling review. All 22 canonical opens and full engineering work remain active.'
    ],
    'local_view_evidence':'raw/R164-local-view-review.json','whole_board_visual':'NOT_TESTED',
    'manufacturer_thermal_coupling_qualification':'NOT_TESTED','physical':'NOT_TESTED',
    'canonical_non_PCB_members_preserved':77,'remaining_unconnected_items_in_adopted_development':22,
    'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,
    'connectivity_fraction_is_not_engineering_progress':True,
    'engineering_status':'FAIL','manufacturing_release':False,'goal_complete':False}
write(study/'summary.json',summary)
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,
    'source_R159H_non_PCB_members':members,'unchanged_native_members_omitted':omitted,
    'original_local_sources_preserved':True,
    'reconstruction':'Use the R159H non-PCB source members with each archived PCB and saved metadata overlay. Full plans rebuild from R159H; R163F search input remains in R163_study.'})
for r in payloads:
    p=study/r['path'];assert sha(p)==r['sha256']
    data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes()
    assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
assert source_all=={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'completed_native_trials':7,
    'all_original_byte_hashes_match':True,'source_native_all_members_unchanged':True,
    'source_local_trials_untouched':True,'source_board_sha256':expected})
status.update({'last_followup_study':'R164','latest_study_evidence':'evidence/R164_study/summary.json',
    'latest_study_adopted':False,
    'latest_study_note':'A restores the ENABLE bias branch while preserving power/reference checks, but UV_N remains open. G joins UV_N but splits 3V3 and has two new reference gaps plus a thermal failure; all R164 candidates rejected. Canonical R159H / 22 opens / 55 percent unchanged.'})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payload_count':len(payloads),'completed_native_trials':7,'continuation_preparation':'R164A','adopted':False,'canonical_remaining':22}))
