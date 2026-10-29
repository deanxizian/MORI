"""Explicit C909 rotation and HEAD_6V_RAW allocation candidate; not adopted."""
import json
import sys
from pathlib import Path
from shapely.geometry import Polygon
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_snapshot

b = Path('robot/.state/c3-completion/trials')
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha == '7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9'
out = b / 'R153A-plan.json'
assert not out.exists()
net = '/HEAD_6V_RAW'
drop = ['9ab72324-cc9b-4135-85b6-936782a014dc']
expected = {u: {'net': c.by_id[u].GetNetname(), 'layer': c.board.GetLayerName(c.by_id[u].GetLayer()),
                'width_mm': c.by_id[u].GetWidth()/1e6, 'start_mm': list(xy(c.by_id[u].GetStart())),
                'end_mm': list(xy(c.by_id[u].GetEnd()))} for u in drop}
zone = next(z for z in c.zones if z.GetZoneName() == 'HEAD_6V_RAW_LOCAL')
patch = [(3.6,16.3),(4.9,16.3),(5.7,17.1),(8.2,17.1),(8.2,21.6),(3.5,21.6),(3.5,17.2)]
old = polyset(zone.Outline())
plan = {'revision': 'R153A', 'scope': __doc__, 'board_sha256': c.sha,
        'translations': [{'reference': 'C909', 'from_mm': [3.85,17.75], 'delta_mm': [0,.65], 'rotation_deg':180}],
        'delete_copper': drop, 'deleted_copper_expected': expected,
        'routes': [{'net': net, 'layer':'B.Cu', 'width_mm':.5,
                    'points_mm':[[3.75,14.7],[3.35,15.1],[3.35,16.075],[4.325,17.05],[4.325,17.15],[4.8,17.625],[4.8,18.4]]}],
        'vias': [{'net':net,'position_mm':[4.325,17.05],'diameter_mm':.8,'drill_mm':.4}],
        'power_zone_expansions':[{'uuid':uid(zone),'source_expected':zone_snapshot(c.board,zone),
            'union_patch_mm':patch,'expected_added_area_mm2':old.union(Polygon(patch)).area-old.area,
            'reason':'Join the isolated C909/C911 output reservoir to its existing 6 V allocation using an explicit new power via and short local branch. Full native refill, original power and reference regression and actual added-path width review remain required.'}]}
out.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'plan':str(out),'added_allocation_mm2':plan['power_zone_expansions'][0]['expected_added_area_mm2']}))
