#!/usr/bin/env python3
"""Local, reviewable placement -> DSN -> SES workflow; never manufacturing files.

Run using the Python bundled with KiCad. Freerouting is a separate local process.
"""
from pathlib import Path
import argparse, json, hashlib, re
import pcbnew as k

R = Path(__file__).resolve().parents[1]
D = R / 'kicad'
PCB = D / 'MORI_carrier.kicad_pcb'
mm = k.FromMM
ap = argparse.ArgumentParser()
ap.add_argument('action', choices=['prepare', 'repair', 'import', 'zones'])
args = ap.parse_args()
board = k.LoadBoard(str(PCB))
classes = {
    'Default': (.25, .60, .30),
    'LogicPower': (.30, .60, .30),  # carrier logic/IMU rail, not ESP32 core supply
    'PeripheralPower': (.80, 1.00, .50),
    'MotorPower': (1.00, 1.20, .60),
    'MainPower': (1.20, 1.20, .60),
    'Ground': (.80, 1.00, .50),
}
mapping = {'3V3':'LogicPower', 'GND':'Ground'}
for name in ['DEVKIT_5V', 'LOGIC_5V_RAW', 'SERVO_5V_RAW', 'HEAD_5V']:
    mapping[name] = 'PeripheralPower'
for name in ['LM1','LM2','RM1','RM2']:
    mapping[name] = 'MotorPower'
for name in ['VMAIN','VM_DRV_IN','VM_MOTOR','DUMP_DRAIN']:
    mapping[name] = 'MainPower'

def apply_classes():
    ns = board.GetDesignSettings().m_NetSettings
    objs = {}
    project = json.loads((D/'MORI_carrier.kicad_pro').read_text())
    out = []
    for name, (track, via, drill) in classes.items():
        nc = k.NETCLASS(name)
        nc.SetClearance(mm(.20)); nc.SetTrackWidth(mm(track))
        nc.SetViaDiameter(mm(via)); nc.SetViaDrill(mm(drill))
        ns.SetNetclass(name, nc); objs[name] = nc
        out.append(dict(name=name, clearance=.20, track_width=track,
            via_diameter=via, via_drill=drill, diff_pair_width=.25,
            diff_pair_gap=.25, diff_pair_via_gap=.25))
    patterns = []
    for net, cl in mapping.items():
        if '/'+net not in board.GetNetsByName():
            raise ValueError('Unknown power net '+net)
        ns.SetNetclassPatternAssignment('/'+net, cl)
        patterns.append({'netclass':cl,'pattern':'/'+net})
    ns.RecomputeEffectiveNetclasses()
    for name, net in board.GetNetsByName().items():
        net.SetNetClass(objs[mapping.get(str(name).lstrip('/'),'Default')])
    project['net_settings']['classes'] = out
    project['net_settings']['netclass_patterns'] = patterns
    (D/'MORI_carrier.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')

apply_classes()
if args.action in ['prepare','repair']:
    if args.action=='prepare':
        assert len(board.GetTracks()) == 0, 'Refusing to replace existing routing'
    else:
        drc=json.loads((R/'reports/drc_routed.json').read_text())
        remove=set()
        for item in drc['violations']:
            if item['type']=='copper_edge_clearance':
                remove.update(x['uuid'] for x in item['items'])
        count=0
        for item in list(board.GetTracks()):
            if item.m_Uuid.AsString() in remove:
                board.Delete(item);count+=1
        print('Removed',count,'tracks violating physical board-edge clearance')
    # Keep this reference in the assembly layer; silk intersects the Q1 outline.
    if args.action=='prepare':
        next(f for f in board.GetFootprints() if f.GetReference()=='R14').Reference().SetLayer(k.F_Fab)
    k.SaveBoard(str(PCB),board)
    assert k.ExportSpecctraDSN(board,str(D/'MORI_carrier.dsn'))
    # KiCad exports cutouts as generic Specctra keepouts using 0.2 mm net
    # clearance. Enlarge those three keepouts by 0.35 mm so routing respects
    # the independent 0.5 mm copper-to-milled-edge requirement. Real Edge.Cuts
    # remain unchanged. DSN units are micrometres, not mm.
    path=D/'MORI_carrier.dsn';text=path.read_text();modified=[0]
    def expand(match):
        nums=[float(x) for x in match.group(1).split()]
        points=list(zip(nums[::2],nums[1::2]))
        xs=[x for x,y in points];ys=[y for x,y in points]
        cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
        if len(points)==5:
            p=[(x+(350 if x>cx else -350),y+(350 if y>cy else -350)) for x,y in points]
        else:
            import math
            p=[]
            for x,y in points:
                rad=math.hypot(x-cx,y-cy)
                p.append((cx+(x-cx)*(rad+350)/rad,cy+(y-cy)*(rad+350)/rad))
        modified[0]+=1
        return '(keepout "" (polygon signal 0 '+ ' '.join(f'{x:.3f} {y:.3f}' for x,y in p)+'))'
    text=re.sub(r'\(keepout "" \(polygon signal 0\s+([\d.eE+\-\s]+)\)\)',expand,text)
    assert modified[0]==3,modified
    path.write_text(text)
    print('PASS: local DSN exported; power-net widths included; unrouted source retained')
elif args.action=='import':
    assert k.ImportSpecctraSES(board,str(D/'MORI_carrier.ses'))
    for drawing in board.GetDrawings():
        if isinstance(drawing,k.PCB_TEXT) and 'UNROUTED' in drawing.GetText():
            drawing.SetText('MORI A0.5 ROUTING CANDIDATE / UNVALIDATED')
    k.SaveBoard(str(PCB),board)
    counts = {'tracks_and_vias':len(board.GetTracks()), 'zones':len(board.Zones()),
        'source_sha256':hashlib.sha256(PCB.read_bytes()).hexdigest(),
        'fabrication_allowed':False,
        'note':'Autoroute result requires native KiCad DRC, current-path/return-path and mechanical review.'}
    (R/'reports/routing_import.json').write_text(json.dumps(counts,indent=2)+'\n')
    print(json.dumps(counts,indent=2))
else:
    assert len(board.Zones())==0, 'Refusing to duplicate ground zones'
    # Both planes use the physical edge constraints. KiCad removes islands and
    # clips the pour to the actual outline/cutouts; no manufacturing export.
    for layer in [k.F_Cu,k.B_Cu]:
        z=k.ZONE(board);z.SetLayer(layer);z.SetNet(board.GetNetsByName()['/GND'])
        z.SetLocalClearance(mm(.25));z.SetThermalReliefGap(mm(.30))
        z.SetThermalReliefSpokeWidth(mm(.50));z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
        poly=z.Outline();poly.NewOutline()
        for x,y in [(50,52),(150,52),(150,148),(50,148)]:poly.Append(mm(x),mm(y))
        board.Add(z)
    assert k.ZONE_FILLER(board).Fill(board.Zones())
    k.SaveBoard(str(PCB),board)
    print('Ground zones filled locally; native DRC still required')
