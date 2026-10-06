"""Scoped E/J3 corrections. Run with KiCad Python. Never changes P5R6 or mechanics.

The rear J3 flip is independent of the pending WeAct assembly-orientation choice.
This script creates review prototypes, not fabrication releases.
"""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import sys
import wx
import pcbnew as k

APP = wx.App(False)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
H = ROOT / 'hardware/v1_2'
sys.path.insert(0, str(H / 'tools'))
from layout_P5 import xy, pt, rect
from layout_P5 import track, via

CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def paths(kind, rev='P5R7'):
    name = f'MORI_{kind}_{rev}'
    d = H / 'kicad' / name
    return name, d, d / (name + '.kicad_pcb')


def copy_project(kind):
    old, source, _ = paths(kind, 'P5R6')
    name, dest, _ = paths(kind)
    if dest.exists():
        raise RuntimeError('Refusing to overwrite ' + str(dest))
    hashes = {}
    for f in source.rglob('*'):
        if not f.is_file() or f.name.startswith('~') or f.suffix in ['.lck', '.kicad_prl', '.dsn', '.ses']:
            continue
        rel = f.relative_to(source)
        out = dest / rel.parent / f.name.replace(old + '.', name + '.')
        out.parent.mkdir(parents=True, exist_ok=True)
        data = f.read_bytes()
        hashes[str(f.relative_to(ROOT))] = sha(f)
        if f.suffix in ['.kicad_sch', '.kicad_pro']:
            data = data.replace(old.encode(), name.encode())
            data = data.replace(b'V1.2-H0.5-P5R6', b'V1.2-H0.5-P5R7')
        out.write_bytes(data)
    dump(HERE / 'reports' / kind / 'copied_source_hashes.json', hashes)
    return name, dest


def pad_state(f):
    return sorted((p.GetNumber(), xy(p.GetPosition()), p.GetNetname(), xy(p.GetSize()), xy(p.GetDrillSize())) for p in f.Pads())


def copper(b):
    ans = []
    for t in b.GetTracks():
        via = isinstance(t, k.PCB_VIA)
        ans.append((t.m_Uuid.AsString(), t.GetNetname(), t.GetLayer(), xy(t.GetStart()), xy(t.GetEnd()),
                    k.ToMM(t.GetWidth(k.F_Cu) if via else t.GetWidth()), k.ToMM(t.GetDrillValue()) if via else None))
    return sorted(ans)


def build_rear():
    name, d, candidate = paths('rear')
    if d.exists():
        assert candidate.read_bytes() == paths('rear', 'P5R6')[2].read_bytes(), 'Candidate has already been changed'
    else:
        name, d = copy_project('rear')
    _, _, p = paths('rear')
    b = k.LoadBoard(str(p))
    f = next(f for f in b.GetFootprints() if f.GetReference() == 'J3')
    before = pad_state(f)
    before_copper = copper(b)
    assert not f.IsFlipped() and xy(f.GetPosition()) == (8.45, 19.5)
    f.Flip(f.GetPosition(), k.FLIP_DIRECTION_TOP_BOTTOM)
    for z in b.Zones():
        if z.GetZoneName() in [prefix + 'J3' + suffix for prefix in ['BODY_', 'NETBODY_', 'VIA_BODY_'] for suffix in ['', '_OPPOSITE']]:
            z.Flip(f.GetPosition(), k.FLIP_DIRECTION_TOP_BOTTOM)
    assert f.IsFlipped() and pad_state(f) == before
    assert copper(b) == before_copper
    title = b.GetTitleBlock()
    title.SetTitle('MORI rear / P5R7 / PROTOTYPE')
    title.SetRevision('V1.2-H0.5-P5R7')
    title.SetComment(1, 'J3 bottom assembly; same holes and nets; NOT_TESTED')
    for g in list(b.GetDrawings()):
        if isinstance(g, k.PCB_TEXT) and 'REAR P5R6' in g.GetText():
            g.SetText(g.GetText().replace('REAR P5R6', 'REAR P5R7'))
    k.SaveBoard(str(p), b)
    dump(HERE / 'reports/rear/initial_flip.json', {
        'pcb': str(p.relative_to(ROOT)), 'sha256': sha(p),
        'J3': {'before_side': 'F', 'after_side': 'B', 'position_mm': xy(f.GetPosition()),
               'numbered_pads_unchanged': True, 'pads': before, 'body_projection_mm': rect(f)},
        'track_and_via_geometry_unchanged': True,
        'physical_validation': 'NOT_TESTED', 'native_checks': 'NOT_TESTED'
    })
    (d / 'README.md').write_text('# MORI rear P5R7 — review prototype\n\n'
        'J3 remains the same vertical JST PH 4-pin connector, mounted on B.Cu, '
        'with every numbered pad at its P5R6 location. The mated plug exits downward. '
        'Electrical topology and other connector datums are preserved.\n\n'
        'PROTOTYPE / NOT_TESTED. No fabrication release or physical fit claim. '
        'See hardware/v1_2/reviews/weact_E_J3_20260930 for hash-backed native checks '
        'and the bounded mechanical screen. Native SW1 is retained; the broader '
        'physical power-cut implementation remains outside this local fix.\n')


