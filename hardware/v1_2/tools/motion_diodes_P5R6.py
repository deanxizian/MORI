"""Correct BAT54H land pattern, preserving every signal and existing copper route."""
from review_P5R6 import *
from functional_schematic import sexpr, encode, q
from body_keepouts_P3R1 import rectangle
from layout_P5 import rect
import csv

NAME = 'BAT54H_SOD123F_Nexperia_20241008_P5R6'


def outline(f, start, end, layer, width, shape=k.S_SEGMENT):
    g = k.PCB_SHAPE(f)
    g.SetShape(shape)
    g.SetLayer(layer)
    g.SetStart(pt(*start))
    g.SetEnd(pt(*end))
    g.SetWidth(mm(width))
    f.Add(g)


def library(d):
    seed = H / 'kicad/MORI_power_P5R5/footprints/Diode_SMD.pretty/D_SOD-123F.kicad_mod'
    node = sexpr(seed.read_text())
    node[1] = q(NAME)
    node = [x for x in node if not (isinstance(x,list) and x and x[0].startswith('fp_'))]
    for x in node:
        if not isinstance(x, list):
            continue
        if x[0] == 'descr':
            x[1] = q('Nexperia BAT54H 2024-10-08 Fig 4/5; copper 1.20 square at +/-1.40; paste 1.10 square. Body MAX 2.7x1.7x1.2 mm, terminals MAX span 3.6 mm. KiCad generic STEP is not manufacturer CAD. Mask inherits project process; assembler confirmation required.')
        if x[0] == 'property' and x[1] in [q('Reference'), q('Value')]:
            x[2] = q('REF**' if x[1] == q('Reference') else 'BAT54H,115')
            if not any(isinstance(y,list) and y[0]=='hide' for y in x):
                x.append(['hide','yes'])
        if x[0] == 'pad':
            x[3] = 'rect'
            x[:] = [y for y in x if not (isinstance(y,list) and y[0] in ['roundrect_rratio','solder_paste_margin','solder_paste_margin_ratio'])]
            for y in x:
                if isinstance(y,list) and y[0]=='at':
                    y[:] = ['at', '-1.4' if x[1]==q('1') else '1.4', '0']
                if isinstance(y,list) and y[0]=='size':
                    y[:] = ['size','1.2','1.2']
            x.extend([['solder_paste_margin','-0.05'],['solder_paste_margin_ratio','0']])
    for text in [
        '(fp_rect (start -1.35 -0.85) (end 1.35 0.85) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
        '(fp_line (start -1.0 -0.85) (end -1.0 0.85) (stroke (width 0.12) (type solid)) (layer "F.Fab"))',
        '(fp_rect (start -2.25 -1.1) (end 2.25 1.1) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        '(fp_line (start -2.2 -0.85) (end -2.2 0.85) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))']:
        node.append(sexpr(text))
    lib = d / 'footprints/MORI_Custom.pretty'
    (lib / (NAME + '.kicad_mod')).write_text('(' + node[0] + '\n' + '\n'.join(encode(x) if isinstance(x,list) else x for x in node[1:]) + '\n)\n')
    return lib


def body_regions(e, refs):
    for z in list(e.b.Zones()):
        if z.GetZoneName() in {prefix + ref + suffix for ref in refs
                             for prefix in ['BODY_', 'NETBODY_'] for suffix in ['', '_OPPOSITE']}:
            e.b.Delete(z)
    for ref in refs:
        f = e.f[ref]
        bounds = rect(f)
        x1, y1, x2, y2 = bounds
        body = rectangle(bounds)
        for p in f.Pads():
            bb = p.GetBoundingBox()
            a, c, z, w = [k.ToMM(v) for v in [bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()]]
            a, c, z, w = a - .005, c - .005, z + .005, w + .005
            body.BooleanSubtract(rectangle([a, c, z, w]))
            px, py = xy(p.GetPosition())
            _, direction = min([(abs(px-x1), 'left'), (abs(x2-px), 'right'),
                                (abs(py-y1), 'top'), (abs(y2-py), 'bottom')])
            channel = {'left': [x1-1,c,z,w], 'right': [a,c,x2+1,w],
                       'top': [a,y1-1,z,w], 'bottom': [a,c,z,y2+1]}[direction]
            body.BooleanSubtract(rectangle(channel))
        body.Simplify()
        for layer, suffix in [(f.GetLayer(), ''), (F if f.GetLayer() == B else B, '_OPPOSITE')]:
            for prefix, shape, forbid in [('BODY_', body, True), ('NETBODY_', rectangle(bounds), False)]:
                z = k.ZONE(e.b)
                z.SetIsRuleArea(True)
                z.SetLayer(layer)
                z.SetZoneName(prefix + ref + suffix)
                z.SetDoNotAllowTracks(forbid)
                z.SetDoNotAllowVias(forbid)
                z.SetDoNotAllowPads(False)
                z.SetDoNotAllowFootprints(False)
                z.SetDoNotAllowZoneFills(False)
                z.Outline().BooleanAdd(shape)
                e.b.Add(z)


