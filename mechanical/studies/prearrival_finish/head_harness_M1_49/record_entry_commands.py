"""Record completed current-main entry-diagnosis commands observed by the agent."""
from pathlib import Path
import datetime,hashlib,json,platform
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
blender_jobs=[
 ('inspect_entry_sections.py','entry_sections.log','entry_topology_review/sections.json'),
 ('diagnose_body_pair.py','body_pair_diagnosis.log','entry_topology_review/closest_cam34.json'),
 ('screen_cam_staggered_entry.py','cam_staggered_entry.log','cam_staggered_entry/body_prefix_screen.json'),
 ('screen_cam_small_entry_stagger.py','cam_small_entry_stagger.log','cam_small_entry_stagger/body_prefix_screen.json'),
 ('screen_cross_order_upper.py','cam_cross_order_upper.log','cam_cross_order_upper/fan_screen.json'),
 ('pack_nine_small_entry_stagger.py','nine_small_entry_stagger.log','nine_small_entry_stagger/combined/lower_nine_screen.json'),
 ('pack_cross_order_upper.py','pack_cross_order_upper.log','cam_cross_order_upper/local_join/local_join_screen.json'),
 ('screen_lower_entry_neck.py','lower_entry_neck.log','left_lower_entry/neck_screen.json'),
 ('screen_cam_lower_entry_stagger.py','cam_lower_entry_stagger.log','cam_lower_entry_stagger/body_prefix_screen.json'),
 ('pack_nine_lower_entry_stagger.py','nine_lower_entry_stagger.log','nine_lower_entry_stagger/combined/lower_nine_screen.json'),
 ('audit_c6_attempt1.py','c6_attempt1_audit.log','c6_left_slot_entry_attempt1/audit.json'),
 ('inspect_c6_candidate.py','c6_geometry_review.log','c6_left_slot_entry/geometry_review.json'),
 ('screen_c6_left_slot_entry.py','c6_left_slot_entry.log','c6_left_slot_entry/body_prefix_screen.json'),
 ('pack_c6_lower_nine.py','pack_c6_lower_nine.log','c6_left_slot_entry/combined/lower_nine_screen.json'),
 ('render_c6_routes.py','c6_routes_render.log','c6_left_slot_entry/render_manifest.json'),
 ('inspect_upper_departures.py','upper_departures.log','upper_departure_review/departure_review.json'),
 ('screen_upper_flare_options.py','upper_flare.log','upper_flare_review/flare_screen.json'),
 ('screen_cam_rearward_loops.py','cam_rearward_loops.log','cam_rearward_loops/loop_screen.json'),
 ('check_cam_rearward_pairs.py','cam_rearward_pairs.log','cam_rearward_loops/refined_pairs.json'),
]
python_jobs=[('plot_entry_sections.py','entry_plots.log','entry_topology_review/plot_manifest.json'),
 ('plot_body_pair.py','body_pair_plot.log','entry_topology_review/pair_plot_manifest.json'),
 ('plot_c6_candidate.py','c6_section_plot.log','c6_left_slot_entry/plot_manifest.json'),
 ('plot_upper_departures.py','upper_departure_plot.log','upper_departure_review/plot_manifest.json')]
entries=[]
for kind,jobs in [('blender',blender_jobs),('python',python_jobs)]:
    for script,log,result in jobs:
        s=HERE/script;l=OUT/log;res=OUT/result
        if not res.exists():continue # Never record an unfinished or unexecuted render.
        r=json.loads(res.read_text());assert sha(s)==r['script_sha256'],script
        contents=l.read_text();assert 'Traceback' not in contents
        if kind=='blender':
            assert 'Blender quit' in contents
            argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))]
        else:argv=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(s.relative_to(ROOT))]
        entries.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
            script_sha256=sha(s),result=str(res.relative_to(ROOT)),result_sha256=sha(res),check_status=r['status']))
report=dict(status='PASS',scope='Actual completed entry-study commands. A script completing successfully does not turn BLOCKED or FAIL engineering results into PASS.',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=entries,python_version=platform.python_version(),
    main_blend_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),main_changed=False,script_sha256=sha(Path(__file__)))
(OUT/'entry_commands.json').write_text(json.dumps(report,indent=2)+'\n');print('ENTRY_COMMANDS_RECORDED',len(entries),flush=True)
