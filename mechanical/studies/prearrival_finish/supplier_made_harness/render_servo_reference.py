"""Render the downloaded STEP as evidence, not as a replacement robot part."""
from pathlib import Path
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams['font.family'] = 'Heiti SC'
plt.rcParams['axes.unicode_minus'] = False
r = json.loads((HERE/'servo_step_inspection.json').read_text())
parts=[]
for row in r['world_parts']:
    data=(HERE/row['stl']).read_bytes()
    count=int.from_bytes(data[80:84], 'little')
    dtype=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('att','<u2')])
    a=np.frombuffer(data, dtype=dtype, count=count, offset=84)['v'].astype(float)
    a=a[:,:,[2,0,1]]; a[:,:,2]+=1.51
    parts.append(a)

fig=plt.figure(figsize=(12,6.5),facecolor='#f3f6f7')
fig.suptitle('新找到的 SCS0009 系列 STEP：含壳体和输出齿轮，不含舵盘',fontsize=17,y=.97)
colors=['#718b96','#4b6270','#6c7b86','#bf9348']
all_triangles=np.concatenate(parts)
all_colors=np.concatenate([np.tile(to_rgb(c),(len(t),1)) for t,c in zip(parts,colors)])
normals=np.cross(all_triangles[:,1]-all_triangles[:,0],all_triangles[:,2]-all_triangles[:,0])
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
light=np.array([.3,-.5,.8]);light/=np.linalg.norm(light)
all_colors*= (.6+.4*np.abs(normals@light))[:,None]
for i,az in enumerate([-52,126]):
    ax=fig.add_subplot(1,2,i+1,projection='3d',facecolor='#f3f6f7')
    # Sort all triangles together, so hollow case sections do not cover each
    # other using separate collections' average depth.
    ax.add_collection3d(Poly3DCollection(all_triangles,facecolors=all_colors,edgecolor='none',shade=False))
    ax.set(xlim=(-19,19),ylim=(-19,19),zlim=(-2,36))
    ax.set_box_aspect((1,1,1));ax.view_init(elev=22,azim=az);ax.set_axis_off()
fig.text(.5,.075,'4 个实体均通过 CAD 有效性检查；原文件按毫米读取，未缩放。',ha='center',fontsize=11,color='#263e49')
fig.text(.5,.04,'来源：Robotopian 下载页。厂家原始来源、采购版次及配套舵盘仍待确认；未替换 MORI 主模型。',ha='center',fontsize=10,color='#596b73')
fig.subplots_adjust(left=0,right=1,top=.9,bottom=.12,wspace=-.2)
fig.savefig(HERE/'servo_reference.png',dpi=150,facecolor=fig.get_facecolor())
