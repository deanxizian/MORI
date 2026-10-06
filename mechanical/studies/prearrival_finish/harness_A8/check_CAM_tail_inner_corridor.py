"""Check the gap identified in the exact Z212 sections, inside the yoke wall."""
from pathlib import Path
TI_SCRIPT=Path(__file__).resolve();TI_ROOT=TI_SCRIPT.parent
TI_HELPER=TI_ROOT/'check_CAM_tail_ribbon_access.py';__file__=str(TI_HELPER)
exec(compile(TI_HELPER.read_text().split('\ntr_rows=[];',1)[0],str(TI_HELPER),'exec'),globals())
__file__=str(TI_SCRIPT)
ti_rows=[];ti_arrays={};ti_ok=[];ti_started=time.time()
for radius,first,column in itertools.product([3.,4.,5.],[1.,2.,3.,4.],[-33.,-34.,-35.]):
    m,p,meta=tr_shape(first,radius,column);i=len(ti_rows)
    fixture=st_hits(m,tr_targets)
    wire=st_wire_hits(m,0.) if fixture['status']=='PASS' else {'status':'NOT_TESTED'}
    row={'candidate':i,**meta,'fixture':fixture,'wires':wire,
         'status':'PASS' if fixture['status']==wire['status']=='PASS' else 'BLOCKED'}
    ti_rows.append(row)
    if row['status']=='PASS':
        ti_ok.append(i);cache(TR_OUT/f'inner_tail_{i}.npz',m);ti_arrays[f'inner_tail_{i}']=p
    print('INNER_TAIL',i,row['status'],radius,first,column,
          [h['object'] for h in fixture['hits']],wire,flush=True)
np.savez_compressed(TR_OUT/'inner_centerlines.npz',**ti_arrays)
ti_result={'status':'PASS' if ti_ok else 'BLOCKED',
    'scope':'Temporary CAM free-tail shape through the gap between pitch servo and yoke side wall, at fixed mechanical zero',
    'source_main_sha256':source_hash,'script_sha256':sha(TI_SCRIPT),'helper_sha256':sha(TI_HELPER),
    'source_sections_sha256':sha(TR_OUT/'sections.json'),
    'start_mm':tr_start.tolist(),'band_width_upper_mm':tr_width,'band_thickness_upper_mm':tr_thickness,
    'rows':ti_rows,'passed':ti_ok,'fixture_ids':list(tr_targets),'not_yet_fitted':wi_excluded,
    'assumed_easy_axis_shape':True,'bend_material_qualification':'NOT_TESTED',
    'full_threading_and_tightening':'NOT_TESTED','wire_forming':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
    'elapsed_s':time.time()-ti_started}
(TR_OUT/'inner_corridor.json').write_text(json.dumps(ti_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('INNER_TAIL_DONE',ti_result['status'],ti_ok,flush=True)
