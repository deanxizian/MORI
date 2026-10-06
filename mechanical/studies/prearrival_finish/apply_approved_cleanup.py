"""Apply only the two user-approved M1.47 cleanups; retain the failed clamp.

Run once. All replaced source files and current deliverables are snapshotted.
"""
import json, shutil, hashlib
from pathlib import Path
from datetime import datetime, timezone

S = Path(__file__).resolve().parent
P = S.parents[2]
M = P / 'mechanical'
B = M / 'revisions/V1.2-M1.46_before_approved_thin_cleanup'
assert not B.exists(), 'Snapshot exists: inspect status; do not reapply blindly'
g = json.loads((P/'config/geometry.json').read_text())
assert g['revision'] == 'V1.2-M1.46'
files = ['config/geometry.json', 'contracts/mechanical_interfaces.json', 'AGENTS.md',
         'mechanical/mori_v1_2.blend', 'mechanical/mori_assembly_animation.blend',
         'mechanical/index.html', 'mechanical/README.md',
         'mechanical/studies/prearrival_finish/HARDWARE_INPUT_REQUEST.md',
         'mechanical/studies/prearrival_finish/MECHANICAL_PURCHASE_REQUIREMENTS.md']
for rel in files:
    src=P/rel
    if src.exists():
        dst=B/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
for rel in ['mechanical/scripts','mechanical/reports','mechanical/animation']:
    shutil.copytree(P/rel,B/rel,ignore=shutil.ignore_patterns('__pycache__','vendor'))
def replace(rel, old, new):
    f=P/rel; text=f.read_text(); assert text.count(old)==1,(rel,old)
    f.write_text(text.replace(old,new,1))

g['revision']='V1.2-M1.47'
g['drive_print_cleanup']['bearing_bar_depth_mm']=19.2
g['prearrival_thin_cleanup']={
    'enabled':True, 'revision':g['revision'], 'approved':True,
    'approval':'User: 这三项按推荐做; two local cleanups only; reaction clamp excluded',
    'suppress_retired_gimbal_bores':True,
    'changed_existing_ids':['Pitch_Yoke','Motor_Retainer','Drive_Bridge'],
    'baseline_blend':str((B/'mechanical/mori_v1_2.blend').relative_to(P)),
    'approved_shape_source':'mechanical/studies/prearrival_finish/thin_candidate_workspace/mechanical/mori_v1_2.blend',
    'approved_shape_ids':['Pitch_Yoke','Motor_Retainer','Drive_Bridge'],
    'cap_depth_source':'#/drive_print_cleanup/bearing_bar_depth_mm',
    'limits':['Nominal geometry only; PA12 strength and fits NOT_TESTED',
              'Yaw_Reaction_Link and its fastening unchanged; initial assembly remains BLOCKED',
              'Existing soft tyre search authorized; no wheel dimension change or order yet']}
(P/'config/geometry.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n')
replace('mechanical/scripts/simple_modules.py',
    "    for target in [upper,lower]:boolean(target,cyl('M2_clear'",
    "    retired = name.startswith('Gimbal_Base_') and P.get('prearrival_thin_cleanup',{}).get('suppress_retired_gimbal_bores',False)\n    for target in ([] if retired else [upper,lower]):boolean(target,cyl('M2_clear'")
replace('mechanical/scripts/simple_modules.py',"    boolean(lower,cyl('M2_nut_access'","    if not retired:boolean(lower,cyl('M2_nut_access'")
replace('mechanical/scripts/simple_modules.py',"    if name.startswith('Gimbal_Base_'):\n        boolean(lower,cyl('open_nut_channel'","    if name.startswith('Gimbal_Base_') and not retired:\n        boolean(lower,cyl('open_nut_channel'")
old="""        fill=cyl('retired_joint_hole',(x,11,hz-35.5),1.25,9)
        union(yoke,fill)
        plug=cyl('retired_nut_pocket',(x,11,hz-38.5),2.85,3)
        intersect(plug,ring('flange_boundary',(0,0,hz-38.5),20,8,3))
        union(yoke,plug)"""
replace('mechanical/scripts/part_consolidation.py',old,
    "        if not P.get('prearrival_thin_cleanup',{}).get('suppress_retired_gimbal_bores',False):\n"+'\n'.join('    '+x for x in old.splitlines()))
c=json.loads((P/'contracts/mechanical_interfaces.json').read_text())
for k in ['revision','mechanical_revision','current_geometry_revision']: c[k]=g['revision']
c['prearrival_thin_cleanup']=g['prearrival_thin_cleanup']
c['current_authority']['scope']='M1.47 adopts only the two approved thin-feature cleanups. Reaction clamp unchanged; remaining closure tracked separately.'
c['current_authority']['tyres']='User approved searching stock soft tyres first and adapting the hub after dimensions/selection review; present105x18 is still a design allocation, not a selected product.'
(P/'contracts/mechanical_interfaces.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
with (P/'AGENTS.md').open('a') as f:
    f.write('\n- M1.47 user explicitly approves the two local thin-feature cleanups: suppress obsolete Gimbal_Base bores/channels at construction and their later refill; widen Motor_Retainer bearing saddle depth18→19.2mm, using the same parameter for Drive_Bridge clearance. Only Pitch_Yoke, Motor_Retainer and Drive_Bridge may change. Preserve failed/unapproved Yaw_Reaction_Link clamp geometry and all hardware/axes; independently compare the three solids to the reviewed candidate and M1.46 baseline, and recheck motion/service/STL/animation. User also approves stock soft-tyre research before adapting hubs, with wheel-diameter/geometry changes returned for review, and authorizes expanded electrical requirements to the existing hardware chat. No order or manufacturing release.\n')
request=S/'HARDWARE_INPUT_REQUEST.md';text=request.read_text().replace('此文件是待交接要求，尚未发送到硬件对话','用户已批准扩展范围，并已发送到“建立 MORI 硬件开发项目”对话').replace('扩展硬件交接范围（待用户确认发送）','扩展硬件交接范围（已获批准并发送，待硬件正式交接）')
request.write_text(text)
record=dict(status='NOT_TESTED',phase='approved_source_edits_applied',utc=datetime.now(timezone.utc).isoformat(),
    revision=g['revision'],baseline=str(B.relative_to(P)),changed_ids=g['prearrival_thin_cleanup']['changed_existing_ids'],
    reaction_clamp_adopted=False,stock_soft_tyre_route_approved=True,
    hardware_request_sent=True,hardware_thread='01a0c24f-ddc2-7f03-a9d4-d09dff26d30f',
    prior_blend_sha256=hashlib.sha256((B/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest())
(S/'approval_execution.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
