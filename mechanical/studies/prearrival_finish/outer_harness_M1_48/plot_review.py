"""Plots of recorded curves and native solid sections; no image editing."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'packing.json').read_text())
sections=json.loads((HERE/'sections.json').read_text())
curves=np.load(HERE/'packed_curves.npz')
upper=np.load(HERE/'upper_entry_curves.npz')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#f5f7f6',
                     'axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
colors={1:'#cc550d',2:'#226f87',3:'#8063a6',4:'#568033'}

fig,ax=plt.subplots(figsize=(10,9),constrained_layout=True)
for r in d['selected']:
    pin=r['pin'];p=curves[f'pin{pin}']
    ax.plot(p[:,0],p[:,1],color=colors[pin],lw=2,label=f'J5.{pin} - {r["analytic_body_neck_length_mm"]:.1f} mm partial path')
    ax.scatter(*p[0,:2],s=42,color=colors[pin],zorder=8)
    ax.scatter(*p[-1,:2],s=70,facecolor='white',edgecolor=colors[pin],linewidth=2,zorder=8)
    ax.annotate(f'{pin}',xy=p[0,:2],xytext=(p[0,0],p[0,1]-4.5),ha='center',color=colors[pin],fontsize=12)
    offset=np.sign(p[-1,:2])*3
    ax.annotate(f'J5.{pin}',xy=p[-1,:2],xytext=p[-1,:2]+offset,color=colors[pin],fontsize=11)
ax.text(18.5,-55,'Native J5 pin order unchanged',ha='center',color='#374d48')
ax.set(xlim=(-41,48),ylim=(-60,41),xlabel='X / mm',ylabel='Y / mm  (+Y front)',
       title='Four simultaneous body-to-neck candidates\nPlan projection only: open circles are unconnected upper ends')
ax.set_aspect('equal');ax.grid(alpha=.17);ax.legend(loc='upper left',fontsize=9)
fig.savefig(HERE/'routes_plan.png',dpi=165);plt.close(fig)

def fill(ax,polygons,color,label):
    vertices=[];codes=[]
    for p in polygons:
        p=np.asarray(p)*[1.,-1.]
        if len(p)<3:continue
        vertices.extend(p.tolist()+[p[0].tolist()])
        codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY])
    if vertices:ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,edgecolor='#53625c',lw=.5,label=label))

fig,axs=plt.subplots(1,2,figsize=(12.5,8),constrained_layout=True)
r=next(r for r in d['selected'] if r['pin']==3)
native=sections['radial'][str(r['azimuth_deg'])]
part_colors={'Body_Upper':'#dce0da','Yaw_Base':'#90a4a1','Yaw_Bearing':'#ccd2d5',
             'Yaw_Reaction_Link':'#a7adc4','Pitch_Yoke':'#e3c18d','Head_Front':'#eee9db'}
for ax in axs:
    for n,color in part_colors.items():fill(ax,native[n],color,n)
    p=curves['pin3'][r['prefix_points']-1:]
    radius=np.linalg.norm(p[:,:2],axis=1)
    ax.plot(radius,p[:,2],lw=3,color='#226f87',label='Verified fixed local portion')
    ax.scatter(radius[-1],p[-1,2],s=85,facecolor='white',edgecolor='#226f87',lw=2,zorder=10)
    ax.set(xlim=(0,42),ylim=(137,199),xlabel='Radial coordinate / mm',ylabel='Height Z / mm')
    ax.set_aspect('equal');ax.grid(alpha=.16)
axs[0].set_title('Current M1.48 solids: fixed portion passes')
axs[0].annotate('Upper end still open',xy=(29.6,168),xytext=(17,164),
                color='#226f87',arrowprops={'arrowstyle':'->','color':'#226f87'})
axs[0].legend(loc='upper right',fontsize=8)
q=upper['pin3'];rad=np.linalg.norm(q[:,:2],axis=1)
axs[1].plot(rad,q[:,2],color='#bd4642',lw=2.3,linestyle='--',label='Rejected direct upward continuation')
axs[1].set_title('A straight inner continuation is not viable')
axs[1].annotate('Needs a different continuation',xy=(6.8,188.4),xytext=(15,196),
                color='#aa3532',arrowprops={'arrowstyle':'->','color':'#aa3532'})
axs[1].legend(loc='lower left',fontsize=8)
fig.suptitle('Native radial section at 45 degrees\nNo material removed; upper yaw/pitch service loops and assembly remain unresolved',fontsize=14)
fig.savefig(HERE/'neck_connection.png',dpi=165);plt.close(fig)
print('OUTER_REVIEW_FIGURES_DONE')
