"""Receipts for completed upper-connection study jobs, never planned commands."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
jobs=[
 ('screen_cam_rearward_fans.py',['--case','rear3'],'cam_rear3_fans.log','cam_rearward_fans/rear3/fan_screen.json'),
 ('pack_cam_rearward_fans.py',['--case','rear3'],'pack_cam_rear3_fans.log','cam_rearward_fans/rear3/local_join/local_join_screen.json'),
 ('screen_cam_aligned_pin1.py',[],'cam_aligned_pin1.log','cam_rearward_fans/rear3_aligned/fan_screen.json'),
 ('pack_cam_aligned_fans.py',['--case','rear3'],'pack_cam_aligned_fans.log','cam_rearward_fans/rear3_aligned/local_join/local_join_screen.json'),
 ('screen_cam_multistage_fans.py',[],'cam_multistage_fans.log','cam_rearward_fans/rear3_multistage/fan_screen.json'),
 ('pack_cam_multistage_fans.py',['--case','rear3'],'pack_cam_multistage_fans.log','cam_rearward_fans/rear3_multistage/local_join/local_join_screen.json'),
 ('screen_cam_deeper_fans.py',['--case','rear7'],'cam_rear7_multistage_fans.log','cam_rearward_fans/rear7_multistage/fan_screen.json'),
 ('pack_cam_multistage_fans.py',['--case','rear7'],'pack_cam_rear7_multistage_fans.log','cam_rearward_fans/rear7_multistage/local_join/local_join_screen.json'),
 ('join_c6_cam_upper.py',['--family','rear7_multistage'],'join_c6_cam_rear7.log','cam_rearward_fans/rear7_multistage/c6_join/join_review.json'),
 ('screen_cam_outlet_steering.py',[],'cam_outlet_steering.log','neck_outlet_steering/neck_screen.json'),
 ('screen_cam_outlet_offset.py',[],'cam_outlet_offset.log','neck_outlet_offset/neck_screen.json'),
 ('screen_rear_outlet_neck.py',[],'rear_outlet_neck.log','rear_outlet_neck/neck_screen.json'),
 ('screen_rear_direct_neck.py',[],'rear_direct_neck.log','rear_direct_neck/neck_screen.json'),
 ('screen_rear_late_neck.py',[],'rear_late_neck.log','rear_late_neck/neck_screen.json'),
 ('screen_rear_separated_neck.py',[],'rear_separated_neck.log','rear_separated_neck/neck_screen.json'),
 ('review_rear_outlet_conflict.py',[],'rear_outlet_review.log','rear_separated_neck/review/review.json'),
 ('screen_rear_power_delayed.py',[],'rear_power_delayed.log','rear_power_delayed/neck_screen.json'),
 ('screen_rear_power_separation.py',[],'rear_power_separation.log','rear_power_separation/neck_screen.json'),
 ('screen_rear_power_bump.py',[],'rear_power_bump.log','rear_power_bump/neck_screen.json'),
 ('review_rear_power_clearance.py',[],'rear_power_clearance_review.log','rear_power_bump/review/review.json'),
 ('screen_cam_compensated_loops.py',[],'cam_compensated_loops.log','cam_compensated_loops/loop_screen.json'),
 ('refine_cam_compensated_conflicts.py',[],'cam_compensated_refinement.log','cam_compensated_loops/refined_pairs.json'),
 ('screen_cam_rear_return.py',[],'cam_rear_return.log','cam_rear_return/loop_screen.json'),
 ('screen_cam_side_return.py',[],'cam_side_return.log','cam_side_return/tail_screen.json'),
 ('screen_cam_oblique_return.py',[],'cam_oblique_return.log','cam_oblique_return/tail_screen.json'),
 ('screen_neck_side_tail_join.py',[],'neck_side_tail_join.log','neck_side_tail_join/join_screen.json'),
 ('screen_neck_side_tail_gentle.py',[],'neck_side_tail_gentle.log','neck_side_tail_gentle/join_screen.json'),
 ('screen_cam_side_service.py',[],'cam_side_service.log','cam_side_service/loop_screen.json'),
 ('screen_cam_side_following.py',[],'cam_side_following.log','cam_side_following/loop_screen.json'),
 ('verify_partitioned_self.py',[],'self_partition_verification.log','self_partition_verification.json'),
 ('review_side_cam_layout.py',[],'side_cam_review.log','side_cam_review/review.json'),
 ('screen_cam_side_fans.py',[],'cam_side_fans.log','cam_side_fans/fan_screen.json'),
 ('join_c6_side_cam.py',[],'join_c6_side_cam.log','cam_side_fans/c6_join/join_review.json'),
 ('review_c6_side_cam.py',[],'review_c6_side_cam.log','cam_side_fans/c6_join/review/review.json'),
 ('inspect_cam_restraint_sites.py',[],'cam_restraint_sites.log','cam_restraints/site_inventory.json'),
 ('audit_cam_material_stations.py',[],'cam_material_stations.log','cam_restraints/material_stations.json'),
 ('check_cam_connector_restraint.py',[],'cam_connector_restraint.log','cam_restraints/connector/review.json'),
 ('check_cam_sliding_guide.py',[],'cam_sliding_guide.log','cam_restraints/sliding_guide/review.json'),
 ('inspect_restraint_conflicts.py',[],'restraint_conflict_locations.log','cam_restraints/conflict_locations.json'),
 ('screen_cam_restraint_positions.py',[],'cam_restraint_positions.log','cam_restraints/position_screen/review.json'),
 ('check_cam_sliding_guide_v2.py',[],'cam_sliding_guide_v2.log','cam_restraints/sliding_guide_v2/review.json'),
 ('locate_restraint_minima.py',[],'restraint_minima.log','cam_restraints/minima.json'),
 ('check_cam_sliding_guide_v3.py',[],'cam_sliding_guide_v3.log','cam_restraints/sliding_guide_v3/review.json'),
 ('check_cam_sliding_guide_v4.py',[],'cam_sliding_guide_v4.log','cam_restraints/sliding_guide_v4/review.json'),
 ('screen_cam_clamp_power_clearance.py',[],'cam_clamp_power_clearance.log','cam_restraints/power_clearance/review.json'),
 ('screen_cam_clamp_power_clearance_v2.py',[],'cam_clamp_power_clearance_v2.log','cam_restraints/power_clearance_v2/review.json'),
 ('screen_cam_clamp_power_clearance_v3.py',[],'cam_clamp_power_clearance_v3.log','cam_restraints/power_clearance_v3/review.json'),
 ('check_cam_guide_terminal_gate.py',[],'cam_guide_terminal_gate.log','cam_restraints/terminal_gate/review.json'),
 ('check_cam_guide_terminal_gate_v2.py',[],'cam_guide_terminal_gate_v2.log','cam_restraints/terminal_gate_v2/review.json'),
 ('check_cam_return_clamp.py',[],'cam_return_clamp.log','cam_restraints/return_clamp/review.json'),
 ('check_cam_return_clamp_v2.py',[],'cam_return_clamp_v2.log','cam_restraints/return_clamp_v2/review.json'),
 ('check_cam_return_clamp_v3.py',[],'cam_return_clamp_v3.log','cam_restraints/return_clamp_v3/review.json'),
 ('audit_cam_return_clamp_material.py',[],'cam_return_material_stations.log','cam_restraints/return_material_stations.json'),
 ('check_cam_restraint_tools_current.py',[],'cam_restraint_tools_current.log','cam_restraints/tool_access/review.json'),
 ('check_cam_restraint_tool_angles.py',[],'cam_restraint_tool_angles.log','cam_restraints/tool_angles/review.json'),
 ('check_cam_restraint_tool_angles_extended.py',[],'cam_restraint_tool_angles_extended.log','cam_restraints/tool_angles_extended/review.json'),
 ('review_cam_restraints.py',[],'cam_restraint_review.log','cam_restraints/review/review.json'),
 ('review_cam_restraints_clear.py',[],'cam_restraint_review_clear.log','cam_restraints/review_clear/review.json'),
 ('review_cam_restraints_parts.py',[],'cam_restraint_review_parts.log','cam_restraints/review_parts/review.json'),
 ('check_cam_return_clamp_high.py',[],'cam_return_clamp_high.log','cam_restraints/return_clamp_high/review.json'),
 ('check_cam_restraint_tools_high.py',[],'cam_restraint_tools_high.log','cam_restraints/tool_high/review.json'),
 ('check_cam_bench_preassembly.py',[],'cam_bench_preassembly.log','cam_restraints/bench_preassembly/review.json'),
 ('check_cam_bench_preassembly_v2.py',[],'cam_bench_preassembly_v2.log','cam_restraints/bench_preassembly_v2/review.json'),
 ('check_cam_bench_transfer.py',[],'cam_bench_transfer.log','cam_restraints/bench_transfer/review.json'),
 ('check_cam_PH_guide_gate.py',[],'cam_PH_guide_gate.log','cam_restraints/PH_terminal_gate/review.json'),
 ('review_cam_bench_sequence.py',[],'cam_bench_review.log','cam_restraints/bench_review/review.json'),
 ('review_cam_bench_sequence_clear.py',[],'cam_bench_review_clear.log','cam_restraints/bench_review_clear/review.json'),
 ('screen_cam_threading_formation.py',[],'cam_threading_formation.log','cam_restraints/threading_formation/review.json'),
 ('screen_cam_threading_formation_v2.py',[],'cam_threading_formation_v2.log','cam_restraints/threading_formation_v2/review.json'),
 ('screen_cam_threading_descent.py',[],'cam_threading_descent.log','cam_restraints/threading_descent/review.json'),
 ('screen_cam_contact_corridor.py',[],'cam_contact_corridor.log','cam_restraints/contact_corridor/review.json'),
 ('screen_cam_contact_corridor_inward.py',[],'cam_contact_corridor_inward.log','cam_restraints/contact_corridor_inward/review.json'),
 ('review_cam_threading.py',[],'cam_threading_review.log','cam_restraints/threading_review/review.json'),
 ('check_reaction_assembly_current.py',[],'reaction_current.log','reaction_current/review.json'),
]
entries=[]
for script,args,log,result in jobs:
    s=HERE/script;l=OUT/log;p=OUT/result
    if not p.exists():continue
    r=json.loads(p.read_text());assert sha(s)==r['script_sha256'],script
    content=l.read_text();assert 'Blender quit' in content and 'Traceback' not in content
    argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))]
    if args:argv+=['--']+args
    entries.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),
        result=str(p.relative_to(ROOT)),result_sha256=sha(p),check_status=r['status']))
receipt=OUT/'CAM_PH_RECEIPT.json';receipt_script=HERE/'receive_cam_ph_reconciliation.py';receipt_log=OUT/'cam_ph_receipt.log'
if receipt.exists() and receipt_log.exists():
    rr=json.loads(receipt.read_text());assert rr['script_sha256']==sha(receipt_script)
    assert 'CAM_PH_RECEIVED CAM-PH-RECON-R1 62' in receipt_log.read_text() and 'Traceback' not in receipt_log.read_text()
    entries.append(dict(argv=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(receipt_script.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(receipt_log.relative_to(ROOT)),log_sha256=sha(receipt_log),script_sha256=sha(receipt_script),
        result=str(receipt.relative_to(ROOT)),result_sha256=sha(receipt),check_status=rr['status']))
r=dict(status='PASS',scope='Completed recorded jobs only; command success does not override a BLOCKED engineering result',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=entries,main_changed=False,
    main_blend_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),script_sha256=sha(Path(__file__)))
(OUT/'upper_connection_commands.json').write_text(json.dumps(r,indent=2)+'\n');print('UPPER_CONNECTION_COMMANDS',len(entries),flush=True)
