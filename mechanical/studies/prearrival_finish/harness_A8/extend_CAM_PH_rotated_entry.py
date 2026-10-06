"""Continue the alternative body-plug assembly investigation with a real budget.

The old search stopped at 272 states with an unsearched frontier, so its result
does not eliminate late connection as an alternative to moving attached wires.
Keep the exact same goal, bodies, wire obstacles, envelope and 0.3 mm margin.
"""
from pathlib import Path
EXTENDPH_SCRIPT=Path(__file__).resolve()
EXTENDPH_HELPER=EXTENDPH_SCRIPT.parent/'plan_CAM_PH_rotated_entry_fast.py'
marker="\nexec(compile('started=time.time();expanded=0;'+run"
__file__=str(EXTENDPH_HELPER)
exec(compile(EXTENDPH_HELPER.read_text().split(marker,1)[0],str(EXTENDPH_HELPER),'exec'),globals())
__file__=str(EXTENDPH_SCRIPT)
ROT_SCRIPT=EXTENDPH_SCRIPT
ROT_OUT=STOCK_OUT/'PH_rotated_entry_extended';ROT_OUT.mkdir(exist_ok=True)
assert run.count('time.time()-started<150')==1
assert run.count('time_budget_s=150')==1
run=run.replace('time.time()-started<150','time.time()-started<600')
run=run.replace('time_budget_s=150','time_budget_s=600')
run=run.replace('expanded%250==0','expanded%100==0')
exec(compile('started=time.time();expanded=0;'+run,str(FAST_BASE),'exec'),globals())
report.update(optimizer_base_sha256=sha(FAST_BASE),search_helper_sha256=sha(EXTENDPH_HELPER),
    collision_method='Unchanged convex containment and BVH screening with sampled exact Boolean checks',
    exact_boolean_audits=exact_audits,convex_queries=convex_queries,
    historical_comparison='Previous same search stopped after 150 seconds; no impossibility inference')
(ROT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('EXTENDED_PH_DONE',report['status'],report['expanded_nodes'],len(exact_audits),flush=True)
