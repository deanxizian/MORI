import sys
from pathlib import Path
from scipy import ndimage
b=Path('robot/.state/c3-completion/trials')
s=(b/'R182_route.py').read_text().split('start=time.monotonic();result=')[0]
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

def connected_mask(g):
 roots=set()
 for i,ly in enumerate(p.layers):
  if ly in g['layers']:
   mm=mask(g['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
   roots.update(int(x) for x in np.unique(lookup[labs[i][mm]]) if x)
 return np.array([np.isin(lookup[lab],list(roots))&free[i] for i,lab in enumerate(labs)])
ma,mz=connected_mask(a),connected_mask(z);rows=[]
for i,ly in enumerate(p.layers):
 if not ma[i].any() or not mz[i].any():continue
 dist,indices=ndimage.distance_transform_edt(~mz[i],return_indices=True);dist[~ma[i]]=1e9
 candidates=[]
 for index in np.argsort(dist,axis=None):
  y,x=np.unravel_index(index,dist.shape)
  if dist[y,x]>100:break
  pt=(float(p.xs[x]),float(p.ys[y]));ty,tx=indices[:,y,x];end=(float(p.xs[tx]),float(p.ys[ty]));mid=Point((pt[0]+end[0])/2,(pt[1]+end[1])/2)
  if any(mid.distance(q['mid'])<1.5 for q in candidates):continue
  line=LineString([pt,end]);stroke=line.buffer(.102)
  objects=[dict(uuid=u,net=c.by_id[u].GetNetname(),kind=type(c.by_id[u]).__name__) for (u,l),g in c.shapes.items() if l==ly and c.by_id[u].GetNetname()!=net and line.intersects(g.buffer(.302))]
  kk=[k['name'] for k in c.keepouts if ly in k['layers'] and k['tracks'] and line.intersects(k['shape'].buffer(.102))]
  bodies=[f.GetReference() for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and line.intersects(fab(f).buffer(.102))] if ly in ['F.Cu','B.Cu'] else []
  reservations=[]
  for q in data['files']:
   if q['layer']==ly and q['net']!=net:
    g=from_wkb((rdir/q['path']).read_bytes())
    if line.intersects(g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.102)):reservations.append(q['net'])
  candidates.append(dict(mid=mid,layer=ly,gap_mm=float(dist[y,x]*p.grid),a=pt,z=end,physical=objects,keepouts=kk,bodies=bodies,power_reservations=reservations,reference_uncovered_mm2=stroke.difference(allowed[i].buffer(.102)).area))
  if len(candidates)==10:break
 rows.extend([{k:v for k,v in q.items() if k!='mid'} for q in candidates])
(out/'barriers.json').write_text(json.dumps(dict(source_sha256=c.sha,net=net,rows=rows),indent=2)+'\n')
for r in rows:print(json.dumps(r),flush=True)
