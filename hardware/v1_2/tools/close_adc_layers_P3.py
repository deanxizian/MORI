import pcbnew as k,json
from layout_P3 import paths,xy,F,B
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));data=json.loads((r/'adc_fanout.json').read_text());log=[]
for row in data:
 try:
  result=connect(b,row['net'],row['source'],row['target'],[F,B],[F,B],(80,55),step=.1);log.append(result);k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True);log.append(dict(net=row['net'],error=str(e)))
try:log.append(connect(b,'/W_VM',(34.675,22),(48,20),[B],[F,B],(80,55),step=.1))
except RuntimeError as e:print(e,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'adc_layers.json').write_text(json.dumps(log,indent=2)+'\n')