def checks(kind, stage):
    name, d, p = paths(kind)
    out = HERE / 'reports' / kind / stage
    out.mkdir(parents=True, exist_ok=True)
    cmds = [
        [CLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors', '--schematic-parity',
         '--refill-zones', '--exit-code-violations', '-o', str(out / 'drc.json'), str(p)],
        [CLI, 'sch', 'erc', '--format', 'json', '--severity-all', '--exit-code-violations',
         '-o', str(out / 'erc.json'), str(d / (name + '.kicad_sch'))]
    ]
    logs = []
    for cmd in cmds:
        cp = subprocess.run(cmd, capture_output=True, text=True)
        logs.append({'argv': cmd, 'returncode': cp.returncode, 'stdout': cp.stdout, 'stderr': cp.stderr})
        print(cmd[2], cp.returncode, cp.stdout, cp.stderr, flush=True)
    dump(out / 'commands.json', {'inputs': {str(q.relative_to(ROOT)): sha(q) for q in [p, d / (name + '.kicad_sch'), d / (name + '.kicad_dru'), d / (name + '.kicad_pro')]}, 'commands': logs})


def reroute_rear():
    """Rebuild this candidate from the unchanged source, not accumulated patches."""
    name, d, p = paths('rear')
    b = k.LoadBoard(str(paths('rear', 'P5R6')[2]))
    f = next(f for f in b.GetFootprints() if f.GetReference() == 'J3')
    f.Flip(f.GetPosition(), k.FLIP_DIRECTION_TOP_BOTTOM)
    pivot=pt(8.45,19.5)
    rotation=k.EDA_ANGLE(180,k.DEGREES_T)
    shift=pt(6,1.7)
    for z in b.Zones():
        if z.GetZoneName() in [prefix + 'J3' + suffix for prefix in ['BODY_', 'NETBODY_', 'VIA_BODY_'] for suffix in ['', '_OPPOSITE']]:
            z.Flip(pivot, k.FLIP_DIRECTION_TOP_BOTTOM)
            z.Rotate(pivot,rotation)
            z.Move(shift)
            # Clip the body screen to the actual JST housing. The inherited
            # Fab bounding box also contained an L-shaped pin-1 annotation.
            # Keep its per-pad outward escape slots; no new track exemptions.
            outline=k.SHAPE_POLY_SET();outline.NewOutline()
            for x,y in [(6.5,19.5),(16.4,19.5),(16.4,24),(6.5,24)]:
                outline.Append(k.FromMM(x),k.FromMM(y))
            z.Outline().BooleanIntersection(outline)
    f.Rotate(pivot,rotation)
    f.Move(shift)
    for t in list(b.GetTracks()):
        if t.GetNetname() in ['/MASTER_RETURN', '/LOOP_3V3', '/CLR_N']:
            b.Delete(t)
        elif t.GetNetname() == '/GND' and (
            isinstance(t, k.PCB_VIA) and xy(t.GetPosition()) in [(10.45, 21.2),(12,23.4)]
            or not isinstance(t, k.PCB_VIA) and (xy(t.GetStart()) in [(10.45, 19.5), (10.45, 21.2)]
                                                or xy(t.GetEnd()) in [(10.45, 19.5), (10.45, 21.2)])):
            b.Delete(t)
    routes = [
        ('/MASTER_RETURN', k.F_Cu, [(9.5,10.85),(7.55,10.85),(7.05,11.35),(7.05,17.3)]),
        ('/MASTER_RETURN', k.B_Cu, [(7.05,17.3),(8.05,18.3),(13.5,18.3),(14.45,19.25),(14.45,21.2)]),
        ('/LOOP_3V3', k.F_Cu, [(9.5,15.7),(9.5,18.3),(10.45,19.25),(10.45,21.2)]),
        ('/CLR_N', k.F_Cu, [(12,15.7),(12,17.4)]),
        ('/CLR_N', k.B_Cu, [(12,17.4),(8.45,17.4)]),
        ('/CLR_N', k.F_Cu, [(8.45,17.4),(8.45,21.2)])
    ]
    for net, layer, points in routes:
        track(b, net, points, .2, layer)
    for net,x,y in [('/MASTER_RETURN',7.05,17.3),('/CLR_N',12,17.4),('/CLR_N',8.45,17.4)]:
        via(b,net,x,y,vd=.8,dr=.3,grid=False)
    # Old B-side solder-view labels would now be underneath the physical plug.
    # Move them to the unchanged F-side solder view; add mated-side labels later.
    for g in list(b.GetDrawings()):
        if not isinstance(g, k.PCB_TEXT):
            continue
        if g.GetText() in ['1RET', '2GND', '3LOOP', '4CLR', 'J3 INTERLOCK']:
            # Relabel in a following explicit marking pass after route checks.
            b.Delete(g)
            continue
        if 'REAR P5R6' in g.GetText():
            g.SetText(g.GetText().replace('REAR P5R6','REAR P5R7'))
    title=b.GetTitleBlock()
    title.SetTitle('MORI rear / P5R7 / PROTOTYPE')
    title.SetRevision('V1.2-H0.5-P5R7')
    title.SetComment(1, 'J3 B.Cu 180 / pad1 (14.45,21.2); same pin signals; NOT_TESTED')
    k.SaveBoard(str(p), b)
    dump(HERE/'reports/rear/route_plan.json', {'routes': routes,
         'reason': 'B-side 180-degree rotation and row Y21.2 provide near-edge upward pin escape, separate D1 courtyard and route corridor; all other component poses unchanged. Same numbered pin signals; numbered pad X positions reverse and row moves +1.7mm.',
         'new_J3_pad1_xy_mm':[14.45,21.2], 'physical_validation':'NOT_TESTED'})


