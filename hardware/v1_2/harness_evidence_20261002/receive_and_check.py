"""Verify the received H01-H04 report and catalogue-range arithmetic.

This does not rerun Blender geometry, qualify crimps, or release cut lengths.
Only files in this directory are written. Existing received snapshots are immutable.
"""
from pathlib import Path
import csv
import datetime
import hashlib
import itertools
import json
import math
import platform

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
MECH = PROJECT / 'mechanical/studies/prearrival_finish/harness_A2'
SNAPS = ROOT / 'received_fourteen'
EXPECTED_REPORT = '0b788e94e7045d15d864c82ef58d46dbbbf770110b34a082d374b223f89d81c1'
EXPECTED_BODY_REPORT = '74ed4fdb5d4db7c97b28c787cea37d1effc9819d42d883f17c5708d365bc7acc'
BLEND_HASH = 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def receive(path, expected):
    content = path.read_bytes()
    assert hashlib.sha256(content).hexdigest() == expected, str(path)
    dest = SNAPS / path.name
    if dest.exists():
        assert dest.read_bytes() == content, 'Refusing to overwrite changed received snapshot'
    else:
        dest.write_bytes(content)
    return {'path': str(path.relative_to(PROJECT)), 'sha256': expected, 'snapshot': str(dest.relative_to(ROOT))}

