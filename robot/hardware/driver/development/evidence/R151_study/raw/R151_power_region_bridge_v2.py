"""Extend the region screen with exact existing anchor terminals.

The original all-interior terminal rule erased 0.50 mm via lands when seeking
0.50 mm copper. Real, already plated via centres and actual pad lands may also
be terminals; native physical/reference screening remains in force. An explicit
wide_vias mode additionally screens 0.80/0.30 mm new power vias conservatively.
No proposal is an adoption or an ampacity qualification.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R151_power_region_bridge.py').read_text()
old="node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')"
new="""# Add exact anchor-centre terminals without requiring a fictitious larger land.
for i,group in enumerate(ids):
    for ly in p.layers:
        extra=[Point(xy(c.by_id[u].GetPosition())).buffer(.039) for u in group if (u,ly) in c.shapes]
        gs[i]['layers'][ly]=gs[i]['layers'][ly].union(unary_union(extra))
"""+old
assert code.count(old)==1;code=code.replace(old,new)
old="rows=[]\nfor i,g in enumerate(gs):"
new="""use_wide_vias=len(sys.argv)>5 and sys.argv[5]=='wide_vias'
via_mask=np.zeros(vf.shape,dtype=bool)
if use_wide_vias:
    # Expanding every original 0.50 mm obstruction by 0.15 mm is conservative
    # for a 0.80 mm annulus; the plated drill remains 0.30 mm.
    via_block=p.via_common.buffer(.15).union(unary_union([s.buffer(.607) for (u,l),s in c.shapes.items() if c.by_id[u].GetNetname()!=net and not isinstance(c.by_id[u],pcb.PAD)]))
    via_mask=~mask(via_block,p.xx,p.yy)
rows=[]
for i,g in enumerate(gs):"""
assert code.count(old)==1;code=code.replace(old,new)
old="result=p.solve(g,h,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),500000)"
new="""result=p.solve(g,h,(free,via_mask,blocked,allowed),500000)
        if result['status']=='PROPOSAL':
            for v in result['vias']:v['diameter_mm']=.8
        result['new_via_policy']='0.80/0.30 mm conservative search' if use_wide_vias else 'No new vias'
        result['endpoint_policy']='Actual wide region interiors plus existing plated anchor centres; exact centre attachment still required before building'"""
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace('No vias or PCB mutations are introduced by this proposal search.','Existing anchor terminals added. Optional wide_vias mode screens 0.80/0.30 mm new vias; no PCB mutation. Endpoints still require exact reconstruction.')
exec(compile(code,str(__file__),'exec'))
