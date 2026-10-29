"""Propose a simple surface route without moving or saving any board items.

An eight-direction grid search penalizes bends. Actual native keepouts, copper
clearances and continuous adjacent ground restrict the search. Output is a trial
plan requiring KiCad DRC, copper regression and visual review, never an adoption.
"""
import argparse
import heapq
import json
import math
from pathlib import Path
import numpy as np
from shapely import intersects_xy, contains_xy
from shapely.geometry import box
from shapely.prepared import prep
from copper_geometry import *


def plan(board, from_pad, to_pad, layer, width, output, revision, margin=5.0, grid=.1):
    c=Copper(board)
    pads=defaultdict(list)
    for p in c.pads:pads[c.pad_name(p)].append(p)
    a,b=pads[from_pad][0],pads[to_pad][0]
    assert a.GetNetname()==b.GetNetname()
    net=a.GetNetname();assert layer in ['F.Cu','B.Cu']
    sa=unary_union([c.shapes[(uid(p),layer)] for p in pads[from_pad] if (uid(p),layer) in c.shapes])
    sb=unary_union([c.shapes[(uid(p),layer)] for p in pads[to_pad] if (uid(p),layer) in c.shapes])
    obstacles=[]
    for (id_,ly),s in c.shapes.items():
        if ly==layer and c.by_id[id_].GetNetname()!=net:
            obstacles.append(s.buffer(.205+width/2))
    for k in c.keepouts:
        if layer in k['layers'] and k['tracks']:
            obstacles.append(k['shape'].buffer(width/2+.005))
    blocked=unary_union(obstacles)
    reference=c.copper[('GND',REFERENCE[layer])]
    # Existing same-net lands are not new routing area; explicit plated transfer
    # antipads are exempted locally. No other net's plane void is exempted.
    lands=[s for (id_,ly),s in c.shapes.items() if ly==layer and isinstance(c.by_id[id_],pcb.PAD) and c.by_id[id_].GetNetname()==net]
    transfers=[Point(xy(p.GetPosition())).buffer(.655) for p in c.vias if p.GetNetname()==net]
    allowed=unary_union([reference]+lands+transfers).buffer(-width/2)
    minx,miny,maxx,maxy=sa.union(sb).bounds
    x0=max(.505+width/2,math.floor((minx-margin)/grid)*grid)
    y0=max(.505+width/2,math.floor((miny-margin)/grid)*grid)
    x1=min(69.495-width/2,maxx+margin);y1=min(34.495-width/2,maxy+margin)
    xs=np.arange(x0,x1+1e-9,grid);ys=np.arange(y0,y1+1e-9,grid)
    xx,yy=np.meshgrid(xs,ys)
    free=~intersects_xy(blocked,xx,yy) & contains_xy(allowed,xx,yy)
    startmask=contains_xy(sa.buffer(-width/2-.005),xx,yy)&free
    endmask=contains_xy(sb.buffer(-width/2-.005),xx,yy)&free
    starts=list(zip(*np.where(startmask)));goals=set(zip(*np.where(endmask)))
    if not starts or not goals:
        print(json.dumps({'status':'NO_ENDPOINT_ACCESS','start_grid_points':len(starts),'end_grid_points':len(goals)}));return
    obstacle_test=prep(blocked);allowed_test=prep(allowed)
    def clear(p,q):
        line=LineString([p,q]);return not obstacle_test.intersects(line) and allowed_test.covers(line)
    def point(node):return (float(xs[node[1]]),float(ys[node[0]]))
    directions=[(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)]
    target=np.array(xy(b.GetPosition()));cost={};parent={};queue=[];seq=0
    for y,x in starts:
        key=(int(y),int(x),8);cost[key]=0.;heapq.heappush(queue,(math.dist(point(key),target),seq,key));seq+=1
    found=None;expanded=0
    while queue:
        _,_,key=heapq.heappop(queue);y,x,d=key;g=cost[key]
        if (y,x) in goals:found=key;break
        expanded+=1
        for nd,(dy,dx) in enumerate(directions):
            ny,nx=y+dy,x+dx
            if not (0<=ny<len(ys) and 0<=nx<len(xs) and free[ny,nx]):continue
            if d!=8 and min((nd-d)%8,(d-nd)%8)>2:continue
            nxt=(ny,nx,nd);step=grid*(math.sqrt(2) if dx and dy else 1)
            ng=g+step+(0.45 if d!=8 and d!=nd else 0)
            if ng>=cost.get(nxt,float('inf')):continue
            if not clear(point(key),point(nxt)):continue
            cost[nxt]=ng;parent[nxt]=key
            heapq.heappush(queue,(ng+max(0,math.dist(point(nxt),target)-max(sb.bounds[2]-sb.bounds[0],sb.bounds[3]-sb.bounds[1])),seq,nxt));seq+=1
    if found is None:
        print(json.dumps({'status':'NO_PATH_IN_SEARCH','expanded':expanded,'grid_mm':grid,'margin_mm':margin}));return
    path=[found]
    while path[-1] in parent:path.append(parent[path[-1]])
    path.reverse();pts=[point(n) for n in path]
    # Remove collinear points only; do not introduce arbitrary shortcut angles.
    simplified=[pts[0]]
    for i in range(1,len(pts)-1):
        u=np.subtract(pts[i],simplified[-1]);v=np.subtract(pts[i+1],pts[i])
        if abs(u[0]*v[1]-u[1]*v[0])>1e-8:simplified.append(pts[i])
    simplified.append(pts[-1]);simplified=[[round(x,6),round(y,6)] for x,y in simplified]
    result={'revision':revision,'scope':'Independent route proposal; native and visual verification required',
            'routes':[{'net':net,'layer':layer,'width_mm':width,'points_mm':simplified,'from_pad':from_pad,'to_pad':to_pad}],
            'search':{'grid_mm':grid,'margin_mm':margin,'expanded':expanded,'length_mm':sum(math.dist(x,y) for x,y in zip(simplified,simplified[1:]))}}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('board');p.add_argument('from_pad');p.add_argument('to_pad');p.add_argument('layer');p.add_argument('width',type=float);p.add_argument('output');p.add_argument('revision');p.add_argument('--margin',type=float,default=5);p.add_argument('--grid',type=float,default=.1);a=p.parse_args();plan(a.board,a.from_pad,a.to_pad,a.layer,a.width,a.output,a.revision,a.margin,a.grid)
