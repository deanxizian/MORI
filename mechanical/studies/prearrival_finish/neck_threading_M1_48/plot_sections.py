"""Plot exported solid sections; no model changes or image editing."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'section_inputs.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#f6f8f7',
                     'axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
colors={'Yaw_Base':'#748c8d','Yaw_Bearing':'#b8c2c9','Yaw_Reaction_Link':'#8d96b4',
        'Pitch_Yoke':'#d7ae71','Head_Lower_Guard':'#ddd9d1','Body_Upper':'#cccfc9',
        'Load_Frame':'#b8c0b1','Yaw_Keeper':'#9baa83'}
def fill(ax,polygons,color,label=None,radial=False,alpha=1):
    verts=[];codes=[]
    for p in polygons:
        p=np.asarray(p,float)
        if len(p)<3:continue
        if radial:p=p*np.array([1.,-1.])
        verts.extend(p.tolist()+[p[0].tolist()]);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY])
    if verts:ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor='#465454',linewidth=.55,alpha=alpha,label=label))

fig,axs=plt.subplots(1,2,figsize=(12,7.5),constrained_layout=True)
q=d['radial']['45']
theta=np.linspace(0,np.pi/2,361);curve=np.column_stack([14.8-8*np.sin(theta),139+8*(1-np.cos(theta))])
curve=np.vstack([[25.,139.],curve,[6.8,163.]])
for ax,part,title in zip(axs,['Yaw_Base','candidate_Yaw_Base'],['CURRENT MAIN - M1.48','UNADOPTED CUT-CHANNEL CANDIDATE']):
    fill(ax,q[part],colors['Yaw_Base'],'Bridge',True)
    fill(ax,q['Yaw_Bearing'],colors['Yaw_Bearing'],'Bearing',True)
    fill(ax,q['Yaw_Reaction_Link'],colors['Yaw_Reaction_Link'],'Reaction link',True)
    ax.plot(curve[:,0],curve[:,1],color='#c53f39',linewidth=2.8,label='Recorded R8 wire centreline')
    ax.axvline(1.8,linestyle=':',color='#597f99',linewidth=.9)
    ax.set(xlim=(0,25),ylim=(136.5,164),xlabel='Radial coordinate r / mm',ylabel='Height Z / mm',title=title)
    ax.set_aspect('equal');ax.grid(alpha=.15)
axs[0].annotate('Wire centre enters solid',xy=(8.997,141.493),xytext=(12,145.1),
                arrowprops={'arrowstyle':'->','color':'#c53f39'},color='#a72621',fontsize=10)
axs[1].annotate('Unapproved channel\nwas loaded by old study',xy=(7.3,143.5),xytext=(11,144.6),
                arrowprops={'arrowstyle':'->','color':'#9b6400'},color='#9b6400',fontsize=10)
axs[0].legend(loc='upper right',fontsize=8)
fig.suptitle('Lower neck: actual section at 45 degrees\nGeometric diagnosis only; terminal sizes and full harness remain unresolved',fontsize=15)
fig.savefig(HERE/'bridge_comparison.png',dpi=170);plt.close(fig)

fig,ax=plt.subplots(figsize=(12,8),constrained_layout=True)
for n in ['Body_Upper','Load_Frame','Head_Lower_Guard','Yaw_Base','Yaw_Bearing','Yaw_Keeper','Pitch_Yoke','Yaw_Reaction_Link']:
    if n in q:fill(ax,q[n],colors[n],n,True)
ax.plot(curve[:,0],curve[:,1],color='#c53f39',linewidth=2.4,label='Recorded R8 centreline')
ax.set(xlim=(-57,57),ylim=(132,203),xlabel='Radial coordinate / mm',ylabel='Height Z / mm',title='Current M1.48 section at 45 degrees - no study channels')
ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='upper left',fontsize=9)
fig.savefig(HERE/'native_neck_context.png',dpi=170);plt.close(fig)

outer_path=HERE/'outer_corridor_curves.npz'
outer_report=HERE/'outer_corridor_screen.json'
if outer_path.exists() and outer_report.exists():
    r=json.loads(outer_report.read_text())
    selected=next(x for x in r['passing'] if x['angle_deg']==45 and x['outer_radius_mm']==37.6
                  and x['lower_z_mm']==137. and x['upper_bend_start_z_mm']==160.)
    c=np.load(outer_path)[selected['curve_key']]
    fig,ax=plt.subplots(figsize=(9,9),constrained_layout=True)
    for n in ['Body_Upper','Yaw_Base','Yaw_Bearing','Pitch_Yoke','Yaw_Reaction_Link']:
        fill(ax,q[n],colors[n],n,True)
    radial=np.linalg.norm(c[:,:2],axis=1)
    ax.plot(radial,c[:,2],color='#176bb1',linewidth=3,label='Local outer corridor (R8 bends)')
    ax.scatter(radial[[0,-1]],c[[0,-1],2],color='white',edgecolor='#176bb1',s=85,zorder=8)
    ax.annotate('Upper end unconnected\nService loop still required',xy=(radial[-1],c[-1,2]),xytext=(18,175),
                arrowprops={'arrowstyle':'->','color':'#176bb1'},color='#176bb1')
    ax.annotate('Lower end unconnected\nPCB route still required',xy=(radial[0],c[0,2]),xytext=(17,133),
                arrowprops={'arrowstyle':'->','color':'#176bb1'},color='#176bb1')
    ax.set(xlim=(5,46),ylim=(130,186),xlabel='Radial coordinate r / mm',ylabel='Height Z / mm',
           title='Unchanged M1.48 parts: a local outer route\nNot a complete cable or an adopted harness')
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='upper right',fontsize=8)
    fig.savefig(HERE/'outer_corridor.png',dpi=170);plt.close(fig)
print('SECTION_FIGURES',flush=True)
