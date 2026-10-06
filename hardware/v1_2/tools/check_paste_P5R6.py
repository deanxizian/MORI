#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export review-only native Paste SVGs; retain resolved aperture measurements.

These SVGs are inspection views, not a released stencil/manufacturing package.
No PCB or schematic is saved. Supplier process/physical assembly remain untested.
"""
import subprocess
import math
import re
import xml.etree.ElementTree as ET
from audit_width_scope_P5R6 import k, OUT, CLI, paths, inputs, dump, sha, xy


def main():
    target = OUT / 'paste_preview'
    target.mkdir(parents=True, exist_ok=True)
    results = {}
    for kind, layer, refs in [('motion', k.B_Paste, ['D1', 'D2', 'D3']),
                              ('imu', k.F_Paste, ['U1'])]:
        name, directory, pcb = paths(kind)
        before = inputs(directory)
        b = k.LoadBoard(str(pcb))
        rows = []
        for ref in refs:
            f = next(f for f in b.GetFootprints() if f.GetReference() == ref)
            for p in sorted(f.Pads(), key=lambda p: int(p.GetNumber())):
                assert p.IsOnLayer(layer)
                margin = p.GetSolderPasteMargin(layer)
                size = p.GetSize()
                aperture = (round(k.ToMM(size.x+2*margin.x), 6),
                            round(k.ToMM(size.y+2*margin.y), 6))
                if kind == 'motion':
                    assert aperture == (1.1, 1.1)
                else:
                    assert sorted(aperture) == [.225, .4275]
                rows.append(dict(ref=ref, pin=p.GetNumber(), net=p.GetNetname(),
                                 location_mm=xy(p.GetPosition()),
                                 angle_deg=p.GetOrientation().AsDegrees(),
                                 copper_pad_mm=xy(size),
                                 native_resolved_margin_mm=xy(margin), aperture_mm=aperture))
        assert len(rows) == (6 if kind == 'motion' else 14)
        svg = target / (kind + '_' + b.GetLayerName(layer) + '_REVIEW_ONLY.svg')
        args = [CLI, 'pcb', 'export', 'svg', '--mode-single', '--fit-page-to-board',
                '--exclude-drawing-sheet', '--layers', b.GetLayerName(layer),
                '--black-and-white', '-o', str(svg), str(pcb)]
        cp = subprocess.run(args, capture_output=True, text=True, timeout=180)
        assert cp.returncode == 0 and svg.is_file(), cp.stderr
        # Independently inspect the exported native SVG, not just pad metadata.
        # KiCad emits these filled apertures as polygonal paths in board mm.
        apertures = []
        for element in ET.parse(svg).getroot().iter('{http://www.w3.org/2000/svg}path'):
            if 'stroke:none' not in element.get('style', ''):
                continue
            path_data = element.get('d', '')
            assert not re.sub(r'[MLZ0-9.,\s\-]', '', path_data), 'Update SVG polygon reader'
            pts = [tuple(map(float, pair)) for pair in re.findall(r'(-?[0-9.]+),(-?[0-9.]+)', path_data)]
            if not pts:
                continue
            lo = [min(p[i] for p in pts) for i in range(2)]
            hi = [max(p[i] for p in pts) for i in range(2)]
            apertures.append(dict(centre=[(a+z)/2 for a, z in zip(lo, hi)],
                                  size=[z-a for a, z in zip(lo, hi)]))
        for row in rows:
            matches = [a for a in apertures if math.dist(a['centre'], row['location_mm']) < .0002]
            assert len(matches) == 1, (row, matches)
            actual = sorted(matches[0]['size'])
            assert all(abs(x-y) < .0002 for x, y in zip(actual, sorted(row['aperture_mm'])))
            row['exported_SVG_bbox_mm'] = matches[0]['size']
            row['SVG_aperture_match'] = 'PASS'
        assert inputs(directory) == before
        results[kind] = dict(status='PASS', pcb_sha256=sha(pcb), input_sha256=before,
                             svg=svg.name, svg_sha256=sha(svg), pads=rows,
                             view='Top-coordinate view; bottom is not mirrored',
                             method='KiCad native resolved pad margin including pad/footprint/project inheritance; native Paste SVG export',
                             command=dict(argv=args, returncode=cp.returncode, stdout=cp.stdout, stderr=cp.stderr),
                             supplier_stencil_process='NOT_TESTED', physical_soldering='NOT_TESTED')
    dump(target / 'apertures.json', results)
    print('Native Paste preview: motion D1/D2/D3 6 pads 1.10x1.10; IMU U1 14 pads 0.4275x0.225 mm')


if __name__ == '__main__':
    main()
