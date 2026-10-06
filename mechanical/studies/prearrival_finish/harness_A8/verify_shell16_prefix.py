"""Audit saved shell16 prefix inputs, boundaries and sample coverage.

This independent data audit does not upgrade finite collision checks to
continuous motion or physical fit.
"""
from pathlib import Path
import hashlib,json
import numpy as np

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'shell16_joint_feed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
d=read(OUT/'screen.json');inputs={}
for section in ['source_files','protected_sources']:
    for p,h in d[section].items():
        assert sha(ROOT/p)==h,p
        inputs[p]=h
assert d['script_sha256']==sha(A8/'screen_shell16_joint_feed.py')
assert d['helper_sha256']==sha(A8/'screen_rear_plug_shell_angles.py')
assert d['curves_sha256']==sha(OUT/'curves.npz')
for p in [OUT/'screen.json',OUT/'curves.npz',A8/'screen_shell16_joint_feed.py',A8/'screen_rear_plug_shell_angles.py']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
assert d['status']=='PASS' and d['body_wire_count']==14
assert d['conservative_plug_envelopes_unchanged']
assert not d['main_applied'] and not d['manufacturing_release']
assert [s['checked_positions'] for s in d['prefix_stages']]==[61,37]
assert all(s['status']=='PASS' and s['planned_positions']==s['checked_positions'] for s in d['prefix_stages'])
saved=np.load(OUT/'curves.npz');source=np.load(ORDER/'CAM_H02_joint_lift/curves.npz')
checked=[];unique=set();pairs=[]
for stage in d['prefix_stages']:
    for row in stage['rows']:
        assert row['status']=='PASS' and row['failure'] is None
        p=row['pose'];i=row['index']
        assert p.get('by',0.)==p['y']==0.
        if stage['stage']=='shell_release':
            assert abs(p['a']-16.*i/60.)<1e-12 and abs(p['sz']-14.*i/60.)<1e-12
            assert p['bz']==0. and p['lift_index']==0
        else:
            assert p['a']==16. and p['sz']==14. and p['bz']==.5*i and p['lift_index']==i
        unique.add((p['a'],p['y'],p['sz'],p['bz']))
        assert len(row['pairs'])==6
        for pin in range(1,5):
            key=f"{stage['stage']}_pin{pin}_pose{i}"
            a=saved[key];b=source[f"pin{pin}_pose{p['lift_index']}"]
            assert a.ndim==2 and a.shape[1]==3 and np.all(np.isfinite(a))
            assert np.array_equal(a,b),key
            checked.append(key)
        pairs.extend(row['pairs'])
assert len(checked)==392 and len(unique)==97
gap=min(r['surface_gap_lower_bound_mm'] for r in pairs)
assert gap>=.3
for pin in range(1,5):
    assert np.array_equal(saved[f'shell_release_pin{pin}_pose60'],saved[f'bridge_lift_pin{pin}_pose0'])
assert len(d['continuation_diagnostics'])==6
assert all(r['status']=='BLOCKED' for r in d['continuation_diagnostics'])
report=dict(status='PASS',scope='Saved data and provenance audit; finite collision results remain separately scoped',
    script_sha256=sha(SCRIPT),source_files=inputs,protected_sources=d['protected_sources'],
    prefix_stages=[dict(stage=r['stage'],positions=r['checked_positions']) for r in d['prefix_stages']],
    finite_sample_records=98,unique_rigid_poses=97,curve_records=392,exact_joint_lift_curve_reuse=True,
    phase_boundary_identity=True,CAM_pair_gap_lower_bound_mm=gap,
    six_simple_continuations='BLOCKED',continuous_assembly='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SHELL16_PREFIX_DATA_AUDIT PASS 61+37 records / 97 unique poses / 392 saved curves')
