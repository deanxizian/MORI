"""Show actual solid slices and contact-box slices from the checked path."""
from pathlib import Path
import hashlib,itertools,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Polygon,Patch
from matplotlib.font_manager import FontProperties

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];REST=HERE/'remaining_routes/cam_restraints'
OUT=REST/'contact_continuous';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
section_file=REST/'contact_lower_inward/sections.json';pathfile=OUT/'path.npz'
sections=json.loads(section_file.read_text());path=np.load(pathfile)
review=json.loads((OUT/'review.json').read_text());assert review['status']=='PASS'
font=FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11})
colors={'Pitch_Yoke':'#acbac2','Yaw_Reaction_Link':'#c89556','Yaw_Base':'#627a8a'}
verts=np.array(list(itertools.product([-1.04,1.04],[-.75,.75],[0.,5.7])))
edges=[(i,j) for i in range(8) for j in range(i+1,8) if np.count_nonzero(verts[i]!=verts[j])==1]
fig,axes=plt.subplots(1,3,figsize=(14.4,5.9));fig.patch.set_facecolor('#f6f7f8')
snapshots=[]
for ax,z in zip(axes,[190.,166.,148.]):
    for name,polygons in sections[str(z)].items():
        points=[];codes=[]
        for poly in polygons:
            points.extend(poly+[poly[0]]);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(poly)-1)+[MPath.CLOSEPOLY])
        if points:ax.add_patch(PathPatch(MPath(points,codes),facecolor=colors[name],edgecolor='#33434a',lw=.6))
    index=int(np.argmin(abs(path['rear_mm'][:,2]-(z+2.85))))
    world=verts@path['rotations'][index].T+path['rear_mm'][index];hits=[]
    for i,j in edges:
        a,b=world[i],world[j]
        if (a[2]-z)*(b[2]-z)>0 or abs(a[2]-b[2])<1e-12:continue
        t=(z-a[2])/(b[2]-a[2]);hits.append((a+t*(b-a))[:2])
    hits=np.unique(np.round(hits,9),axis=0);assert len(hits)>=3
    centre=hits.mean(0);order=np.argsort(np.arctan2(hits[:,1]-centre[1],hits[:,0]-centre[0]));hits=hits[order]
    ax.add_patch(Polygon(hits,facecolor='#20bd88',edgecolor='#006445',lw=1.4,zorder=5))
    ax.annotate('名义端子截面',centre,(-17,-17),arrowprops={'arrowstyle':'->','color':'#006445'},color='#006445',fontsize=10)
    ax.set(xlim=(-18,18),ylim=(-20,18),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
    ax.set_title(f'切片 Z = {z:.0f} mm\n端子尾端 Z = {path["rear_mm"][index,2]:.2f} mm',fontsize=12)
    ax.grid(alpha=.15);snapshots.append({'section_z_mm':z,'path_index':index,'contact_section_mm':hits.tolist()})
fig.suptitle('名义端子穿颈路径：保留反力连杆，连续几何检查通过',fontsize=17,y=.96)
fig.legend(handles=[Patch(color=colors['Pitch_Yoke'],label='俯仰支架'),Patch(color=colors['Yaw_Reaction_Link'],label='反力连杆'),
                    Patch(color=colors['Yaw_Base'],label='固定轴承座'),Patch(color='#20bd88',label='名义 PH 端子')],
           loc='lower center',bbox_to_anchor=(.5,.115),ncol=4,frameon=False)
fig.text(.5,.066,'图为同一条路径在三个不同位置的真实截面；不是同时存在三只端子。',ha='center',fontsize=10)
fig.text(.5,.027,'图内未展示其余导线。C6 / 导向件仍未采用；实际压接外形、整根软线移动及装配顺序尚未完成。',ha='center',fontsize=10,color='#804211')
fig.subplots_adjust(left=.055,right=.975,bottom=.27,top=.80,wspace=.25)
file=OUT/'sections.png';fig.savefig(file,dpi=150);plt.close(fig)
result={'status':'PASS','scope':'Rendered actual horizontal geometry slices, not assembly release',
        'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [section_file,pathfile,OUT/'review.json']},
        'snapshots':snapshots,'image':file.name,'image_sha256':sha(file),
        'script_sha256':sha(Path(__file__)),'actual_command':[sys.executable,*sys.argv]}
(OUT/'plot_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_CONTACT_SECTIONS_PLOT_DONE',len(snapshots))
