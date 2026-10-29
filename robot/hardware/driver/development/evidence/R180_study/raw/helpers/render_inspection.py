"""Render an explicitly labelled native-geometry diagnostic SVG (not a screenshot)."""
import argparse
import html
from pathlib import Path
from copper_geometry import *
from shapely.geometry import box


def render(board, layer, bounds, output, highlight=None):
    c=Copper(board);x0,y0,x1,y1=bounds;window=box(*bounds)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="{1400*(y1-y0)/(x1-x0)}" viewBox="{x0} {y0} {x1-x0} {y1-y0}">',
         f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#171b22"/>']
    def draw(g,color,opacity=1,stroke=None):
        g=g.intersection(window)
        for p in parts(g):
            rings=[p.exterior]+list(p.interiors)
            d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in r.coords)+' Z' for r in rings)
            out.append(f'<path d="{d}" fill="{color}" fill-opacity="{opacity}" stroke="{stroke or color}" stroke-width="0.015" fill-rule="evenodd"/>')
    for net,ly,g in c.fills:
        if ly==layer:draw(g,'#2b5e50' if net=='GND' else '#456470',.75)
    for k in c.keepouts:
        if layer in k['layers'] and k['tracks']:draw(k['shape'],'#8b3c3c',.16,'#874448')
    for (id_,ly),g in c.shapes.items():
        if ly!=layer or not g.intersects(window):continue
        o=c.by_id[id_];color='#ffe05b' if o.GetNetname()==highlight else ('#74dca0' if o.GetNetname()=='GND' else '#c99468')
        draw(g,color,.95)
        if isinstance(o,pcb.PCB_VIA):
            x,y=xy(o.GetPosition());out.append(f'<circle cx="{x}" cy="{y}" r="{o.GetDrillValue()/2e6}" fill="#171b22"/>')
        if isinstance(o,pcb.PAD):
            x,y=xy(o.GetPosition());name=html.escape(c.pad_name(o));out.append(f'<text x="{x}" y="{y}" fill="#fff" font-size="0.22" text-anchor="middle">{name}</text>')
    for f in c.footprints:
        if c.board.GetLayerName(f.GetLayer())==layer and window.contains(Point(xy(f.GetPosition()))):
            x,y=xy(f.GetPosition());out.append(f'<text x="{x}" y="{y}" fill="#88c4ff" font-size="0.35" text-anchor="middle">{html.escape(f.GetReference())}</text>')
    for x in range(int(x0)+1,int(x1)+1):
        out.append(f'<path d="M{x},{y0} L{x},{y1}" stroke="#a0a0a0" stroke-width="0.008" opacity=".4"/>')
        out.append(f'<text x="{x+.03}" y="{y0+.25}" fill="#aaa" font-size=".22">{x}</text>')
    for y in range(int(y0)+1,int(y1)+1):
        out.append(f'<path d="M{x0},{y} L{x1},{y}" stroke="#a0a0a0" stroke-width="0.008" opacity=".4"/>')
        out.append(f'<text x="{x0+.03}" y="{y-.03}" fill="#aaa" font-size=".22">{y}</text>')
    out.append('</svg>');Path(output).write_text('\n'.join(out))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('board');p.add_argument('layer');p.add_argument('bounds',nargs=4,type=float);p.add_argument('output');p.add_argument('--highlight');a=p.parse_args();render(a.board,a.layer,a.bounds,a.output,a.highlight)
