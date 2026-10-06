from pathlib import Path
REVIEW=Path(__file__).resolve().parent
base=(REVIEW/'body_routes_current.py').read_text().split('prior=json.loads')[0]
exec(compile(base,str(REVIEW/'body_routes_current.py'),'exec'),globals())
reports=['body_routes_current.json','imu_piecewise_routes.json']
out=[]
for file in reports:
 d=json.loads((REVIEW/file).read_text())
 for r in d.get('routes',d.get('attempts',[])):
  c=r.get('closest_candidate')
  if not c:continue
  p=np.array(c.get('first_blocked',c.get('first_blocked_point_mm')));near=[]
  for n,t in trees.items():
   pos,norm,face,dist=t.find_nearest(Vector(p))
   if dist<5:near.append(dict(id=n,distance_mm=dist,inside=(Vector(p)-pos).dot(norm)<-.0001))
  out.append(dict(file=file,id=r['id'],point=p.tolist(),near=sorted(near,key=lambda t:t['distance_mm'])))
(REVIEW/'route_obstacle_probe.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
