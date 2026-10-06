"""Repair the explicitly marked P4 motion chains; require native DRC after edits.

No board outline, signal assignment, footprint size or clearance is changed.
The rejected native projects are saved in user_review_20260923/before/.
"""
from pathlib import Path
import json, math
import pcbnew as k
from geometry_guard_P3R1 import Guard
from layout_P3R1 import track, F, B

H=Path(__file__).resolve().parents[1]
O=H/'layout_P4/user_review_20260923'
P=H/'kicad/MORI_motion_P4/MORI_motion_P4.kicad_pcb'
b=k.LoadBoard(str(P)); log=[]

def replace(label, net, ids, points, layer=B, width=.2):
    old=[t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
    if len(old)!=len(ids):
        raise RuntimeError((label, 'source changed',len(old),len(ids)))
    saved=[t.Duplicate() for t in old]
    oldlength=sum(k.ToMM(t.GetLength()) for t in old)
    for t in old:b.Delete(t)
    guard=Guard(b,net)
    clear=all(guard.line_clear(a,z,layer,width) for a,z in zip(points,points[1:]))
    if clear:
        new=track(b,net,points,width,layer)
        row=dict(region=label,net=net,removed=ids,new_uuids=[t.m_Uuid.AsString() for t in new],path_mm=points,old_length_mm=oldlength,new_length_mm=sum(math.dist(a,z) for a,z in zip(points,points[1:])),geometry_candidate='PASS',native_check='NOT_TESTED')
    else:
        for t in saved:b.Add(t)
        row=dict(region=label,net=net,geometry_candidate='FAIL',attempted_path_mm=points,source_preserved=True)
    log.append(row); print(json.dumps(row),flush=True)

replace('A / header kink','/ARM_CLK',[
    'f107995a-4b49-4c3a-9f7d-c1e5e5229d47',
    '918622b2-2355-459c-b7c5-8c41dd764da5'],
    [(9.91,4.8),(6.9,7.81),(6.9,12.35)])

replace('B / misaligned diagonal and return','/LINK_RX',[
    'df8d572f-5a5c-47e4-a64d-05b0c08ebbef',
    '34666cf4-5fb9-4297-8607-6a6eb943df75',
    'eba8dad2-26c3-417e-940e-7cd3fc7ad782',
    '82988af5-45ed-40d2-9919-322890cba8f8'],
    [(31.6065,5.2739),(34.6,8.2674),(34.6,10.25),(35.1,10.75),(35.45,10.75)])

replace('D / unnecessary reverse jog','/ARM_Q',[
    '6fedbf54-59b3-4f89-b39f-9c8ab289e0ec',
    'a494b2a6-fbe9-4be2-9471-f7db222aeede',
    'd328e0f1-1330-42de-a541-69a5abbeded9',
    '37023ae8-0a98-4521-99ec-d25fe0b554f1',
    'df6e182a-46f8-4f97-86bc-2349eba61713',
    '273eebcf-2241-4b9a-b7b8-69d7b093f82e'],
    [(38.95,15.25),(40.4,16.7),(40.4,18.2),(41.45,19.25),(41.45,20.55)])

k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P),b)
(O/'marked_chain_edits.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
