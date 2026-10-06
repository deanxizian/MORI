"""Export source-derived sections for the staged assembly diagnostic report."""
from pathlib import Path
SEC_SCRIPT=Path(__file__).resolve();SEC_HELPER=SEC_SCRIPT.parent/'screen_CAM_bridge_wire_stock.py'
text=SEC_HELPER.read_text().split('\nstages=',1)[0]
writer="np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})"
assert text.count(writer)==1
text=text.replace(writer,'# Read-only import; do not rewrite earlier source arrays.')
__file__=str(SEC_HELPER);exec(compile(text,str(SEC_HELPER),'exec'),globals());__file__=str(SEC_SCRIPT)
SEC_OUT=FULL/'split_assembly/review';SEC_OUT.mkdir(exist_ok=True)
rotate=np.array([[0.,1.,0.,0.],[0.,0.,1.,0.],[1.,0.,0.,0.]])
polys=lambda x:[np.asarray(p).tolist() for p in x.to_polygons()]
sections={}
for key,plane,coordinate,names in [
 ('camera_support_X6','X',6.,['Head_Front','Display_Frame']),
 ('LCD_rim_Z237_4','Z',237.4,['Head_Front','Display_PCB']),
]:
    overlap=phys[names[0]]^phys[names[1]]
    if plane=='Z' and overlap.volume()>1e-5:
        bb=np.array(overlap.bounding_box());trials=np.linspace(bb[2],bb[5],101)[1:-1]
        coordinate=max(trials,key=lambda z:overlap.slice(float(z)).area())
    assert np.isfinite(coordinate)
    s={n:polys((phys[n].transform(rotate) if plane=='X' else phys[n]).slice(coordinate)) for n in names}
    s['overlap']=polys((overlap.transform(rotate) if plane=='X' else overlap).slice(coordinate))
    sections[key]=dict(plane=plane,coordinate_mm=coordinate,polygons=s,
        intersection_mm3=max(0.,float(overlap.volume())),surface_gap_bounded_search_mm=float(phys[names[0]].min_gap(phys[names[1]],1.)))
projections={n:polys(phys[n].transform(rotate).project()) for n in ['Load_Frame','Yaw_Base','Body_Upper','Power_Module','MCU_Carrier']}
result=dict(status='PASS',scope='Exact source-solid sections and projections for diagnostic plots only',
    script_sha256=sha(SEC_SCRIPT),helper_sha256=sha(SEC_HELPER),source_main_sha256=source_hash,
    protected_sources=protected,substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    sections=sections,YZ_projections=projections,
    complete_wire_arrays_path=str((STOCK_OUT/'full_wires.npz').relative_to(PROJECT)),
    complete_wire_arrays_sha256=sha(STOCK_OUT/'full_wires.npz'),
    housing_bounds_mm=list(housing.bounding_box()),main_applied=False,manufacturing_release=False)
(SEC_OUT/'sections.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('STAGED_SUPPLY_SECTIONS PASS',flush=True)
