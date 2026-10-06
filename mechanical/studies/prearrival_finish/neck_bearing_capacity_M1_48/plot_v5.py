"""Plot actual source and C4/C5 finite-pose sections."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=json.loads((HERE/'C5_review_sections.json').read_text())
assert data['C5_build_sha256']==sha(HERE/'C5_build.json')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors=dict(Yaw_Base='#bbcac2',Pitch_Yoke='#387f8b',Yaw_Anti_Lift_Keeper='#d1a151',Yaw_Bearing='#74828c',Head_Rear='#c0b4c6',Yaw_Reaction_Link='#304a3b')
def fill(ax,polys,color,zorder):
    verts=[];codes=[]
    for a in polys:
        if not a:continue
        verts.extend(a+[a[0]]);codes.extend([MP.MOVETO]+[MP.LINETO]*(len(a)-1)+[MP.CLOSEPOLY])
    if verts:ax.add_patch(PathPatch(MP(verts,codes),facecolor=color,edgecolor='none',zorder=zorder))
fig,axes=plt.subplots(2,3,figsize=(13.8,8.7))
curves=np.load(HERE/'C4_packed_curves.npz');pack=json.loads((HERE/'C4_packing.json').read_text())
for col,(tag,title) in enumerate([('main','Current M1.48'),('C4','Earlier C4: clearance failed'),('C5','Proposed C5: finite checks pass')]):
    for row,key in enumerate(['horizontal_Z166','side_X8.5']):
        ax=axes[row,col]
        for i,n in enumerate(['Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Head_Rear']):
            fill(ax,data['sections'][tag][key][n],colors[n],i)
        if row==0 and tag!='main':
            for j,slot in enumerate(pack['selected']):
                p=curves[f'wire{j}_y0'];x=np.interp(166,p[:,2],p[:,0]);y=np.interp(166,p[:,2],p[:,1])
                ax.add_patch(plt.Circle((x,y),slot['OD_mm']/2,color='#d7742f',zorder=10))
        ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_facecolor('#fafbf9')
        if row==0:
            ax.set_xlim(-20,20);ax.set_ylim(-20,17);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
            ax.set_title(title+'\nZ = 166 mm; yaw 0 / pitch +25 deg')
        else:
            ax.set_xlim(-19,-5);ax.set_ylim(157,172);ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)')
            ax.set_title('X = 8.5 mm section; pitch +25 deg')
fig.suptitle('C5: retain the head shell, close the neck clearance and thin transition',fontsize=16,y=.985)
fig.legend(handles=[Patch(color=colors[n],label=l) for n,l in [('Pitch_Yoke','Yaw support'),('Yaw_Anti_Lift_Keeper','Keeper'),('Head_Rear','Original tilted head shell')]]+[Patch(color='#d7742f',label='Local wire OD samples')],loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.012))
fig.subplots_adjust(top=.88,bottom=.11,hspace=.38,wspace=.25)
fig.savefig(HERE/'C5_sections.png',dpi=160,facecolor='white')
fig.savefig(HERE/'C5_sections.svg',facecolor='white')
print('C5_SECTIONS_PLOTTED')
