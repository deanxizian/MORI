"""Apply source 0.499999-mm bevels individually, retaining branch continuity."""
import sys,json,math,collections,subprocess,hashlib
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
kind=sys.argv[1];name,d,p,r=paths(kind);cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([sys.executable,str(H/'tools/corner_review_P5.py'),kind],check=True,capture_output=True)
rows=json.loads((r/'R14_corner_review.json').read_text())['corner_review'];log=[];b=k.LoadBoard(str(p))
def check():
 k.SaveBoard(str(p),b);subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/'bevel-native-drc.json'),str(p)],capture_output=True,check=True)
 return json.loads((r/'bevel-native-drc.json').read_text())
def hard(j):return collections.Counter(v['type']for v in j['violations']if v['type']not in['silk_over_copper','silk_overlap'])
cur=check()
for row in rows:
 if row['status']!='PASS':continue
 connected(b);net=row['net'];l=b.GetLayerID(row['layer']);v=tuple(row['vertex'])
 ts=[t for t in b.GetTracks()if not isinstance(t,k.PCB_VIA)and t.GetNetname()==net and t.GetLayer()==l and v in[xy(t.GetStart()),xy(t.GetEnd())]]
 if len(ts)!=2:continue
 a=xy(ts[0].GetEnd())if xy(ts[0].GetStart())==v else xy(ts[0].GetStart());z=xy(ts[1].GetEnd())if xy(ts[1].GetStart())==v else xy(ts[1].GetStart());la,lz=math.dist(a,v),math.dist(z,v)
 if min(la,lz)<.500001:continue
 x=tuple(v[i]+(a[i]-v[i])*.499999/la for i in range(2));y=tuple(v[i]+(z[i]-v[i])*.499999/lz for i in range(2));ps=[a,x,y,z];w=k.ToMM(ts[0].GetWidth())
 if not all(Guard(b,net).line_clear(u,t,l,w)for u,t in zip(ps,ps[1:])):continue
 before=p.read_bytes()
 for t in ts:b.Delete(t)
 track(b,net,ps,w,l);nxt=check();aa,zz=hard(nxt),hard(cur)
 if len(nxt['unconnected_items'])<=len(cur['unconnected_items'])and all(aa[t]<=zz[t]for t in aa):
  cur=nxt;log.append(dict(**row,result='PASS',new_path=ps));print(kind,'bevel',net,v,flush=True)
 else:
  p.write_bytes(before);b=k.LoadBoard(str(p));log.append({**row,'result':'NOT_APPLICABLE','reason':'Native trial would affect a nearby branch or via connection; preserved terminal geometry'})
 (r/'R14_bevel_transactions.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),trials=log),indent=2)+'\n')
cur=check();(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n')
(r/'R14_bevel_transactions.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),trials=log),indent=2)+'\n')
print(kind,'bevels accepted',sum(x['result']=='PASS'for x in log),hard(cur),len(cur['unconnected_items']))
