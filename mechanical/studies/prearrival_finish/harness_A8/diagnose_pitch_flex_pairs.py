"""Locate the tightest whole-bundle pair over all ten pitch states.

This does not relax the0.3mm target or select a manufacturing route. Unlike the
early-exit packing screen it evaluates every pitch for each original pair.
"""
from pathlib import Path
PAIR_DIAG_SCRIPT=Path(__file__).resolve();PAIR_DIAG_DIR=PAIR_DIAG_SCRIPT.parent
PAIR_DIAG_HELPER=PAIR_DIAG_DIR/'check_cam_pitch_flex_packing.py';__file__=str(PAIR_DIAG_HELPER)
exec(compile(PAIR_DIAG_HELPER.read_text().split('\nbody_samples={',1)[0],str(PAIR_DIAG_HELPER),'exec'),globals())
__file__=str(PAIR_DIAG_SCRIPT)
old=json.loads((OUT/'packing.json').read_text());cache={};t0=time.time()
for row in pool['rows']:
    pin=row['pin']
    for i,c in enumerate(row['candidates']):
        for p in c['poses']:
            angle=p['pitch_deg'];points=all_curves[f'pin{pin}_candidate{i}_pitch{angle}']
            tr=np.asarray(rigidtr(0,angle));tail=head_curves[f'left_slot{pin-1}']@tr[:3,:3].T+tr[:3,3]
            joined=np.vstack([points,tail[-2::-1]])
            cache[pin,i,angle]=(fine(joined),max(p['chord_error_bound_mm'],head_family['curve_error_bounds_mm'][pin-1]))
rows=[];by_pair={}
for pa,pb in itertools.combinations(range(1,5),2):
    for ia,ib in itertools.product(range(len(pool['rows'][pa-1]['candidates'])),range(len(pool['rows'][pb-1]['candidates']))):
        worst=None
        for pitch in range(-20,26,5):
            sa,ea=cache[pa,ia,pitch];sb,eb=cache[pb,ib,pitch];r=pair(sa,sb,ea,eb)
            if worst is None or r['gap_bound_mm']<worst['gap_bound_mm']:
                u,v=r['sample_indices'];worst={'pitch_deg':pitch,**r,'point_a_mm':sa[0][u].tolist(),'point_b_mm':sb[0][v].tolist()}
        row={'pins':[pa,pb],'candidates':[ia,ib],'status':worst['status'],'worst':worst}
        rows.append(row);by_pair[pa,ia,pb,ib]=row
    print('FULL_PAIR_DIAG',pa,pb,round(time.time()-t0,1),flush=True)
choices=[]
for choice in itertools.product(*(range(len(r['candidates'])) for r in pool['rows'])):
    selected=[by_pair[a,choice[a-1],b,choice[b-1]] for a,b in itertools.combinations(range(1,5),2)]
    worst=min(selected,key=lambda r:r['worst']['gap_bound_mm'])
    choices.append({'candidates':list(choice),'minimum_surface_gap_bound_mm':worst['worst']['gap_bound_mm'],'limiting_pair':worst})
best=max(choices,key=lambda r:r['minimum_surface_gap_bound_mm'])
result={'status':'PASS' if best['minimum_surface_gap_bound_mm']>=.3 else 'BLOCKED',
    'scope':'All finite-pose pair gaps and the least-tight reviewed combination; no allowance relaxation or adoption',
    'source_script_sha256':sha(PAIR_DIAG_SCRIPT),'source_helper_sha256':sha(PAIR_DIAG_HELPER),
    'source_pool_sha256':sha(OUT/'flex_pool.json'),'source_curves_sha256':sha(OUT/'flex_candidates.npz'),
    'source_main_sha256':source_hash,'required_surface_gap_mm':.3,'rows':rows,'best_combination_for_review':best,
    'main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED','elapsed_s':time.time()-t0}
(OUT/'full_pair_diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FULL_PAIR_DIAG_DONE',result['status'],best['candidates'],best['minimum_surface_gap_bound_mm'],flush=True)