def sync(d, n, mapping):
    def update(node):
        if not isinstance(node, list):
            return
        props = {json.loads(x[1]): x for x in node if isinstance(x,list) and x and x[0]=='property'}
        if 'Reference' in props and 'Footprint' in props:
            ref = json.loads(props['Reference'][2])
            if ref in mapping:
                props['Footprint'][2] = q(mapping[ref])
        for x in node:
            update(x)
    for path in [d / (n + '.kicad_sch'), d / 'MORI.kicad_sym']:
        node = sexpr(path.read_text())
        update(node)
        path.write_text('(' + node[0] + '\n' + '\n'.join(encode(x) if isinstance(x,list) else x for x in node[1:]) + '\n)\n')
    path = d / 'connectivity.json'
    data = json.loads(path.read_text())
    for c in data['components']:
        if c['ref'] in mapping:
            c['footprint'] = mapping[c['ref']]
    dump(path, data)
    path = d / 'assembly_bom.csv'
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        if row['ref'] in mapping:
            row['footprint'] = mapping[row['ref']]
    with path.open('w', newline='') as out:
        w = csv.DictWriter(out, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def apply():
    e = Edit('motion')
    assert all(e.f[ref].GetValue() == 'BAT54H,115' for ref in ['D1','D2','D3'])
    assert all(NAME != str(e.f[ref].GetFPID().GetLibItemName()) for ref in ['D1','D2','D3']), 'Already applied'
    lib = library(e.d)
    log = []
    for ref in ['D1', 'D2', 'D3']:
        old = e.f[ref]
        old_pads = {p.GetNumber(): p for p in old.Pads()}
        pos, angle, side = old.GetPosition(), old.GetOrientationDegrees(), old.GetLayer()
        f = k.FootprintLoad(str(lib), NAME)
        f.SetFPID(k.LIB_ID('MORI_Custom', NAME))
        f.SetReference(ref)
        f.SetValue(old.GetValue())
        f.SetPath(old.GetPath())
        e.b.Add(f)
        f.SetPosition(pos)
        if side == B:
            f.Flip(pos, k.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(angle)
        for p in f.Pads():
            original = old_pads[p.GetNumber()]
            p.SetNet(original.GetNet())
            delta_old = (original.GetPosition() - pos)
            delta_new = (p.GetPosition() - pos)
            assert (delta_old.x*delta_new.x + delta_old.y*delta_new.y) > 0, 'Polarity reversed'
            # Existing route endpoints remain 0.25 mm outward of each new land centre.
            assert p.HitTest(original.GetPosition()), 'Old copper landing outside new pad'
        before = {'footprint': old.GetFPIDAsString(), 'pads': [(p.GetNumber(),xy(p.GetPosition()),xy(p.GetSize()),p.GetNetname()) for p in old.Pads()]}
        e.b.Remove(old)
        e.f[ref] = f
        log.append({'ref':ref, 'before':before, 'after':{'footprint':f.GetFPIDAsString(),
                    'pads':[(p.GetNumber(),xy(p.GetPosition()),xy(p.GetSize()),p.GetNetname()) for p in f.Pads()]}})
    body_regions(e, ['D1','D2','D3'])
    sync(e.d, e.name, {ref:'MORI_Custom:'+NAME for ref in ['D1','D2','D3']})
    dump(e.r/'diode_land_pattern.json', {'source':'https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf',
                                       'source_date':'2024-10-08', 'copper_pad_mm':[1.2,1.2],
                                       'pad_pitch_mm':2.8, 'paste_mm':[1.1,1.1],
                                       'mask':'Project process inherited; not copied from vendor mask artwork',
                                       'changes':log, 'physical_assembly':'NOT_TESTED'})
    return e.check('BAT54H_vendor_land', accept=True)


if __name__ == '__main__':
    ok, report = apply()
    if not ok:
        for row in report['violations']:
            print(row)
        raise SystemExit(1)
