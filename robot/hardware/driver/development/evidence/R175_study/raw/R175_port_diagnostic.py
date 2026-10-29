"""Identify endpoint access regions in the exact supply-guarded geometry.

This is a bounded diagnostic, not a proof of global impossibility. It records
whether each native pad can reach any geometrically allowed layer transfer.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_guarded_loops_expanded.py').read_text()
src=src.replace("rev+'-R175-guarded-loops'", "rev+'-R175-port-diagnostic'")
start=src.index('tasks=[');end=src.index('\nrows=[]',start)
src=src[:start]+"tasks=[('ina_input_plus','R1706.2','U1701.1'),('supervisor_gnd','C1304.2','U1302.2')]"+src[end:]
old=' result=None;attempts=[]'
new='''
 from scipy import ndimage
 diagnostics=[]
 for terminal in [a,z]:
  for i,ly in enumerate(p.layers):
   if ly not in terminal['layers']:continue
   lab,n=ndimage.label(free[i],np.ones((3,3)))
   onpad=mask(terminal['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   for label in np.unique(lab[onpad]):
    region=lab==label;ys,xs=np.where(region)
    vias=[]
    for j,other in enumerate(p.layers):
     if i==j:continue
     accessible=region & vf & free[j]
     if REFERENCE[ly]!=REFERENCE[other]:accessible &= p.ground_near
     vias.append(dict(to_layer=other,sites=int(accessible.sum())))
    diagnostics.append(dict(pads=terminal['pads'],layer=ly,label=int(label),cells=int(region.sum()),bounds_mm=[float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])],transfer_options=vias))
 (out/(name+'-ports.json')).write_text(json.dumps(diagnostics,indent=2)+'\\n')
 print(json.dumps(dict(name=name,endpoint_regions=diagnostics)),flush=True)
 result=None;attempts=[]
'''
assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))
