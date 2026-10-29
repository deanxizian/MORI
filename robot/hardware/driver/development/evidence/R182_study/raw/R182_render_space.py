"""Render exact native board/footprint geometry for an unadopted outline comparison.

Copper fills hidden for clarity. Same native XY view on both faces (not mirrored
underside assembly views). No geometry is synthesized from a photograph.
"""
import ast, hashlib, html, json, sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
out=b/'R182-space-comparison';out.mkdir(exist_ok=True)
assert not any(out.iterdir()), 'Never overwrite a completed comparison'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
proposal=Copper(b/'R182I/MORI_Interface_C3.kicad_pcb')
check=json.loads((b/'R182I-space-check.json').read_text())
assert source.sha==check['source_sha256'] and proposal.sha==check['proposal_sha256']
W,H=1680,1160
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
     '<rect width="1680" height="1160" fill="#f4f6f9"/>']
def txt(x,y,value,size=18,color='#23364a',anchor='start'):
    svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(value)}</text>')
def draw(g,color,alpha=1,stroke=None,width=.02):
    for p in parts(g):
        rings=[p.exterior]+list(p.interiors)
        d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in r.coords)+' Z' for r in rings)
        svg.append(f'<path d="{d}" fill="{color}" fill-opacity="{alpha}" stroke="{stroke or color}" stroke-width="{width}" fill-rule="evenodd"/>')
txt(40,38,'MORI C3 | board space comparison',28)
txt(40,66,'Native geometry, equal scale | two outer faces | copper fills hidden | proposal NOT adopted',17,'#5e6c7c')
txt(40,101,'R181C / CURRENT DEVELOPMENT',21)
txt(880,101,'R182I / INDEPENDENT SPACE PROPOSAL',21,'#9b4e0d')
txt(40,129,'70 x 35 x 1.6 mm | 19 open items | 0 other DRC',17)
txt(880,129,f'70 x 40 x 1.6 mm | {check["unconnected_items"]} open items | {check["other_DRC"]} other DRC',17,'#9b4e0d')
for col,c in enumerate([source,proposal]):
    depth=35 if col==0 else 40
    for row,face in enumerate(['F.Cu','B.Cu']):
        x0=42+col*840;y0=196+row*468;scale=10.3
        txt(x0,y0-19,face+' — native XY (not mirrored)',18)
        svg.append(f'<g transform="translate({x0},{y0}) scale({scale})">')
        draw(box(0,0,70,depth),'#ffffff',1,'#273c4f',.1)
        if col:
            draw(box(0,35,70,40),'#ffdb98',.65)
            svg.append('<path d="M0,35 L70,35" stroke="#bd6c14" stroke-width=".10" stroke-dasharray=".7 .4"/>')
        for t in c.segments:
            if c.board.GetLayerName(t.GetLayer())==face:draw(c.shapes[uid(t),face],'#79899b',.48)
        for f in c.footprints:
            if c.board.GetLayerName(f.GetLayer())!=face:continue
            ref=f.GetReference();focus=ref in ['U301','C301']
            color='#e47324' if focus else ('#597488' if ref.startswith('J') else '#4c8ba9')
            draw(outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd),color,.15,color,.014)
            draw(fab(f),color,.56)
            for p in f.Pads():
                g=c.shapes.get((uid(p),face))
                if g is not None:draw(g,'#ba864b',.8)
            if focus:
                x,y=xy(f.GetPosition())
                svg.append(f'<circle cx="{x}" cy="{y}" r="2.1" fill="none" stroke="#c84d13" stroke-width=".12"/>')
                txt(x,y-2.4,ref,.9,'#9e3708','middle')
            elif ref.startswith('J'):
                x,y=xy(f.GetPosition());txt(x,y,ref,.68,'#142d43','middle')
        for v in c.vias:
            x,y=xy(v.GetPosition());color='#138663' if v.GetNetname()=='GND' else '#657487'
            svg.append(f'<circle cx="{x}" cy="{y}" r=".22" fill="{color}"/><circle cx="{x}" cy="{y}" r=".13" fill="#fff"/>')
        for f in c.footprints:
            if not f.GetReference().startswith('H'):continue
            for p in f.Pads():
                x,y=xy(p.GetPosition());r=p.GetDrillSize().x/2e6
                svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f4f6f9" stroke="#1b3144" stroke-width=".12"/>')
        # Dimension lines use the actual outline endpoints, at identical scales.
        svg.append(f'<path d="M0,{depth+.9} L70,{depth+.9} M0,{depth+.4} L0,{depth+1.4} M70,{depth+.4} L70,{depth+1.4}" stroke="#546579" stroke-width=".08"/>')
        txt(35,depth+2.2,'70 mm',.95,'#45586b','middle')
        svg.append(f'<path d="M72,0 L72,{depth} M71.5,0 L72.5,0 M71.5,{depth} L72.5,{depth}" stroke="#546579" stroke-width=".08"/>')
        txt(72.7,depth/2,str(depth)+' mm',.85,'#45586b')
        if col:
            txt(48,38.2,'+5 mm / +350 mm2',1.1,'#8b4e0b','middle')
            if row==0:txt(48,39.5,'NO POWER / GROUND PLANE ADDED',.68,'#8b4e0b','middle')
        svg.append('</g>')
txt(40,1118,'Fixed in proposal: 4 mounts, 9 connectors, 68 core pins, 324 vias, all other 213 footprints.',17)
txt(40,1144,'Only U301/C301 moved; 18 old terminal traces released. Unrouted, no fit/strength/EMC qualification. No manufacturing release.',16,'#9b4e0d')
svg.append('</svg>')
(out/'comparison.svg').write_text('\n'.join(svg))
(out/'manifest.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=source.sha,proposal_sha256=proposal.sha,
  source_outline_mm=[70,35],proposal_outline_mm=[70,40],same_scale=True,faces=['F.Cu','B.Cu'],
  image_is_native_geometry_diagnostic=True,adopted=False,manufacturing_release=False),indent=2)+'\n')
print(str(out/'comparison.svg'))
