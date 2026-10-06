"""Read-only, source-hashed copper review atlas. No KiCad file writes.

Track widths use millimetres in plot space, not an arbitrary screen width.
Fab rectangles come from native geometry; pad round corners are simplified.
Native DRC remains the check of exact pad/copper clearance.
"""
from pathlib import Path
import json, hashlib, math, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib import transforms

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SRC=ROOT/'hardware/v1_2/j10_routing_C3_20261002'
G=json.loads((SRC/'reports/FINAL_geometry.json').read_text())
INV=json.loads((SRC/'reports/after_inventory.json').read_text())
FLAGS=json.loads((SRC/'reports/changed_route_flags.json').read_text())['flags']
PCB=SRC/'MORI_power_J10_C3_CANDIDATE/MORI_power_J10_C3_CANDIDATE.kicad_pcb'
assert hashlib.sha256(PCB.read_bytes()).hexdigest()==G['sha256']==INV['sha256']
OUT=HERE/'images';OUT.mkdir(parents=True,exist_ok=True)
BG='#101f2c'

def capsule(ax,a,b,w,col,alpha=1):
    dx,dy=b[0]-a[0],b[1]-a[1];d=math.hypot(dx,dy)
    if d:
        n=(-dy*w/(2*d),dx*w/(2*d))
        ax.add_patch(Polygon([(a[0]+n[0],a[1]+n[1]),(b[0]+n[0],b[1]+n[1]),(b[0]-n[0],b[1]-n[1]),(a[0]-n[0],a[1]-n[1])],fc=col,ec='none',alpha=alpha))
    for p in [a,b]:ax.add_patch(Circle(p,w/2,fc=col,ec='none',alpha=alpha))

def draw(ax,layer,bounds,net=None,marks=(),title=''):
    x1,x2,y1,y2=bounds;ax.set_facecolor(BG)
    for ref,f in G['footprints'].items():
        if f['body']:
            a,b,c,d=f['body']
            if c>=x1 and a<=x2 and d>=y1 and b<=y2:
                ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,ec='#bbcbbc' if f['layer']==layer else '#516574',ls='-'if f['layer']==layer else '--',lw=.7))
    for t in G['tracks']:
        if t['via']:continue
        if t['layer']!=layer:continue
        col='#fd8178'if layer=='F.Cu'else '#79bfff'
        if net:col='#ffdd55'if t['net']==net else '#476176'
        capsule(ax,t['start'],t['end'],t['width'],col)
    for t in G['tracks']:
        if not t['via']:continue
        ax.add_patch(Circle(t['start'],t['width']/2,fc='#b1a4dc'if not net or t['net']==net else '#596271',ec='#d3c7fb',lw=.3))
        ax.add_patch(Circle(t['start'],.1,fc=BG))
    for ref,f in G['footprints'].items():
        for p in f['pads']:
            if layer not in p['layers']:continue
            x,y=p['xy'];w,h=p['size'];tr=transforms.Affine2D().rotate_deg_around(x,y,-p['rotation'])+ax.transData
            col='#d2a243' if not net or p['net']==net else '#706549'
            if p['shape']==0:ax.add_patch(Circle((x,y),w/2,fc=col,ec='#f1dc9f',lw=.35))
            else:ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc=col,ec='#f1dc9f',lw=.35,transform=tr))
            if p['drill'][0]:ax.add_patch(Circle((x,y),p['drill'][0]/2,fc=BG))
            if x1<=x<=x2 and y1<=y<=y2:ax.text(x,y,p['number'],fontsize=6,color='white',ha='center',va='center',clip_on=True)
        x,y=f['xy']
        if x1<=x<=x2 and y1<=y<=y2:ax.text(x,y,ref,fontsize=8,color='white',ha='center',va='center',clip_on=True,bbox=dict(fc=BG,ec='none',alpha=.8,pad=.7))
    for x,y,label in marks:
        ax.add_patch(Circle((x,y),.36,fc='none',ec='#fff',lw=1.1));ax.text(x+.45,y-.35,label,fontsize=7,color='white',clip_on=True)
    ax.set(xlim=(x1,x2),ylim=(y2,y1),aspect='equal');ax.tick_params(colors='#c8d6e3',labelsize=7);ax.grid(alpha=.14);ax.set_title(title,fontsize=10,color='white')

def create():
    groups=[]
    for f in FLAGS:
        found=next((g for g in groups if g['net']==f['net'] and g['layer']==f['layer'] and math.dist(g['xy'],f['xy'])<1.6),None)
        if found:found['flags'].append(f)
        else:groups.append({'net':f['net'],'layer':f['layer'],'xy':f['xy'],'flags':[f]})
    for n in range(0,len(groups),6):
        fig,axs=plt.subplots(2,3,figsize=(18,12));fig.patch.set_facecolor(BG)
        for ax,g in zip(axs.flat,groups[n:n+6]):
            x,y=g['xy'];ids=','.join(f['id'] for f in g['flags']);g['image']=f'flags_{n//6+1:02d}.png';g['panel']=ids
            draw(ax,g['layer'],[x-3.2,x+3.2,y-3.2,y+3.2],g['net'],[(x,y,'')],ids+' '+g['net']+' '+g['layer'])
        for ax in list(axs.flat)[len(groups[n:n+6]):]:ax.axis('off')
        fig.tight_layout();fig.savefig(OUT/f'flags_{n//6+1:02d}.png',dpi=145);plt.close(fig)
    tiles=[]
    for layer in ['F.Cu','B.Cu']:
        for row,(a,b) in enumerate([(0,29),(26,55)]):
            for col,(x,y) in enumerate([(0,29),(26,55),(52,80)]):
                name=f'tile_{layer.replace(".","_")}_{row+1}{col+1}.png';fig,ax=plt.subplots(figsize=(12,12));fig.patch.set_facecolor(BG)
                draw(ax,layer,[x,y,a,b],title=name+' / solid body=this side, dashed=opposite')
                fig.tight_layout();fig.savefig(OUT/name,dpi=140);plt.close(fig)
                tiles.append({'image':name,'layer':layer,'bounds':[x,y,a,b]})
    old=[f for f in INV['candidates'] if f['type'] in ['FOLDBACK','OVERLAP_PARALLEL']]
    for n in range(0,len(old),6):
        fig,axs=plt.subplots(2,3,figsize=(18,12));fig.patch.set_facecolor(BG)
        for ax,f in zip(axs.flat,old[n:n+6]):
            x,y=f['xy'];draw(ax,f['layer'],[x-2.4,x+2.4,y-2.4,y+2.4],f['net'],[(x,y,'')],f['id']+' '+f['type']+' '+f['net'])
        for ax in list(axs.flat)[len(old[n:n+6]):]:ax.axis('off')
        fig.tight_layout();fig.savefig(OUT/f'legacy_flags_{n//6+1:02d}.png',dpi=145);plt.close(fig)
    (HERE/'atlas_index.json').write_text(json.dumps({'source_sha256':G['sha256'],'groups':groups,'tiles':tiles,'legacy_flags':old},ensure_ascii=False,indent=2))
    print('Rendered',len(groups),'flag groups,',len(tiles),'whole-board tiles,',len(old),'legacy flags')

if __name__=='__main__':create()
