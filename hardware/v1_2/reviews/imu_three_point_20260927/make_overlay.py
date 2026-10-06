"""Diagnostic vector plot from native geometry; no CAD edits."""
import html
import json
from pathlib import Path
O=Path(__file__).resolve().parent
d=json.loads((O/'evaluation.json').read_text())
decision = json.loads((O/'review_response.json').read_text()) if (O/'review_response.json').exists() else {}
withdrawn = decision.get('proposal_state') == 'WITHDRAWN_BY_USER'
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="790" viewBox="0 0 1120 790">',
 '<rect width="1120" height="790" fill="#f7f9fc"/>',
 '<style>text{font-family:Arial,sans-serif;fill:#192e48} .small{font-size:14px} .tiny{font-size:.40px}</style>',
 '<text x="46" y="44" font-size="25" font-weight="bold">MORI IMU | 20 x 21 mm mounting proposal</text>',
 '<text x="46" y="72" font-size="15">P5R4 native copper translated by Y + 5 mm. Evaluation only; no new PCB saved.</text>',
 '<g transform="translate(70 125) scale(27)">',
 '<rect x="0" y="0" width="20" height="21" fill="white" stroke="#162d43" stroke-width=".07"/>',
 '<rect x="0" y="0" width="20" height="5" fill="#ffe4aa" opacity=".55"/>']
def ring(points):
 return 'M'+' L'.join(f'{x:.5f},{y+5:.5f}' for x,y in points)+' Z'
for z in d['zones']:
 if z['layer']!='B.Cu':continue
 for p in z['saved_polygons']:
  path=' '.join(ring(r) for r in [p['outer'],*p['holes']])
  s.append(f'<path d="{path}" fill="#d99b34" fill-opacity=".3" fill-rule="evenodd"/>')
 for p in z['virtually_cut_polygons']:
  path=' '.join(ring(r) for r in [p['outer'],*p['holes']])
  s.append(f'<path d="{path}" fill="#3187ac" fill-opacity=".17" fill-rule="evenodd"/>')
for t in d['tracks_and_vias']:
 x,y=t['start_mm'];xx,yy=t['end_mm'];color='#bd3c51' if t['layer']=='F.Cu' else '#246abb'
 if t['kind']=='via':s.append(f'<circle cx="{x}" cy="{y+5}" r="{t["width_mm"]/2}" fill="white" stroke="#8355a2" stroke-width=".10"/>')
 else:s.append(f'<path d="M{x},{y+5} L{xx},{yy+5}" fill="none" stroke="{color}" stroke-width="{t["width_mm"]}" stroke-linecap="round"/>')
for p in d['pads']:
 if not p['copper']:continue
 x,y=p['position_mm'];w,h=p['size_mm'];color='#f4d589'
 s.append(f'<rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx=".14" transform="translate({x},{y+5}) rotate({-p["rotation_deg"]})" fill="{color}" stroke="#716744" stroke-width=".035"/>')
 if p['drill_mm'][0]:s.append(f'<circle cx="{x}" cy="{y+5}" r="{p["drill_mm"][0]/2}" fill="white"/>')
for p in d['placements']:
 if p['ref'].startswith('H'):continue
 box=p['fab_graphics_bounds_with_line_width_mm']
 if not box:continue
 x,y,xx,yy=box
 s.append(f'<rect x="{x}" y="{y+5}" width="{xx-x}" height="{yy-y}" fill="white" fill-opacity=".67" stroke="#283747" stroke-width=".055"/>')
 s.append(f'<text x="{(x+xx)/2}" y="{(y+yy)/2+5+.18}" font-size=".48" font-weight="bold" text-anchor="middle">{p["ref"]}</text>')
s.append('<path d="M0,5 H20" stroke="#778492" stroke-width=".055" stroke-dasharray=".3,.2"/>')
s.append('<text x=".35" y="4.65" class="tiny">Old rear board edge after translation</text>')
s.append('<path d="M2.5,17.5 L10,2.5 L17.5,17.5 Z" stroke="#27724d" stroke-width=".045" stroke-dasharray=".24,.20" fill="none"/>')
s.append('<circle cx="10" cy="2.5" r="3.3" fill="#ef9a29" fill-opacity=".07" stroke="#db7a0d" stroke-width=".085" stroke-dasharray=".25,.12"/>')
for ref,(x,y) in zip(['H1','H2','H3'],d['proposal']['proposed_holes_xy_mm']):
 s.append(f'<circle cx="{x}" cy="{y}" r="1.2" fill="white" stroke="#1b4763" stroke-width=".075"/>')
 s.append(f'<path d="M{x-.35},{y} H{x+.35} M{x},{y-.35} V{y+.35}" stroke="#1b4763" stroke-width=".035"/>')
 s.append(f'<text x="{x}" y="{y+1.8}" font-size=".48" font-weight="bold" text-anchor="middle">{ref}</text>')
s.append('</g>')
lines=[('Proposed geometry','#192e48'),('Outline: 20 x 21 x 1.6 mm',None),('H1: (2.5, 17.5)  |  H2: (17.5, 17.5)',None),('H3: (10, 2.5), trial NPTH diameter 2.4',None),('Dashed orange: diameter 6.6 keepout',None),
 ('Required copper change','#a45805'),('Existing GND overlaps keepout by 0.299 mm.',None),('Trim about 0.554 mm2 on EACH copper face.',None),('Virtual cut preserves existing ground regions.',None),
 ('No signal reroute indicated','#19643b'),('Keepout to nearest trace: 2.664 mm',None),('Keepout to nearest pad: 2.108 mm',None),('Keepout to J1 Fab outline: 0.590 mm',None),
 ('Mechanical follow-up','#a45805'),('Board centre: (-25, -40) -> (-25, -42.5)',None),('Third support overhangs PCB edge by 0.8 mm.',None),('Hole-to-edge material: 1.3 mm.',None),('Fastener fit, stress and vibration: NOT_TESTED',None)]
y=142
for txt,color in lines:
 if color:y+=20
 s.append(f'<text x="665" y="{y}" font-size="{17 if color else 14}" font-weight="{"bold" if color else "normal"}" fill="{color or "#283747"}">{html.escape(txt)}</text>');y+=26
s.extend(['<text x="70" y="728" font-size="14">Two-layer native copper shown schematically; proposed holes drawn as diameter 2.4 mm.</text>',
 '<text x="70" y="752" font-size="14">Baseline ERC / DRC: PASS. Proposed-board ERC / DRC: NOT_TESTED. No manufacturing release.</text>','</svg>'])
svg = '\n'.join(s)
if withdrawn:
 svg = svg.replace('MORI IMU | 20 x 21 mm mounting proposal',
                   'WITHDRAWN | IMU three-point historical review')
 svg = svg.replace('P5R4 native copper translated by Y + 5 mm. Evaluation only; no new PCB saved.',
                   'Current design: original 20 x 16 mm, two holes. No board changes authorized by this proposal.')
(O/'proposal_overlay.svg').write_text(svg)
# Quick Look crops landscape SVG thumbnails to a square. Keep a separate
# square preview canvas so every annotation is visible in the PNG preview.
preview = svg.replace('width="1120" height="790" viewBox="0 0 1120 790"',
                      'width="1120" height="1120" viewBox="0 -165 1120 1120"', 1)
preview = preview.replace('<rect width="1120" height="790" fill="#f7f9fc"/>',
                          '<rect x="0" y="-165" width="1120" height="1120" fill="#f7f9fc"/>', 1)
(O/'proposal_preview.svg').write_text(preview)
print(O/'proposal_overlay.svg')
