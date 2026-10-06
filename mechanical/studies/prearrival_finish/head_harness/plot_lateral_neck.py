from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
HERE=Path(__file__).resolve().parent;d=json.loads((HERE/'lateral_neck_sections.json').read_text())
font=FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc');fontManager.addfont(font.get_file())
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})
colors={'Body_Upper':'#ccd6db','Head_Front':'#e5e9e4','Head_Rear':'#e5e9e4','Head_Lower_Guard':'#e5e9e4',
        'Yaw_Base':'#8fa8b5','Pitch_Yoke':'#407b89','Yaw_Reaction_Link':'#d4a973',
        'Pitch_Cradle':'#a5c7b8','Display_Frame':'#a5c7b8','Yaw_Bearing':'#778284',
        'Yaw_Servo':'#c8b7a2','Pitch_Servo':'#c8b7a2'}
def poly_path(polygons):
    vs=[];codes=[]
    for p in polygons:
        if len(p)<3:continue
        vs+=p+[p[0]];codes += [PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY]
    return PlotPath(vs,codes)
fig,axes=plt.subplots(3,4,figsize=(16,10.7),dpi=150,facecolor='#f7f8f5')
for ax,case in zip(axes.ravel(),d['sections']):
    ax.set_facecolor('#fff')
    for name,row in case['layers'].items():
        ax.add_patch(PathPatch(poly_path(row['polygons_mm']),facecolor=colors.get(name,'#bfc4c2'),edgecolor='#52636a',lw=.45))
    axis=case['plane_axis'];pos=case['plane_position_mm'];pitch=case['pitch_deg']
    ax.set(xlim=(-55,55),ylim=(145,230),aspect='equal',xlabel=('X' if axis=='y' else 'Y')+' / mm',ylabel='Z / mm')
    ax.set_title(f'{axis.upper()} = {pos:g} mm · Pitch {pitch:+d}°',fontsize=11)
    ax.grid(alpha=.1);ax.spines[['right','top']].set_visible(False)
fig.suptitle('进入头部的现有空间：侧向剖面与俯仰姿态',fontsize=20,x=.05,ha='left',y=.985)
fig.text(.05,.02,'蓝：固定轴承座 / 深青：Yaw 支架 / 棕：反力轴 / 浅绿：Pitch 支架；全部为当前实体剖面，未增加走线孔。',fontsize=11,color='#52636a')
fig.subplots_adjust(left=.05,right=.98,top=.93,bottom=.085,wspace=.25,hspace=.42)
for ext in ['png','svg']:fig.savefig(HERE/('lateral_neck_sections.'+ext),facecolor=fig.get_facecolor())
print('LATERAL_NECK_PLOT')
