"""Plot actual received component projections and conservative side-entry sweep."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
p=json.loads((PROJECT/'config/geometry.json').read_text())
cache=json.loads((PROJECT/p['native_electronics']['boards']['power']['mesh']).read_text())
result=json.loads((HERE/'J10_A2_envelope_review.json').read_text())
hit={v['object'].removeprefix('Power/') for row in result['unplug_blocked_samples'] for v in row['overlaps']}
fig,axes=plt.subplots(1,2,figsize=(11,7),constrained_layout=True)
for ax,title in zip(axes,['Fully mated envelope','Conservative 12 mm unplug sweep']):
    ax.set(xlim=(20,50),ylim=(50,18),aspect='equal',title=title,xlabel='Native PCB X (mm)',ylabel='Native PCB Y (mm)')
    ax.grid(alpha=.15)
    for c in cache['components']:
        if c['reference'] in ['PCB','J10']:continue
        b=c['bounds_xyz_mm'];lo=[b[0][0],-b[1][1]];size=[b[0][1]-b[0][0],b[1][1]-b[1][0]]
        if lo[0]>50 or lo[0]+size[0]<20 or lo[1]>50 or lo[1]+size[1]<18:continue
        colour='#9e432e' if c['reference'] in hit else '#758c88'
        ax.add_patch(Rectangle(lo,*size,facecolor=colour,edgecolor=colour,alpha=.22))
        if c['reference'] in hit or c['reference'] in ['R50','JP70']:
            ax.text(lo[0]+size[0]/2,lo[1]+size[1]/2,c['reference'],ha='center',va='center',fontsize=7,color='#263a36')
    for i in range(8):ax.plot(44.5,27+2*i,'o',color='#17392f',markersize=3)
    ax.add_patch(Rectangle((38.25,25.05),7.6,17.9,fill=False,edgecolor='#176553',lw=1.7,label='Socket body'))
    ax.annotate('Exit / unplug',xy=(29,23),xytext=(43,23),arrowprops={'arrowstyle':'->','color':'#176553'},ha='right',color='#176553',fontsize=9)
axes[0].add_patch(Rectangle((36.25,25.05),9.6,17.9,fill=False,edgecolor='#bb7b1d',lw=2,label='Mated box'))
axes[0].add_patch(Rectangle((31.25,25.05),5,17.9,fill=False,edgecolor='#bb7b1d',ls=':',lw=1.5,label='5 mm exit allocation'))
axes[1].add_patch(Rectangle((24.25,25.05),21.6,17.9,facecolor='#e6be7d',alpha=.16,edgecolor='#bb7b1d',lw=2,label='Whole-box swept region'))
for ax in axes:ax.legend(loc='lower left',fontsize=7)
fig.suptitle('J10 side-entry C1 / M1.47: not adopted',fontsize=14)
fig.text(.5,.012,'PCB top view; bounds are conservative envelopes, not detailed connector solids. All dimensions remain unchanged.',ha='center',fontsize=8)
fig.savefig(HERE/'J10_A2_envelopes.png',dpi=170)
plt.close(fig)
