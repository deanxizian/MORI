"""Check the existing five-millimetre straight lead allocation on the PH path.

Bare-housing access is insufficient if its existing wire exit also clips a
part. Keep the four source exits, OD, initial straight length and 0.3 margin.
This checks only the rigid first five millimetres, not the flexible remainder.
"""
from pathlib import Path
LEAD_SCRIPT=Path(__file__).resolve();LEAD_HELPER=LEAD_SCRIPT.parent/'screen_CAM_PH_shell16_stepped_entry.py'
__file__=str(LEAD_HELPER)
exec(compile(LEAD_HELPER.read_text().split('\ntrials=[];',1)[0],str(LEAD_HELPER),'exec'),globals())
__file__=str(LEAD_SCRIPT)
OUT=STOCK_OUT/'PH_shell16_stepped_entry'
src=json.loads((OUT/'screen.json').read_text());assert src['script_sha256']==sha(LEAD_HELPER)
assert src['status']=='PASS'
states=[tuple(p) for p in src['selected']['path_states']]
rows=[];saved={};failure=None
for pin in range(1,5):
    startpoint=np.asarray(wire[pin][0]);other=np.asarray(wire[pin][1])
    assert abs(startpoint[0]-(13.5+2*pin))<1e-4,startpoint
    # The source route begins at the connector's allocated exit plane.
    assert np.linalg.norm((other-startpoint)/np.linalg.norm(other-startpoint)-[0.,0.,1.])<1e-5
    leadbox=manifold.Manifold.cube([OD+2*MARGIN,OD+2*MARGIN,5.+2*MARGIN],center=True).translate((startpoint+np.array([0.,0.,2.5])).tolist())
    one=[]
    for index,(a,b) in enumerate(zip(states[:-1],states[1:])):
        swept=manifold.Manifold.batch_hull([leadbox.translate(list(a[:3])),leadbox.translate(list(b[:3]))])
        f=collision(swept)
        row=dict(index=index,start_translation_mm=list(a[:3]),end_translation_mm=list(b[:3]),status='BLOCKED' if f else 'PASS',failure=f)
        if f:
            # Confirm a bound rejection with the exact closed-solid method;
            # box corners conservatively over-cover the round insulated lead.
            exact=exact_collision(swept)
            row['exact_padded_box_failure']=exact
            failure=f
        one.append(row)
        if f:break
    rows.append(dict(pin=pin,exit_mm=startpoint.tolist(),allocated_straight_mm=5.,status='BLOCKED' if one[-1]['failure'] else 'PASS',segments=one))
    print('PH_EXIT_LEAD',pin,rows[-1]['status'],one[-1].get('exact_padded_box_failure'),flush=True)
report=dict(status='BLOCKED' if failure else 'PASS',scope='Four five-millimetre rigid lead-exit allocations on the selected bare-housing path',
    script_sha256=sha(LEAD_SCRIPT),helper_sha256=sha(LEAD_HELPER),source_files={str((OUT/'screen.json').relative_to(PROJECT)):sha(OUT/'screen.json'),str(partial_path.relative_to(PROJECT)):sha(partial_path)},
    protected_sources=protected,rows=rows,wire_OD_mm=OD,required_margin_mm=MARGIN,
    lead_geometry='Conservative rectangular enclosure of existing OD and 5 mm straight with 0.3 mm margin; not a measured crimp profile',
    initial_mating_segment='NOT_TESTED',flexible_remaining_wire='NOT_TESTED',
    bare_housing_sweep='PASS',complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'exit_leads.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_EXIT_LEADS_DONE',report['status'],flush=True)
