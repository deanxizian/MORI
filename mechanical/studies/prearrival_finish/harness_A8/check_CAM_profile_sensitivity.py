"""Bound a small stated profile uncertainty; this is not tool metrology."""
from pathlib import Path
PS_SCRIPT=Path(__file__).resolve();PS_ROOT=PS_SCRIPT.parent
PS_HELPER=PS_ROOT/'check_CAM_two_anchor_tool_access.py';__file__=str(PS_HELPER)
exec(compile(PS_HELPER.read_text().split('\nta_rows=[];',1)[0],str(PS_HELPER),'exec'),globals())
__file__=str(PS_SCRIPT)
PS_OUT=PS_ROOT/'cam_profiled_tool';ps_rows=[]
ps_sets={
 'reference':PT_STATIONS,
 'expanded_transition':[(0.,15.,9.5),(17.,15.,9.5),(25.,22.,11.),(42.,40.,22.),(69.,64.,22.),(125.,64.,22.)]}
for name,stations in ps_sets.items():
    sweep=pt_sections(stations,60.)
    for angle in [30.,45.]:
        m=sweep.translate((-st_pivot).tolist()).rotate([0.,angle,0.]).translate(st_pivot.tolist())
        fixture=st_hits(m,ta_targets);wire=st_wire_hits(m,0.)
        row={'case':name,'angle_deg':angle,'stations':stations,'fixture':fixture,'wires':wire,
             'status':'PASS' if fixture['status']==wire['status']=='PASS' else 'BLOCKED'}
        if row['status']=='PASS':
            row['wire_minimum']=ta_wire_minimum(m)
            row['rigid_without_ties']=st_hits(m,{n:t for n,t in ta_targets.items() if n not in ['CAM_Tie_Head','CAM_Tie_Band','CAM_connector_tie_head','CAM_connector_tie_band']})
            assert row['wire_minimum']['status']=='PASS'
        ps_rows.append(row);print('PROFILE_SENSITIVITY',name,angle,row['status'],row.get('wire_minimum'),flush=True)
ps_record={'status':'PASS' if all(r['status']=='PASS' for r in ps_rows) else 'BLOCKED','scope':'Four stated envelope cases only; blade datum and 0.25 mm tie-face offset retained',
    'source_main_sha256':source_hash,'script_sha256':sha(PS_SCRIPT),'helper_sha256':sha(PS_HELPER),'rows':ps_rows,
    'assumed_perturbation':'Profile widths +2 mm, depth +2 mm, non-tip/non-end stations begin 3 mm nearer the tip; no certified uncertainty range inferred from photographs',
    'vendor_tool_fit':'NOT_TESTED','main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED'}
(PS_OUT/'sensitivity.json').write_text(json.dumps(ps_record,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PROFILE_SENSITIVITY_DONE',ps_record['status'],flush=True)
