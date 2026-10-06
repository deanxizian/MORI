import pcbnew as k,json
from layout_P3 import paths,xy,track,via,F,B
from route_local_P3 import connect
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/HEAD_TX','/HEAD_RX','/HEAD_OE_N','/S288_OE_N']:b.Delete(t)
jobs=[('HEAD_TX',[(21.75,26.05),(21.75,27.55)]),('HEAD_RX',[(21.25,26.05),(21.25,26.55),(20.4,27.4)]),('HEAD_OE_N',[(22.25,26.05),(22.25,26.15),(23.5,27.4)]),('HEAD_OE_N',[(15.45,10.75),(14.6,10.75),(14.1,10.25)]),('S288_OE_N',[(18.55,11.25),(19.35,11.25),(20.9,12.8),(21.4,12.8)]),('S288_OE_N',[(26.45,10.75),(26.05,10.75),(25,11.8)])]
for nn,points in jobs:via(b,nn,*points[-1],grid=False);track(b,nn,points,.2,B)
k.SaveBoard(str(p),b)
for nn,a,z,zlayers in [('HEAD_TX',(21.75,27.55),(20.07,32.74),[F,B]),('HEAD_RX',(20.4,27.4),(22.61,30.2),[F,B]),('HEAD_OE_N',(23.5,27.4),(14.1,10.25),[F]),('S288_OE_N',(21.4,12.8),(25,11.8),[F])]:
 try:connect(b,'/'+nn,a,z,[F],zlayers,(70,35),step=.05)
 except RuntimeError as e:print('BLOCKED',nn,e,flush=True)
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
