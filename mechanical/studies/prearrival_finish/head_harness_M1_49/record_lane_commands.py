"""Record completed commands observed in this continuation, without rerunning them."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=[]
jobs=[
 ('screen_cam_lane_swap.py','cam_lane_swap.log','cam_lane_swap/body_prefix_screen.json',False),
 ('pack_nine_lane_swap.py','pack_nine_lane_swap.log','nine_lane_swap/combined/lower_nine_screen.json',False),
 ('diagnose_cam_swap_pair.py','cam_swap_pair_diagnosis.log','CAM_swap_pair_diagnosis.json',True),
 ('diagnose_cam_same_heading.py','cam_same_heading.log','cam_same_heading_diagnosis.json',True),
 ('screen_stagger_neck.py','stagger_neck.log','stagger_neck/neck_screen.json',False),
 ('screen_stagger_neck_clear.py','stagger_neck_clear.log','stagger_neck_clear/neck_screen.json',False),
 ('screen_stagger_neck_spk26.py','stagger_neck_spk26.log','stagger_neck_spk26/neck_screen.json',False),
 ('screen_stagger_neck_spk26_phase2.py','stagger_neck_spk26_phase2.log','stagger_neck_spk26_phase2/neck_screen.json',False),
 ('render_stagger_neck.py','stagger_neck_render.log','stagger_neck_spk26_phase2/render_manifest.json',False),
 ('screen_cam_height_entry.py','cam_height_entry.log','cam_height_entry/body_prefix_screen.json',False),
 ('pack_nine_height_entry.py','pack_nine_height_entry.log','nine_height_entry/combined/lower_nine_screen.json',False),
 ('screen_cam_left_neck.py','cam_left_neck.log','cam_left_bank/neck_screen.json',False),
 ('screen_cam_left_front_neck.py','cam_left_front_neck.log','cam_left_front_bank/neck_screen.json',False),
 ('render_cam_left_front_neck.py','cam_left_front_neck_render.log','cam_left_front_bank/render_manifest.json',False),
 ('screen_cam_left_front_prefix.py','cam_left_front_prefix.log','cam_left_front_prefix/body_prefix_screen.json',False),
 ('pack_nine_left_front.py','pack_nine_left_front.log','nine_left_front/combined/lower_nine_screen.json',False),
 ('rebuild_left_pin_order.py','left_pin_order.log','cam_left_pin_order/body_prefix_screen.json',False),
 ('pack_nine_left_order.py','pack_nine_left_order.log','nine_left_order/combined/lower_nine_screen.json',False),
 ('rebuild_cam_four_order.py','cam_four_order.log','cam_four_order/body_prefix_screen.json',False),
 ('pack_nine_four_order.py','pack_nine_four_order.log','nine_four_order/combined/lower_nine_screen.json',False),
 ('screen_cam_four_order_expanded.py','cam_four_order_expanded.log','cam_four_order_expanded/body_prefix_screen.json',False),
 ('pack_nine_four_order_expanded.py','pack_nine_four_order_expanded.log','nine_four_order_expanded/combined/lower_nine_screen.json',False),
 ('screen_four_order_upper.py','cam_four_order_upper.log','cam_four_order_upper/fan_screen.json',False),
 ('pack_four_order_upper.py','pack_four_order_upper.log','cam_four_order_upper/local_join/local_join_screen.json',False),
 ('screen_diverse_four_order_upper.py','cam_four_order_upper_diverse.log','cam_four_order_upper_diverse/fan_screen.json',False),
 ('pack_diverse_four_order_upper.py','pack_diverse_four_order_upper.log','cam_four_order_upper_diverse/local_join/local_join_screen.json',False),
 ('screen_left_tall_entry.py','left_tall_entry.log','left_tall_entry/neck_screen.json',False),
 ('screen_left_tall_entry_clear.py','left_tall_entry_clear.log','left_tall_entry_clear/neck_screen.json',False),
 ('refine_tall_speaker_lane.py','tall_speaker_lane_refinement.log','left_tall_entry_refined/neck_screen.json',False),
 ('screen_left_tall_entry_dip.py','left_tall_entry_dip.log','left_tall_entry_dip/neck_screen.json',False),
 ('diagnose_tall_neck_clearance.py','tall_neck_clearance_diagnosis.log','tall_neck_clearance_diagnosis.json',False),
 ('screen_left_tall_balanced.py','left_tall_balanced.log','left_tall_balanced/neck_screen.json',False),
 ('render_left_tall_balanced.py','left_tall_balanced_render.log','left_tall_balanced/render_manifest.json',False),
 ('rebuild_cam_four_tall_entry.py','cam_four_tall_entry.log','cam_four_tall_entry/body_prefix_screen.json',False),
 ('screen_cam_four_tall_directed.py','cam_four_tall_directed.log','cam_four_tall_directed/body_prefix_screen.json',False),
]
for script,log,result,factory in jobs:
    s=HERE/script;l=OUT/log;res=OUT/result;r=json.loads(res.read_text())
    assert sha(s)==r['script_sha256'],script
    assert 'Blender quit' in l.read_text(),log
    argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background']
    argv+=['--factory-startup'] if factory else ['mechanical/mori_v1_2.blend']
    argv+=['-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))]
    entries.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
        script_sha256=sha(s),result=str(res.relative_to(ROOT)),result_sha256=sha(res),check_status=r['status']))
s=HERE/'receive_wire_evidence.py';l=OUT/'hardware_wire_receipt.log';res=OUT/'hardware_wire_evidence_receipt.json'
r=json.loads(res.read_text());assert sha(s)==r['script_sha256'];assert 'HARDWARE_WIRE_RECEIPT 75 254' in l.read_text()
entries.append(dict(argv=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(s.relative_to(ROOT))],cwd=str(ROOT),exit_code=0,
    log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),result=str(res.relative_to(ROOT)),result_sha256=sha(res),check_status=r['status']))
report=dict(status='PASS',scope='Actual completed commands; each result retains its limited PASS/BLOCKED scope',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=entries,
    main_blend_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),main_changed=False,script_sha256=sha(Path(__file__)))
(OUT/'lane_height_commands.json').write_text(json.dumps(report,indent=2)+'\n')
print('LANE_COMMANDS_RECORDED',len(entries),flush=True)
