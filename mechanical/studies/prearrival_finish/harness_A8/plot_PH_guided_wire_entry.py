"""Plot the verified stored wires, connector poses and unchanged body solids."""
from pathlib import Path
import json,hashlib,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'PH_guided_wire_entry';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
data=read(OUT/'screen.json');verified=read(OUT/'verification.json')
continuous=read(OUT/'full_wire_continuous.json')
assert continuous['status']=='PASS' and continuous['source_verification_sha256']==sha(OUT/'verification.json')
assert data['status']==verified['status']=='PASS'
assert verified['source_report_sha256']==sha(OUT/'screen.json')
assert data['curves_sha256']==sha(OUT/'curves.npz')
projections=read(STOCK/'PH_shell16_stepped_entry/projections.json')
old_verify=read(STOCK/'PH_shell16_stepped_entry/verification.json')
assert old_verify['source_target_members']==data['source_target_members']
assert projections['verification_sha256']==sha(STOCK/'PH_shell16_stepped_entry/verification.json')
wires=np.load(OUT/'curves.npz');guide=data['selected_guide']


def rotate(v,axis,angle):
    return v*math.cos(angle)+np.cross(axis,v)*math.sin(angle)+axis*np.dot(axis,v)*(1-math.cos(angle))


def pose(s):
    q=next((q for q in guide['segments'] if q['s1']>=s-1e-9),guide['segments'][-1])
    local=np.clip(s-q['s0'],0,q['length']);t=np.asarray(q['tangent']);n=np.asarray(q['normal'])
    if q['kind']=='line':return np.asarray(q['start'])+local*t,t,n
    axis=np.asarray(q['axis']);angle=local/q['radius']
    return np.asarray(q['c'])+rotate(np.asarray(q['r0']),axis,angle),rotate(t,axis,angle),rotate(n,axis,angle)


def hull2d(points):
    ordered=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    def chain(items):
        result=[]
        for q in items:
            while len(result)>=2 and cross(result[-2],result[-1],q)<=1e-12:result.pop()
            result.append(q)
        return result
    return np.asarray(chain(ordered)[:-1]+chain(ordered[::-1])[:-1])


font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':10})
fig,axes=plt.subplots(2,3,figsize=(14,10),dpi=170)
indices=[0,len(data['replay'])//2,len(data['replay'])-1]
labels=['身体端就位，四根线尾暂留在颈部外侧','插头沿圆滑通道转向','插头到达上方开放空间']
colors=['#be462b','#c18b16','#248971','#4c62b4']
size=np.asarray(projections['housing_dimensions_mm'])
corners=np.array([[x,y,z] for x in [-.5,.5] for y in [-.5,.5] for z in [-.5,.5]])*size
for column,(index,label) in enumerate(zip(indices,labels)):
    s=data['replay'][index]['s_mm'];p,t,n=pose(s);rot=np.column_stack([n,np.cross(t,n),t])
    housing=corners@rot.T+p-(5+size[2]/2)*t
    for row,(plane,dims) in enumerate([('YZ',[1,2]),('XZ',[0,2])]):
        ax=axes[row,column]
        for name,polys in projections['projections'][plane].items():
            color='#5c8992' if name=='Yaw_Base' else '#abb8bb'
            for poly in polys:
                pp=np.asarray(poly);pp=np.vstack([pp,pp[0]])
                ax.plot(pp[:,0],pp[:,1],color=color,lw=.65,alpha=.75)
        for pin,color in enumerate(colors,1):
            points=wires[f'pose{index}_pin{pin}']
            ax.plot(points[:,dims[0]],points[:,dims[1]],color=color,lw=1.05,label=f'线 {pin}')
        hh=hull2d(housing[:,dims])
        ax.add_patch(Polygon(hh,closed=True,facecolor='#c27538',edgecolor='#734025',alpha=.6,lw=1.2))
        ax.set(aspect='equal',xlim=(-78,58) if plane=='YZ' else (-61,61),ylim=(111,229),
               xlabel=('Y' if plane=='YZ' else 'X')+' / mm',ylabel='Z / mm')
        ax.grid(alpha=.12)
        if row==0:ax.set_title(label,fontsize=10.5,pad=13)
        if column==0:ax.text(.02,.95,('侧视' if plane=='YZ' else '正视')+'投影',transform=ax.transAxes,color='#395a60')
        if row==1:ax.text(.03,.02,f'检查位置 {index+1}/171',transform=ax.transAxes,color='#455c62',fontsize=9)
axes[0,0].legend(loc='upper right',fontsize=8,ncol=2)
fig.suptitle('PH 插头带四根全长导线：先在颈外暂存，再处理穿颈',fontsize=18,y=.973,color='#254951')
fig.text(.055,.119,'全线：171 个位置、174 个连续区间通过；插头与线根：875 个连续包络通过。图示拔出，装入反序。',fontsize=11,color='#37585f')
fig.text(.055,.084,'线尾继续向上延伸，图中截取装配区域；计算保留每根原名义总长，未增加裁线长度。最小解析弯曲半径不少于 9 mm。',fontsize=10.5,color='#37585f')
fig.text(.055,.05,'上壳保持 16° / +14 mm，承重桥就位。H01/H04 延后；穿颈、收线、手部工具和完整工序仍未完成。',fontsize=10.5,color='#93631f')
fig.text(.055,.018,'M1.47 主模型未修改。研究使用未采用的通道候选与端子预留；不是制造放行或实物装配证明。',fontsize=10.5,color='#93631f')
fig.subplots_adjust(left=.055,right=.985,top=.912,bottom=.22,hspace=.31,wspace=.25)
fig.savefig(OUT/'route.png');plt.close(fig)
report=dict(status='PASS',scope='Source-based stored full-wire snapshots',script_sha256=sha(SCRIPT),
    source_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'screen.json',OUT/'verification.json',OUT/'full_wire_continuous.json',OUT/'curves.npz',
        STOCK/'PH_shell16_stepped_entry/projections.json',STOCK/'PH_shell16_stepped_entry/verification.json']},
    outputs={'route.png':sha(OUT/'route.png')},cropped_upper_stock_is_in_calculation=True,
    main_applied=False,manufacturing_release=False)
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('GUIDE_PLOT_DONE')
