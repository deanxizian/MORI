"""Conservative candidates for the seven inherited return-path flags.

No files are modified. Candidates avoid all existing non-ground copper (including
power pours), pad physical clearance, rule areas and board edges. Native DRC and
post-refill regression still required before adoption.
"""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import box
from shapely.prepared import prep
from copper_geometry import *


def suggest(board, out):
    c = Copper(board)
    ev = Path(__file__).resolve().parents[2] / 'evidence/R108P/transition_audit.json'
    flags = [r for r in json.loads(ev.read_text())['vias'] if r['reference_change_screen']=='FAIL']
    obstacles = []
    # Physical pad spacing applies even to ground pads. Use 0.005 mm reserve.
    for (id_, ly), s in c.shapes.items():
        o = c.by_id[id_]
        if isinstance(o, pcb.PAD) or o.GetNetname() != 'GND':
            obstacles.append(s.buffer(.455))
        elif isinstance(o, pcb.PCB_VIA):
            obstacles.append(Point(xy(o.GetPosition())).buffer(.70))
    # Rank power-plane impact separately. A via may create an antipad, but that
    # candidate must then preserve every inherited eroded-copper connection.
    power = []
    for net, layer, s in c.fills:
        if net != 'GND':
            power.append(s)
    for k in c.keepouts:
        if k['vias']:
            obstacles.append(k['shape'].buffer(.255))
    blocked = prep(unary_union(obstacles))
    power = unary_union(power)
    ground = c.copper[('GND','In1.Cu')].intersection(c.copper[('GND','In4.Cu')]).buffer(-.255)
    ground = prep(ground.intersection(box(.755,.755,69.245,34.245)))
    result = []
    for f in flags:
        x,y = f['pos']; candidates=[]
        for ix in range(math.ceil((x-1.95)*20), math.floor((x+1.95)*20)+1):
            for iy in range(math.ceil((y-1.95)*20), math.floor((y+1.95)*20)+1):
                pos=(ix/20,iy/20); d=math.dist(pos,(x,y)); point=Point(pos)
                if .70 <= d <= 1.95 and not blocked.intersects(point) and ground.contains(point):
                    candidates.append({'position_mm':pos,'distance_mm':d,
                                       'power_antipad_projection_mm2':point.buffer(.655).intersection(power).area})
        candidates.sort(key=lambda r:(r['power_antipad_projection_mm2'],r['distance_mm']))
        result.append({'signal_uuid':f['uuid'],'net':f['net'],'signal_position_mm':f['pos'], 'candidate_count':len(candidates),'candidates':candidates[:30]})
    Path(out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='candidates'} | {'nearest':r['candidates'][:1]} for r in result],indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('board');p.add_argument('output');a=p.parse_args();suggest(a.board,a.output)