def finish_rear():
    name,d,p=paths('rear');b=k.LoadBoard(str(p))
    assert next(f for f in b.GetFootprints() if f.GetReference()=='J3').IsFlipped()
    labels=[('J3 B-SIDE',(11.45,19.05)),('4:CLR',(8.5,22.8)),('1:RET',(14,22.8)),
            ('3:LOOP',(8.5,24)),('2:GND',(14,24))]
    existing={g.GetText() for g in b.GetDrawings() if isinstance(g,k.PCB_TEXT)}
    for text,position in labels:
        if text in existing:
            t=next(g for g in b.GetDrawings() if isinstance(g,k.PCB_TEXT) and g.GetText()==text)
            t.SetTextSize(pt(.8,.8));continue
        t=k.PCB_TEXT(b);t.SetText(text);t.SetPosition(pt(*position));t.SetLayer(k.F_SilkS)
        t.SetTextSize(pt(.8,.8));t.SetTextThickness(k.FromMM(.12));b.Add(t)
    b.GetTitleBlock().SetComment(0,'J3 mating/route review; physical tests NOT_TESTED')
    b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
    sch=d/(name+'.kicad_sch')
    s=sch.read_text().replace('(date "2026-09-23")','(date "2026-09-30")')
    s=s.replace('P5R6 layout/assembly review; circuit P5; PROTOTYPE / NOT_TESTED',
                'P5R7 J3 bottom assembly; pin functions unchanged; PROTOTYPE / NOT_TESTED')
    sch.write_text(s)
    sl=d/'schematic_layout.json';j=json.loads(sl.read_text());j.update(project=name,schematic_sha256=sha(sch));dump(sl,j)
    dump(d/'layout_notes.json',{'revision':'P5R7-J3','circuit_revision':'V1.2-H0.5-P5',
        'scope':'Rear J3 only; motion E awaits explicit core orientation confirmation',
        'mechanical_handoff':'../../handoff/mechanical_J3_P5R7_20260930.json',
        'review':'../../reviews/weact_E_J3_20260930/README.md',
        'physical_tests':'NOT_TESTED','manufacturing_release':False})
    for file in ['assembly_bom.csv']:
        with (d/file).open(encoding='utf-8-sig',newline='')as h:rows=list(csv.DictReader(h))
        for row in rows:
            if row['ref']=='J3':
                row['note']='JST B4B-PH-K-S(LF)(SN), C131334; PHR-4/SPH-002T-P0.5S. B.Cu assembly, 180deg, pad1=(14.45,21.2)mm. 1=MASTER_RETURN / power J19.1; 2=GND / power J19.2; 3=LOOP_3V3 / motion J8.1; 4=CLR_N / motion J8.2. Native top view left-to-right 4,3,2,1. Verify numbered housings and continuity; no price/stock confirmation in this change.'
        with (d/file).open('w',encoding='utf-8-sig',newline='')as h:
            w=csv.DictWriter(h,list(rows[0]));w.writeheader();w.writerows(rows)
    (d/'README.md').write_text('''# MORI rear P5R7 — J3 装配修正原型

J3 保留 JST B4B-PH-K-S(LF)(SN) / PHR-4 / SPH-002T-P0.5S，改为 B.Cu 安装、180°，向下插拔。1 号孔为原生板坐标 (14.45,21.20) mm，孔排整体 Y+1.70 mm。原生顶视图从左到右为 4、3、2、1；各编号对应的网络和线束功能不变。

|针|网络|对端|
|---|---|---|
|1|MASTER_RETURN|电源板 J19.1|
|2|GND|电源板 J19.2|
|3|LOOP_3V3|运动板 J8.1|
|4|CLR_N|运动板 J8.2|

板框仍为原生 24×25×1.6 mm；安装孔、其余器件坐标、原理图拓扑均保持。P5R6 文件完整保留。不要在旧 P5R6 板上仅把插座翻面；P5R7 已调整编号孔位的网络连接。

三根互锁信号局部重布；0.20 mm 线宽、0.80/0.30 mm 新增过孔。J3 的塑料本体投影按 JST 图中 9.9×4.5 mm 确定，不把 Fab 层外侧的 1 脚 L 形标记算入实体；原有逐引脚逃线通道保留，无新增 DRC 忽略。

PROTOTYPE / NOT_TESTED。检查、几何局限和带哈希交接见 hardware/v1_2/reviews/weact_E_J3_20260930/README.md。SW1 电路本次保留；整机物理断电/急停实现另需闭合。没有下单或生产验证声明。
''')


if __name__ == '__main__':
    if sys.argv[1] == 'build_rear':
        build_rear()
    elif sys.argv[1] == 'check':
        checks(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'reroute_rear':
        reroute_rear()
    elif sys.argv[1] == 'finish_rear':
        finish_rear()
    else:
        raise SystemExit('Unsupported action')
