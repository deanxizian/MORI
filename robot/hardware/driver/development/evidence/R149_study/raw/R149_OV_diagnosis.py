"""Record the exact OV barrier found by the invalid soft-path diagnosis; no route approval."""
import json,sys,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');out=b/'R149-OV-diagnosis.json';assert not out.exists()
c=Copper(b/'R149C/MORI_Interface_C3.kicad_pcb');net='Net-(U1301-INB-_{slash}_OV)';d=json.loads((b/'R149-soft-obstacle-diagnostic/diagnosis.json').read_text())[0]
data=dict(scope=__doc__,source_sha256=c.sha,net=net,In2_allowed_by_unchanged_R13=net in in2_routing_nets(c.path),groups=[g['pads'] for g in groups(c,net)],tracks=[dict(uuid=uid(t),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=xy(t.GetStart()),end_mm=xy(t.GetEnd())) for t in c.segments if t.GetNetname()==net],vias=[dict(uuid=uid(v),**via_snapshot(c.board,v)) for v in c.vias if v.GetNetname()==net],invalid_current_path_length_mm=sum(math.dist(a,z) for r in d['routes'] for a,z in zip(r['points_mm'],r['points_mm'][1:])),crossed_segments=d['crossed_existing_segments'],adopted=False)
out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
