"""Repair inherited IMU clock reference gaps with explicit local transfer moves.

Compare only an independent native candidate. Existing pad connections, full
power widths, both ground references and all native rules remain acceptance
requirements. No component, interface, net, via padstack or circuit value moves.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R187A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
deleted=['a93c6a20-eae0-4527-86b8-95853466dda0','31b7439e-6c1d-4cea-ae06-e85607dd94ab','5238e0b6-c38f-44e4-95e6-75fd8a7c27db',
         '130145db-8b13-4841-95e4-1df81a6bb5b6','504c67a9-2a4c-425c-b4c3-c3f99e699631',
         '9bf8637a-5f8b-4375-8494-c38f014753d0','d5eb6e3a-1ff2-42ba-859f-5e4d297bd054','0b577a67-ae57-43c5-84b3-50ee8003fac9']
moves=[]
for old,new,net,reason in [([47.3,7.075],[47.3,7.4],'Net-(D1001-K)','Restore reference beneath IMU SCL while explicitly retaining the clamp/sampling B and In3 connections.'),
                           ([52.25,7.65],[52.25,7.4],'MOTION_3V3','Restore reference beneath the retained clock bend; preserve the 0.50 mm supply branch and 0.20 mm bypass branch.')]:
    v=next(v for v in c.vias if list(xy(v.GetPosition()))==old and v.GetNetname()==net)
    moves.append(dict(uuid=uid(v),source_expected=via_snapshot(c.board,v),position_mm=new,reason=reason))
def route(net,layer,pts,width=.2):return dict(net=net,layer=layer,width_mm=width,points_mm=pts)
plan=dict(revision='R187A',board_sha256=c.sha,scope=__doc__,move_vias=moves,delete_copper=deleted,
    deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
    routes=[route('/01 {slash} Core/IMU_SCL','F.Cu',[[45.84,6.5],[49.75,6.5],[50.9,7.65],[51.39,7.65]]),
            route('Net-(D1001-K)','B.Cu',[[46.9,6.675],[47.3,7.075],[47.3,7.4]]),
            route('Net-(D1001-K)','In3.Cu',[[46.575,7.8],[46.975,7.4],[47.3,7.4]]),
            route('MOTION_3V3','B.Cu',[[52.25,5.9],[52.25,7.4]]),
            route('MOTION_3V3','B.Cu',[[52.25,7.4],[52.45,7.6],[52.45,11.875]],.5)])
out.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(revision='R187A',retired_tracks=len(deleted),moved_non_GND_vias=len(moves))))
