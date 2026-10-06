"""Reconnect current native DRC airwires on logic boards, obeying body zones.

Power main paths must be repaired with their original width; this helper
deliberately refuses the power board.
"""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,track,via,F,B
from route_local_P3R1 import connect
from geometry_guard_P3R1 import Guard
from close_routes_P2 import merge_lines
kind=sys.argv[1];assert kind in ['motion','imu'];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());items={}
for f in b.GetFootprints():
    for pad in f.Pads():items[pad.m_Uuid.AsString()]=pad
for t in b.GetTracks():items[t.m_Uuid.AsString()]=t
size={'imu':(20,16),'motion':(70,35)}[kind]
def coords(z):return [xy(z.GetStart()),xy(z.GetEnd())] if isinstance(z,k.PCB_TRACK) and not isinstance(z,k.PCB_VIA) else [xy(z.GetPosition())]
def layers(z):return [l for l in [F,B] if z.IsOnLayer(l)]
log=[]
for index,row in enumerate(j['unconnected_items']):
    a,z=[items.get(q['uuid']) for q in row['items']]
    if a is None or z is None:
        pad=a or z
        if pad is None or pad.GetNetname()!='/GND':continue
        pos=coords(pad)[0];g=Guard(b,'/GND')
        # Avoid long ground detours: one local stitch beyond the body/pads.
        done=False
        for layer in layers(pad):
            for distance,end,route in g.portals(pos,layer,radius=3,step=.2):
                if not .91<end[0]<size[0]-.91 or not .91<end[1]<size[1]-.91:continue
                track(b,'/GND',route,.2,layer);via(b,'/GND',*end,grid=False)
                log.append(dict(index=index,status='LOCAL_GROUND_STITCH',start=pos,end=end));done=True;break
            if done:break
        if not done:log.append(dict(index=index,status='BLOCKED_GROUND',position=pos))
    else:
        choices=sorted((math.dist(aa,zz),aa,zz) for aa in coords(a) for zz in coords(z))
        for _,aa,zz in choices:
            try:
                result=connect(b,str(a.GetNetname()),aa,zz,layers(a),layers(z),size,step=.05)
                log.append(dict(index=index,status='ROUTED',**result));break
            except RuntimeError as exc:reason=str(exc)
        else:log.append(dict(index=index,status='BLOCKED',reason=reason));print('BLOCKED',index,reason,flush=True)
    k.SaveBoard(str(p),b)
    (r/'reconnections.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
merge_lines(b)
# Exact endpoints on existing and new vias; small grid-rounding differences
# must not leave a trace connected only to the rim of a via.
vias=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA)]
for t in list(b.GetTracks()):
    if isinstance(t,k.PCB_VIA):continue
    for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
        near=[v for v in vias if v.GetNetCode()==t.GetNetCode() and (v.GetPosition()-get()).EuclideanNorm()<k.FromMM(.04)]
        if near:setter(near[0].GetPosition())
    if t.GetLength()<k.FromMM(.005):b.Delete(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
print(name,'reconnection attempts',len(log),flush=True)
