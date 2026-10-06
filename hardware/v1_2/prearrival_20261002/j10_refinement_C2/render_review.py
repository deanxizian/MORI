"""Dimensioned candidate review, not a 3D model or a manufacturing drawing."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import numpy as np

HERE = Path(__file__).resolve().parent
old = json.loads((HERE / 'footprints_C1.json').read_text())
back = json.loads((HERE / 'backside_screen.json').read_text())
snap = json.loads((HERE / 'candidate_snapshot.json').read_text())
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9})
fig = plt.figure(figsize=(14, 8.5), facecolor='#f6f8fb')
gs = fig.add_gridspec(2, 2, width_ratios=[1.06, 1], height_ratios=[1, 1],
                      left=.055, right=.97, bottom=.11, top=.86, wspace=.26, hspace=.46)
ax = fig.add_subplot(gs[:, 0])
ax.set_facecolor('#f6f8fb')
for ref, f in old.items():
    bb = f['body']
    if not bb or ref in ['J10', 'D30', 'F70', 'R50', 'JP70', 'TP71']:
        continue
    x1, y1, x2, y2 = bb
    if x2 < 20 or x1 > 48 or y2 < 22 or y1 > 49:
        continue
    ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fc='#e7eaf0', ec='#a0a7b3', lw=.7))
    ax.text((x1+x2)/2, (y1+y2)/2, ref, ha='center', va='center', fontsize=7, color='#5c6575')
for row in back['backside_envelopes']:
    lo, hi = row['board_bounds_mm']
    ax.add_patch(Rectangle(lo[:2], hi[0]-lo[0], hi[1]-lo[1], fc='#c3e4e0', ec='#16897c',
                           linestyle='--', lw=1.2, alpha=.8))
    ax.text((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, row['reference']+'\nB.Cu',
            ha='center', va='center', color='#086356', fontsize=8)
# Socket is stationary; only the plug's envelope is withdrawn.
ax.add_patch(Rectangle((38.25,25.05),7.6,17.9,fc='#f9dfa0',ec='#aa7017',lw=1.7))
ax.text(45.3,34,'J10 fixed socket',rotation=90,ha='center',va='center',color='#825610')
ax.add_patch(Rectangle((36.25,25.1),6.85,17.8,fc='#bed6f7',ec='#356bba',lw=1.2,alpha=.72))
ax.add_patch(Rectangle((30.9,25.1),6.85,17.8,fill=False,ec='#356bba',lw=1.2,linestyle='--'))
ax.annotate('',xy=(30.9,23.7),xytext=(36.25,23.7),arrowprops=dict(arrowstyle='<->',color='#356bba'))
ax.text(33.58,23.35,'5.35 mm trial',ha='center',va='bottom',color='#356bba',fontsize=8)
for p in snap['footprints']['J10']['pads']:
    x,y=p['xy_mm'];ax.add_patch(Circle((x,y),.75,fc='#fff',ec='#aa7017'))
    ax.text(47.0,y,p['number'],va='center',ha='left',color='#364256')
ax.annotate('Wire exit / actual Z unknown',xy=(36.25,41.5),xytext=(22,47.7),
            arrowprops=dict(arrowstyle='->',color='#356bba'),fontsize=9,color='#356bba')
for ref in ['JP70','TP71']:
    f=snap['footprints'][ref];x,y=f['xy_mm']
    ax.scatter([x],[y],s=35,marker='+',color='#202d44')
    ax.text(x,y+.7,ref+' candidate',fontsize=8,ha='center')
ax.set(xlim=(20,49),ylim=(50,21.5),aspect='equal',xlabel='Native PCB X / mm',ylabel='Native PCB Y / mm')
ax.grid(alpha=.15)
ax.set_title('Placement and plug path\nSame numbered hole centres; component moves are candidates',loc='left',pad=15)

bx=fig.add_subplot(gs[0,1])
bx.set_title('Local underside envelopes / mm',loc='left',pad=14)
bx.add_patch(Rectangle((0,-1.6),16,1.6,fc='#334c50'))
bx.text(15.7,-.8,'PCB 1.6',ha='right',va='center',color='white',fontsize=9)
for x,width,depth,ref in [(1.4,4,2.65,'D30'),(8.2,4,3.09,'F70')]:
    bx.add_patch(Rectangle((x,-1.6-depth),width,depth,fc='#c3e4e0',ec='#16897c',lw=1.2))
    bx.text(x+width/2,-1.6-depth/2,ref+'\n'+str(depth),ha='center',va='center',color='#086356')
bx.axhline(-4.6,color='#9e6770',ls='--',lw=1)
bx.text(15.7,-4.82,'Old 3.00 mm underside allocation',ha='right',va='top',color='#9e6770',fontsize=8)
bx.text(.1,1.4,'F70: +0.09 beyond old allocation; local geometry reviewed.\nMax package + assumed 0.15 assembly allowance.\nHeat, solder tolerance and handling remain unqualified.',va='top',color='#4a5568')
bx.set(xlim=(0,16),ylim=(-6,1.8),aspect='equal');bx.set_axis_off()

cx=fig.add_subplot(gs[1,1])
cx.set_title('Named-wire static bend comparison',loc='left',pad=14)
for R,OD,name,color in [(10.922,1.0922,'Alpha 5853: R = 10D','#aa7017'),(5.08,1.016,'Alpha 6711: R = 5D','#356bba')]:
    a=np.linspace(0,np.pi/2,100)
    xx=np.r_[0,5,5+R*np.sin(a)]
    zz=np.r_[0,0,R*(1-np.cos(a))]
    cx.plot(xx,zz,lw=3,color=color,label=name)
    cx.text(5+R+.15,R,f'{R:g} mm',va='center',color=color,fontsize=8)
cx.axvline(5,color='#9aa3b0',ls=':',lw=1)
cx.text(2.5,1,'5 mm trial\nstraight exit',ha='center',fontsize=8,color='#576275')
cx.set(xlim=(-.5,20),ylim=(-1,13),xlabel='Distance from wire exit / mm',ylabel='Rise from wire exit / mm')
cx.grid(alpha=.15);cx.legend(loc='upper left',frameon=False,fontsize=8)
fig.suptitle('MORI J10 C2 | PLACEMENT STUDY',x=.055,ha='left',fontsize=20,color='#18314b',weight='bold',y=.975)
fig.text(.055,.913,'NOT A RELEASED PCB  •  26 unconnected items  •  14 DRC warnings  •  No manufacturing output',
         fontsize=11,color='#ae3434')
fig.text(.055,.04,'Nominal envelopes only. The 5.35 mm path is a geometric allocation, not a vendor extraction specification.\n'
         '6711 is an unselected wire candidate. Crimp exit height, clearance, full harness, tool access and final routing remain BLOCKED.',
         fontsize=9,color='#576275')
fig.savefig(HERE/'J10_C2_review.png',dpi=170,facecolor=fig.get_facecolor())
plt.close(fig)
