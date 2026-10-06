"""Check the two small tail angles left feasible by the surface diagnosis."""
from pathlib import Path
SMALL16_SCRIPT=Path(__file__).resolve()
SMALL16_HELPER=SMALL16_SCRIPT.parent/'screen_shell16_refined_tail_splay.py'
small_text=SMALL16_HELPER.read_text();small_prefix,small_run=small_text.split('\ntrials=[];',1)
__file__=str(SMALL16_HELPER)
exec(compile(small_prefix,str(SMALL16_HELPER),'exec'),globals())
__file__=str(SMALL16_SCRIPT)
REFINE16_SCRIPT=SMALL16_SCRIPT
OUT=ORDER_OUT/'shell16_small_tail_splay';OUT.mkdir(exist_ok=True)
assert small_run.count('for splay_angle in [4.,5.,6.,-4.]:')==1
small_run=small_run.replace('for splay_angle in [4.,5.,6.,-4.]:','for splay_angle in [3.,3.5]:')
exec(compile('trials=[];'+small_run,str(SMALL16_HELPER),'exec'),globals())
report['search_helper_sha256']=sha(SMALL16_HELPER)
report['surface_diagnosis_sha256']=sha(ORDER_OUT/'shell16_splay_clearance/diagnosis.json')
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