def main():
    SNAPS.mkdir(exist_ok=True)
    records = [receive(MECH/'fourteen_validation.json', EXPECTED_REPORT)]
    records.append(receive(MECH/'fourteen_body_sequence.json', EXPECTED_BODY_REPORT))
    v = json.loads((SNAPS/'fourteen_validation.json').read_text())
    body = json.loads((SNAPS/'fourteen_body_sequence.json').read_text())
    assert body['source_blend_sha256'] == BLEND_HASH
    assert body['source_wire_check_sha256'] == EXPECTED_REPORT
    assert body['status']=='FAIL' and body['position_samples']==407
    for path, expected in v['sources'].items():
        records.append(receive(PROJECT/path, expected))
    assert sha(PROJECT/'mechanical/mori_v1_2.blend') == BLEND_HASH == v['source_blend_sha256']
    six = json.loads((SNAPS/'ecowire_joint.json').read_text())
    imu = json.loads((SNAPS/'imu_wide_joint.json').read_text())
    routes = six['routes'] + imu['routes']
    ids = {r['id'] for r in routes}
    expected_ids = {f'{h}_{pin}' for h,n in [('H01',2),('H02',2),('H03',2),('H04',8)] for pin in range(1,n+1)}
    assert ids == expected_ids
    assert len(v['envelopes']) == len(v['rigid_solids']) == 14
    assert all(e['positive_connected_components'] == 1 for e in v['envelopes'])
    assert {e['id'] for e in v['envelopes']} == ids
    actual_pairs = {tuple(sorted([r['a'],r['b']])) for r in v['wire_to_wire']}
    assert actual_pairs == set(itertools.combinations(sorted(ids),2)) and len(v['wire_to_wire']) == 91
    assert all(r['status']=='PASS' and not r['overlaps'] and not r['under_0p3_gap'] for r in v['rigid_solids'])
    assert all(r['status']=='PASS' and r['intersection_mm3']==0 for r in v['wire_to_wire'])
    assert v['head_motion']['poses']==130 and not v['head_motion']['overlaps']
    assert v['source_unchanged'] and not v['main_geometry_changed'] and not v['cut_lengths_released']
    assert {r['pin'] for r in imu['routes'] if r['route_side']=='left'} == set(range(1,6))
    assert {r['pin'] for r in imu['routes'] if r['route_side']=='right'} == {6,7,8}

    # Exact part candidates, not generic AWG/UL substitutions.
    wires = {'6711': {'awg':26,'od_inches':0.038,'od_tolerance_inches':0.002},
             '6712': {'awg':24,'od_inches':0.043,'od_tolerance_inches':0.002}}
    for w in wires.values():
        w['od_min_mm'] = round((w['od_inches']-w['od_tolerance_inches'])*25.4,6)
        w['od_max_mm'] = round((w['od_inches']+w['od_tolerance_inches'])*25.4,6)
        w['static_bend_screen_mm'] = round(5*w['od_max_mm'],6)
        w['SPH002_catalogue_window_check'] = 'PASS' if 24<=w['awg']<=30 and .8<=w['od_min_mm']<=w['od_max_mm']<=1.5 else 'FAIL'
        w['crimp_qualification'] = 'NOT_TESTED'
        w['selected_for_procurement'] = False
    rows = []
    port_pairs = {'H01':('power_J17','motion_J1'),'H02':('motion_J2','power_J13'),
                  'H03':('motion_J3','power_J14'),'H04':('motion_J4','imu_J1')}
    for r in sorted(routes,key=lambda row:row['id']):
        w = wires['6712' if r['harness']=='H01' else '6711']
        assert (r['from_port'],r['to_port']) == port_pairs[r['harness']]
        assert math.isclose(r['wire_OD_max_mm'],w['od_max_mm'],abs_tol=1e-6)
        bend = r.get('minimum_curvature_radius_mm',r.get('analytic_bend_radius_mm'))
        assert bend+1e-6 >= w['static_bend_screen_mm']
        rows.append({'wire':r['id'],'from_port':r['from_port'],'from_pin':r['pin'],
                     'to_port':r['to_port'],'to_pin':r['pin'],
                     'candidate':'Alpha '+('6712' if r['harness']=='H01' else '6711'),
                     'awg':w['awg'],'OD_min_mm':w['od_min_mm'],'OD_max_mm':w['od_max_mm'],
                     'catalogue_5D_screen_mm':w['static_bend_screen_mm'],
                     'reported_curve_min_radius_mm':bend,
                     'geometric_length_NOT_CUT_LENGTH_mm':r['geometric_centerline_length_mm'],
                     'cut_length_mm':'','crimp_status':'NOT_TESTED','procurement_release':'BLOCKED'})
    with (ROOT/'fourteen_static_candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    minpair=min(v['wire_to_wire'],key=lambda r:r['conservative_inflated_capsule_gap_lower_bound_mm'])
    minrigid=min(({'wire':r['id'],**g} for r in v['rigid_solids'] for g in r['gap_checks']),key=lambda g:g['conservative_capsule_gap_lower_bound_mm'])
    formal=json.loads((PROJECT/'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json').read_text())
    changed=[p for p,h in formal.items() if sha(PROJECT/p)!=h]
    assert not changed, changed
    report={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command':'python3 hardware/v1_2/harness_evidence_20261002/receive_and_check.py',
            'python':platform.python_version(),'status':'PASS',
            'scope':'Received-source integrity, internal count/pin consistency and catalogue-range arithmetic only; not an independent geometry rerun',
            'received':records,'source_blend_sha256':BLEND_HASH,'wire_count':14,'pair_count':91,'head_pose_count':130,
            'minimum_reported_pair':minpair,'minimum_reported_rigid':minrigid,'wire_catalogue_checks':wires,
            'body_assembly_status':body['status'],'body_assembly_sample_count':body['position_samples'],
            'body_assembly_conflicts':[{'path':p['id'],'status':p['status'],'pairs':p['pairs']} for p in body['paths']],
            'bridge_screw_tools':body['tools'],
            'finished_harness_quantity':4,'PHR_2_quantity':4,'PHR_3_quantity':2,'PHR_8_quantity':2,
            'SPH_002_contacts_installed_quantity':28,'quantity_scope':'H01-H04 only; no spare contacts or other harnesses included',
            'formal_source_files_verified_unchanged':len(formal),'changed_formal_files':changed,
            'native_CAD_changed':False,'mechanical_model_changed':False,'procurement_released':False,
            'cut_lengths_released':False,'power_on_released':False,
            'limitations':v['limits']+['IMU route-source pending wording is historical; its matching hash is consumed by the fourteen-wire report.',
                                       'Nominal catalogue overlap is not JST/Alpha approval of this insulation/crimp combination.']}
    (ROOT/'receipt_and_range_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','wire_count','pair_count','head_pose_count','formal_source_files_verified_unchanged','procurement_released']},ensure_ascii=False))

if __name__=='__main__': main()
