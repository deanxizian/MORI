"""Review geometry exported from native KiCad; planes hidden intentionally."""
import sys,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,Polygon
from matplotlib import transforms
HERE=Path(__file__).resolve().parent
label=sys.argv[1];g=json.loads((HERE/'reports'/(label+'_geometry.json')).read_text())
limits=list(map(float,sys.argv[2:6]))if len(sys.argv)>2 else [0,80,0,55]
for layer in ['F.Cu','B.Cu']:
 fig,ax=plt.subplots(figsize=(16,11));ax.set_facecolor('#0c1b29');fig.patch.set_facecolor('#0c1b29')
 for zone in g['areas']:
  if layer in zone['layers']and zone['name'].startswith('BODY_'):
   for pts in zone['polys']:ax.add_patch(Polygon(pts,fc='#384454',ec='#667080',lw=.3,alpha=.5))
 for t in g['tracks']:
  c='#ff6664'if layer=='F.Cu'else '#63b5ff'
  if t['via']:
   ax.add_patch(Circle(t['start'],t['width']/2,fc='#ad9cdf',ec='#d9cff8',lw=.3))
  elif t['layer']==layer:ax.plot([t['start'][0],t['end'][0]],[t['start'][1],t['end'][1]],color=c,lw=t['width']*4,solid_capstyle='round')
 for ref,f in g['footprints'].items():
  if f['body']:
   x1,y1,x2,y2=f['body'];ax.add_patch(Rectangle((x1,y1),x2-x1,y2-y1,fill=False,ec='#779587'if f['layer']==layer else '#485664',ls='-'if f['layer']==layer else '--',lw=.6))
  for p in f['pads']:
   if layer not in p['layers']:continue
   x,y=p['xy'];w,h=p['size'];tr=transforms.Affine2D().rotate_deg_around(x,y,-p['rotation'])+ax.transData
   ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc='#cba145',ec='#ffdfa0',lw=.4,transform=tr))
   if p['drill'][0]:ax.add_patch(Circle((x,y),p['drill'][0]/2,fc='#0c1b29'))
   ax.text(x,y,p['number'],fontsize=5,color='white',ha='center',va='center',clip_on=True)
  x,y=f['xy'];ax.text(x,y,ref,fontsize=7,color='#f1f5f9',ha='center',va='center',clip_on=True,bbox=dict(fc='#122333',ec='none',alpha=.7,pad=.4))
 ax.set(xlim=limits[:2],ylim=[limits[3],limits[2]],aspect='equal');ax.tick_params(colors='white');ax.grid(alpha=.12);ax.set_title(f'{label} | {layer} | native coordinates (mm), planes hidden',color='white')
 fig.savefig(HERE/'reports'/(label+'_'+layer.replace('.','_')+'.png'),dpi=140,bbox_inches='tight');plt.close(fig)
