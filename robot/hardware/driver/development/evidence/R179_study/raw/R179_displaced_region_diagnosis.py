import sys
from pathlib import Path
from scipy import ndimage
b=Path('robot/.state/c3-completion/trials')
s=(b/'R179_displaced_route.py').read_text().split('start=time.monotonic();result=')[0]
exec(compile(s,'guarded_geometry','exec'))
labs=[];count=0
for f in free:
 lab,n=ndimage.label(f,np.ones((3,3)));lab[lab>0]+=count;labs.append(lab);count+=n
parent=list(range(count+1))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i in range(len(p.layers)):
 for j in range(i+1,len(p.layers)):
  mm=vf&free[i]&free[j]
  if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:mm &= p.ground_near
  for x,y in np.unique(np.column_stack([labs[i][mm],labs[j][mm]]),axis=0):parent[root(int(x))]=root(int(y))
lookup=np.array([root(i) for i in range(count+1)])
rows=[]
for g in groups:
 roots=set()
 for i,ly in enumerate(p.layers):
  if ly in g['layers']:
   mm=mask(g['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   roots.update(int(x) for x in np.unique(lookup[labs[i][mm]]) if x)
 r=dict(pads=g['pads'],layers=[])
 for i,ly in enumerate(p.layers):
  mm=np.isin(lookup[labs[i]],list(roots))&free[i];ys,xs=np.where(mm)
  vm=mm & vf;vys,vxs=np.where(vm)
  r['layers'].append(dict(layer=ly,cells=int(mm.sum()),bounds=[float(p.xs[xs.min()]),float(p.ys[ys.min()]),float(p.xs[xs.max()]),float(p.ys[ys.max()])] if len(xs) else None,via_sites=int(vm.sum()),via_positions=[[round(float(p.xs[x]),5),round(float(p.ys[y]),5)] for y,x in zip(vys,vxs)]))
 rows.append(r)
(out/'regions.json').write_text(json.dumps(dict(source_sha256=c.sha,net=net,groups=rows),indent=2)+'\n')
for row in rows: print(json.dumps(row),flush=True)
