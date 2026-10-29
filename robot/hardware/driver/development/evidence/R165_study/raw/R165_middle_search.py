"""Recompute the UV divider transfer with native reference copper reserved.
The search is local, permits no new vias, and reserves the outward UV output
exit on In3. Existing source terminals, all keepouts and width rules remain.
The result is a proposal requiring full native refill and electrical review.
"""
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
s=(b/'R161_power_aware_search.py').read_text().split('"""',2)[2]
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('uv_middle','Net-(R1301-~-Pad1)','R1301.1','R1302.2')]"+s[end:]
old=".1,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2)"
assert s.count(old)==1;s=s.replace(old,".05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2)")
marker=" reserved={ly:unary_union"
insert=""" # Restrict the diagnostic to the detector group and preserve the UV output exit.
 region=box(63.95,24.0,69.4,31.6)
 for i,ly in enumerate(p.layers):
  allowed[i]=allowed[i].intersection(region)
  if ly=='In3.Cu':
   exit_line=LineString([[62,29.7],[64.2,29.7]])
   blocked[i]=blocked[i].union(exit_line.buffer(.405))
 vf=np.zeros(vf.shape,dtype=bool)
"""
assert s.count(marker)==1;s=s.replace(marker,insert+marker)
exec(compile(s,'R165_local_reference_constrained_middle_node','exec'))
