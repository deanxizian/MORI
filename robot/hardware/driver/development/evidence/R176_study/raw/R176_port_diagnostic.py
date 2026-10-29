"""Bounded native port regions and actual constraints; never a global no-fit claim."""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R176_route_screen.py').read_text()
inject=r'''
src=src.replace("rev+'-R176-'+mode", "rev+'-R176-ports-'+mode")
needle=' result=None;attempts=[]'
replacement=r"""
 from scipy import ndimage
 diagnostics=[]
 for terminal_pad in [aa,bb]:
  pname=c.pad_name(terminal_pad)
  for i,ly in enumerate(p.layers):
   if (uid(terminal_pad),ly) not in c.shapes:continue
   lab,n=ndimage.label(free[i],np.ones((3,3)))
   onpad=mask(c.shapes[uid(terminal_pad),ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   for label in np.unique(lab[onpad]):
    region=lab==label;ys,xs=np.where(region)
    options=[]
    for j,other in enumerate(p.layers):
     if i==j:continue
     accessible=region & vf & free[j]
     if REFERENCE[ly]!=REFERENCE[other]:accessible &= p.ground_near
     options.append(dict(to_layer=other,sites=int(accessible.sum())))
    positions=np.column_stack((p.xx[region],p.yy[region]))
    obstacles=[]
    # Report individual constraint coverage on the actual outward-access region.
    for (u,layer),g in c.shapes.items():
     o=c.by_id[u]
     if isinstance(o,pcb.PAD) or o.GetNetname()!=net:
      blocked_here=mask(g.buffer(.457),positions[:,0],positions[:,1])
      if blocked_here.any():obstacles.append(dict(kind='pad_or_foreign_copper',uuid=u,label=c.pad_name(o) if isinstance(o,pcb.PAD) else o.GetNetname(),layer=layer,cells=int(blocked_here.sum())))
    for q in c.keepouts:
     if q['vias']:
      blocked_here=mask(q['shape'].buffer(.257),positions[:,0],positions[:,1])
      if blocked_here.any():obstacles.append(dict(kind='native_via_keepout',name=q.get('name'),cells=int(blocked_here.sum())))
    rg=mask(p.reference_guard,positions[:,0],positions[:,1])
    obstacles.sort(key=lambda x:-x['cells'])
    diagnostics.append(dict(pad=pname,layer=ly,label=int(label),cells=int(region.sum()),bounds_mm=[float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])],transfer_options=options,reference_guard_cells=int(rg.sum()),individual_obstacles=obstacles))
 (out/(name+'-ports.json')).write_text(json.dumps(diagnostics,indent=2)+'\n')
 print(json.dumps(dict(name=name,ports=[{k:v for k,v in x.items() if k!='individual_obstacles'} for x in diagnostics])),flush=True)
 result=None;attempts=[]
"""
assert src.count(needle)==1;src=src.replace(needle,replacement)
exec(compile(src,str(__file__),'exec'))
'''
src=src.replace("exec(compile(src,str(__file__),'exec'))",inject)
exec(compile(src,str(__file__),'exec'))
