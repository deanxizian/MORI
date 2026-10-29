"""Read-only exact original via preservation in every completed R170 board."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170-source-retention.json';assert not out.exists();c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');source={uid(v):via_snapshot(c.board,v) for v in c.vias};ground={u:s for u,s in source.items() if s['net']=='GND'};rows=[]
# All 325 current-source vias are kept. The separate 114 original R108P ground
# vias are proved by the preserved inspection helper for the final comparison.
for suffix in 'ABCDEFGHIJ':
 rev='R170'+suffix;q=Copper(b/rev/'MORI_Interface_C3.kicad_pcb');actual={uid(v):via_snapshot(q.board,v) for v in q.vias};bad=[u for u,s in source.items() if actual.get(u)!=s];rows.append(dict(revision=rev,board_sha256=q.sha,original_vias=len(source),original_GND_vias=len(ground),exact_snapshot_mismatches=bad));assert not bad,(rev,bad)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,rows=rows,status='PASS'),indent=2)+'\n');print('PASS',len(rows),'native boards;',len(source),'original vias retained per board')
