"""Extract new copper proposals from SES; never import its replacement geometry."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from prepare_freerouting import closing

def parse(path):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', path.read_text())
    stack = [[]]
    for token in tokens:
        if token == '(':
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif token == ')':
            assert len(stack) > 1
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    assert len(stack) == 1 and len(stack[0]) == 1
    root = stack[0][0]
    assert root[0] == 'session'
    return root

def child(node, key):
    rows = [x for x in node[1:] if isinstance(x, list) and x and x[0] == key]
    assert len(rows) == 1, key
    return rows[0]

def inventory(path):
    root = parse(path)
    route = child(root, 'routes')
    resolution = child(route, 'resolution')
    assert resolution[1] == 'um'
    scale = 1 / (1000 * float(resolution[2]))
    library = child(route, 'library_out')
    # This build truncates decimal padstack labels, e.g. 499.999 -> 499,
    # while preserving a 5000-unit circle. Resolve that label against the
    # known source DSN and use its geometry, never the truncated label as size.
    original = Path('robot/.state/c3-completion/trials/R152-exchange2/R148E-r13.dsn').read_text()
    source_stacks = {}
    for m in re.finditer(r'\(padstack\s+"(Via\[0-5\]_([0-9.]+):([0-9.]+)_um)"', original):
        scope = original[m.start():closing(original,m.start())+1]
        circles = re.findall(r'\(circle\s+\S+\s+([0-9.]+)',scope)
        assert len(set(circles)) == 1
        alias = 'Via[0-5]_' + str(int(float(m[2]))) + ':' + str(int(float(m[3]))) + '_um'
        assert alias not in source_stacks
        source_stacks[alias] = dict(source_name=m[1], diameter_mm=float(circles[0])/1000, drill_mm=float(m[3])/1000)
    stacks = {}
    stack_transport = []
    for p in library[1:]:
        assert p[0] == 'padstack'
        circles = [child(x, 'circle') for x in p[2:] if x[0] == 'shape']
        assert {x[1] for x in circles} == set(LAYERS)
        widths = {round(float(x[2]) * scale, 9) for x in circles}
        assert len(widths) == 1
        name = re.fullmatch(r'Via\[0-5\]_([0-9.]+):([0-9.]+)_um', p[1])
        assert name, p[1]
        diameter = widths.pop()
        original_stack = source_stacks[p[1]]
        assert abs(diameter - original_stack['diameter_mm']) <= scale/2 + 1e-9
        stacks[p[1]] = dict(diameter_mm=diameter, drill_mm=original_stack['drill_mm'])
        stack_transport.append(dict(ses_name=p[1], ses_diameter_mm=diameter, **original_stack))
    placements = {}
    for component in child(root, 'placement')[1:]:
        if component[0] != 'component':
            continue
        for x in component[2:]:
            assert x[0] == 'place' and x[1] not in placements
            placements[x[1]] = x[2:]
    segments, vias = [], []
    for net in child(route, 'network_out')[1:]:
        assert net[0] == 'net'
        for obj in net[2:]:
            if obj[0] == 'wire':
                path = child(obj, 'path')
                values = [float(x) * scale for x in path[3:]]
                assert len(values) % 2 == 0 and len(values) >= 4
                points = [[round(values[i], 9), round(-values[i+1], 9)] for i in range(0,len(values),2)]
                for a,z in zip(points,points[1:]):
                    if a != z:
                        segments.append(dict(net=net[1], layer=path[1], width_mm=round(float(path[2])*scale,9), points_mm=[a,z]))
            elif obj[0] == 'via':
                vias.append(dict(net=net[1], position_mm=[round(float(obj[2])*scale,9),round(-float(obj[3])*scale,9)], **stacks[obj[1]]))
            else:
                raise AssertionError('Unknown SES copper: ' + obj[0])
    return dict(placements=placements, segments=segments, vias=vias, padstack_transport=stack_transport)

def extract(routed_path, revision, replace_signals=False, policy_path=None):
    b = Path('robot/.state/c3-completion/trials')
    control_path = b / 'R152-readback5/result.ses'
    source_path = Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
    source = Copper(source_path)
    expected = '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
    assert source.sha == expected
    before, after = inventory(control_path), inventory(routed_path)
    assert before['placements'] == after['placements'] and len(after['placements']) == 215
    assert len(before['vias']) == 323
    assert before['segments']
    control_geometry = {}
    source_geometry = {}
    for r in before['segments']:
        control_geometry.setdefault((r['net'],r['layer']),[]).append(LineString(r['points_mm']).buffer(r['width_mm']/2))
    for t in source.segments:
        layer = source.board.GetLayerName(t.GetLayer())
        source_geometry.setdefault((t.GetNetname(),layer),[]).append(LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(t.GetWidth()/2e6))
    control_differences = []
    for key in sorted(set(control_geometry)|set(source_geometry)):
        old = unary_union(source_geometry.get(key,[]))
        new = unary_union(control_geometry.get(key,[]))
        loss = old.difference(new.buffer(.0002)).area
        extra = new.difference(old.buffer(.0002)).area
        if loss > 1e-6 or extra > 1e-6:
            control_differences.append(dict(net=key[0],layer=key[1],loss_mm2=loss,extra_mm2=extra))
    allowed = in2_routing_nets(source_path)
    violations = [r for r in after['segments'] if r['layer'] in ['In1.Cu','In4.Cu'] or (r['layer']=='In2.Cu' and r['net'] not in allowed)]
    assert not violations, 'R13 output violation: ' + repr(violations[:5])
    deletions=[];snapshots={};active=None
    if replace_signals:
        policy_path=Path(policy_path or 'robot/.state/c3-completion/trials/R152-joint-exchange/R148E-joint.routing.json')
        policy=json.loads(policy_path.read_text())
        assert policy['source_board_sha256']==source.sha
        movable=set(policy['movable_signal_nets'])
        active=set(policy['open_nets'])|set(policy['coupled_connected_nets'])
        routed_geometry={}
        for r in after['segments']:
            routed_geometry.setdefault((r['net'],r['layer']),[]).append(LineString(r['points_mm']).buffer(r['width_mm']/2))
        routed_geometry={k:unary_union(v) for k,v in routed_geometry.items()}
        for t in source.segments:
            if t.GetNetname() not in movable:continue
            layer=source.board.GetLayerName(t.GetLayer())
            old=LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(t.GetWidth()/2e6)
            new=routed_geometry.get((t.GetNetname(),layer),GeometryCollection())
            if old.difference(new.buffer(.003)).area>1e-6:
                deletions.append(uid(t))
                snapshots[uid(t)]=dict(net=t.GetNetname(),layer=layer,width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
    old_vias = [(v.GetNetname(), Point(xy(v.GetPosition()))) for v in source.vias]
    missing_fixed_vias=[dict(net=n,position_mm=list(p.coords)[0]) for n,p in old_vias if not any(v['net']==n and p.distance(Point(v['position_mm']))<.002 for v in after['vias'])]
    assert not missing_fixed_vias, 'Source vias are protected in this proposal'
    new_vias = [v for v in after['vias'] if not any(n == v['net'] and p.distance(Point(v['position_mm'])) < .002 for n,p in old_vias)]
    source.copper
    retained=source.copper
    if deletions:
        retained={};omitted=set(deletions)
        for (i,layer),shape_ in source.shapes.items():
            if i not in omitted:retained.setdefault((source.by_id[i].GetNetname(),layer),[]).append(shape_)
        for net,layer,shape_ in source.fills:retained.setdefault((net,layer),[]).append(shape_)
        retained={k:unary_union(v) for k,v in retained.items()}
    new_segments = []
    for r in after['segments']:
        if active is not None and r['net'] not in active:continue
        stroke = LineString(r['points_mm']).buffer(r['width_mm']/2)
        old = retained.get((r['net'],r['layer']),GeometryCollection())
        added = stroke.difference(old.buffer(.003))
        if added.area > 1e-6:
            new_segments.append(r)
    netlist = sorted({x['net'] for x in new_segments + new_vias})
    source_groups=source.pad_groups()
    plan = dict(revision=revision, scope=__doc__, board_sha256=source.sha,
                source_ses=str(routed_path), control_ses=str(control_path),
                source_ses_sha256=hashlib.sha256(routed_path.read_bytes()).hexdigest(),
                routes=new_segments, vias=new_vias, delete_copper=deletions,deleted_copper_expected=snapshots)
    report = dict(scope=__doc__, source_board_sha256=source.sha, placements_preserved=215,
                  control_segments=len(before['segments']), control_vias=len(before['vias']),
                  control_native_track_count=len(source.segments),
                  control_geometry_differences_at_0_2um=control_differences,
                  padstack_transport=after['padstack_transport'],
                  result_segments=len(after['segments']), result_vias=len(after['vias']),
                  output_R13_violations=violations,
                  new_segment_count=len(new_segments), new_via_count=len(new_vias),
                  explicitly_replaced_source_tracks=len(deletions),
                  replacement_policy=str(policy_path) if policy_path else None,
                  missing_fixed_vias=missing_fixed_vias,
                  nets=[dict(net=n, new_segments=sum(x['net']==n for x in new_segments), new_vias=sum(x['net']==n for x in new_vias), source_pad_groups=len(source_groups.get(n,[]))) for n in netlist],
                  native_candidate_built=False,
                  limits=['A 3 um geometry tolerance only removes transport noise; it does not waive native clearance or reference checks.',
                          'New copper is reapplied to exact R148E native objects. The SES board and its altered old padstacks are never imported.',
                          'These are proposals, not accepted connections or a completed board.'])
    for suffix, data in [('plan',plan),('extraction',report)]:
        p=b/(revision+'-'+suffix+'.json');assert not p.exists();p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['placements_preserved','output_R13_violations','new_segment_count','new_via_count','explicitly_replaced_source_tracks','nets']},ensure_ascii=False))

if __name__ == '__main__':
    args=sys.argv[3:]
    policy=args[args.index('--policy')+1] if '--policy' in args else None
    extract(Path(sys.argv[1]), sys.argv[2], '--replace-signals' in args, policy)
