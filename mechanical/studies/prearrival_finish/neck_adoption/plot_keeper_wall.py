"""Draw the archived comparison, showing approval separately from test provenance."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Circle
HERE=Path(__file__).resolve().parent
plt.rcParams['font.family']=['Arial Unicode MS','PingFang SC','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
data=json.loads((HERE/'keeper_wall_sections.json').read_text())
check=json.loads((HERE/'keeper_wall_verification.json').read_text())
adopted=(HERE/'keeper_wall_approval.json').exists()
approval=json.loads((HERE/'keeper_wall_approval.json').read_text()) if adopted else None
main=HERE.parents[2]/'mori_v1_2.blend'
current_sha=hashlib.sha256(main.read_bytes()).hexdigest()
def section(ax, polygons, color):
    vertices=[];codes=[]
    for p in polygons:
        if len(p)<3:continue
        vertices.extend(p+[p[0]])
        codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY])
    if vertices:ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,edgecolor='#243b45',lw=.9))
def dimension(ax,xa,xb,y,label,dy=1.2):
    ax.plot([xa,xa],[y-.6,y+dy+.15],color='#9b3f17',lw=.7)
    ax.plot([xb,xb],[y-.6,y+dy+.15],color='#9b3f17',lw=.7)
    ax.annotate('',(xa,y+dy),(xb,y+dy),arrowprops=dict(arrowstyle='<->',color='#9b3f17',lw=1))
    ax.text((xa+xb)/2,y+dy+.2,label,ha='center',va='bottom',fontsize=11,color='#8d3210')
fig,axes=plt.subplots(2,2,figsize=(12,9))
fig.patch.set_facecolor('#f6f8fa')
for col,(tag,xc,title) in enumerate([('approved_C5',26.,'原 C5：修正前的孔壁'),('candidate_K1',26.2,('已采用 K1' if adopted else '候选 K1')+'：孔轴各向外 0.2 mm')]):
    for row,z in enumerate([157.,162.]):
        ax=axes[row,col]
        ax.set_facecolor('#fff')
        section(ax,data[str(z)][tag]['Yaw_Base'],'#bfd6dc')
        section(ax,data[str(z)][tag]['Yaw_Anti_Lift_Keeper'],'#78979c')
        ax.plot([xc,xc],[-7,7],color='#444',ls='--',lw=.65)
        ax.plot([20,34],[0,0],color='#444',ls='--',lw=.65)
        ax.set_xlim(20,34);ax.set_ylim(-6,7);ax.set_aspect('equal')
        ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm')
        ax.grid(alpha=.12)
        ax.set_title(title if row==0 else '压板上层沉孔截面',fontsize=13,pad=10)
        if row==0:
            dimension(ax,22.5,xc-2.025,0,'1.475 mm' if col==0 else '1.675 mm',3.1)
            ax.text(20.4,-5.3,'Z = 157 mm · 嵌件孔 Ø4.05',fontsize=11)
        else:
            radius=30 if col==0 else 30.2
            dimension(ax,xc+3,radius,0,'1.00 mm',3.3)
            ax.text(20.4,-5.3,'Z = 162 mm · 沉孔 Ø6',fontsize=11)
fig.suptitle('压板固定孔：实际实体剖面对比（右侧，左侧对称）',fontsize=18,y=.99)
fig.text(.5,.016,'只调整 2 件现有打印件及对应紧固件位置；无新增零件。1.6 mm 是设计预留值，并非强度认证。',ha='center',fontsize=11)
fig.tight_layout(rect=(0,.04,1,.96))
fig.savefig(HERE/'keeper_wall_comparison.png',dpi=170)
fig.savefig(HERE/'keeper_wall_comparison.svg')
assert check['status']=='PASS',check['status']
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · 压板固定孔局部修正 K1</title><style>
body{font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;background:#f4f7f8;color:#17313c;margin:0}main{max-width:1120px;margin:auto;padding:28px}h1{font-size:29px;line-height:1.3}h2{font-size:21px}article{background:white;border-radius:14px;padding:22px;margin:18px 0}img{width:100%;height:auto}table{width:100%;border-collapse:collapse}td,th{padding:9px;text-align:left;border-bottom:1px solid #ddd}a{color:#135d93}.status{display:inline-block;background:#ffe2af;padding:5px 12px;border-radius:8px}small{color:#516770}code{overflow-wrap:anywhere}</style>
<main><a href="../neck_bearing_capacity_M1_48/C5_index.html">← 已采用的 C5 颈部方案</a>
<h1>压板固定孔的局部修正</h1><span class="status">候选 K1 · 尚未应用，等待确认</span>
<p>C5 已应用到 M1.49。整机复核发现：压板嵌件孔内侧最薄处为 1.475 mm，未达到原方案使用的 1.6 mm 几何预留值。此前候选检查范围不足，未覆盖这处最薄侧壁。</p>
<article><h2>建议的修正</h2><p>左右固定孔、螺钉和嵌件各向外移 0.2 mm；压板与外围环内径各增加 0.4 mm。外围环外径保持，外轮廓没有新增突出。轴承、旋转件、头壳、屏幕和舵机保持原位。</p>
<table><tr><th>项目</th><th>当前 C5</th><th>候选 K1</th></tr><tr><td>两侧孔轴 X</td><td>±26.0 mm</td><td>±26.2 mm</td></tr><tr><td>嵌件孔最薄侧壁</td><td>1.475 mm</td><td>1.675 mm</td></tr><tr><td>压板外径</td><td>60.0 mm</td><td>60.4 mm</td></tr><tr><td>外围环内径 / 外径</td><td>60.6 / 65.4 mm</td><td>61.0 / 65.4 mm</td></tr><tr><td>沉孔至压板外缘</td><td>1.0 mm</td><td>1.0 mm</td></tr><tr><td>新增打印件 / 紧固件</td><td colspan="2">均为 0</td></tr></table></article>
<article><a href="keeper_wall_comparison.png"><img src="keeper_wall_comparison.png" alt="当前 C5 与候选 K1 的实际实体剖面对比"></a><small>由保存的主模型和独立候选实体切片绘制；不是概念示意轮廓。</small></article>
<article><h2>名义几何复核</h2><p>130 个头部组合姿态、压板侧向装入、与偏航组件一起下放、轴承装入、两枚螺钉装入和扳手空间检查均通过。39 个轴向防脱采样通过。与头壳的最小采样间隙仍约 0.420 mm。</p><p>1.6 mm 是原设计预留值，不代表尼龙打印或嵌件的强度已验证。完整线束、实际公差及承载验证仍未完成。</p><a href="keeper_wall_verification.json">检查记录</a> · <a href="keeper_wall_comparison.svg">矢量剖面</a></article>
<small>当前主模型 SHA256：SOURCE_HASH</small></main></html>'''
if adopted:
    html=html.replace('候选 K1 · 尚未应用，等待确认','K1 已确认并应用到 M1.49')
    html=html.replace('建议的修正','已采用的修正').replace('<th>当前 C5</th><th>候选 K1</th>','<th>修正前 C5</th><th>已采用 K1</th>')
    html=html.replace('C5 已应用到 M1.49。整机复核发现：','C5 应用后的整机复核发现：')
    html=html.replace('当前主模型 SHA256：SOURCE_HASH','比较基线（修正前）SHA256：SOURCE_HASH')
    html=html.replace('</main>','<p><a href="index.html">当前交付与检查</a> · <a href="keeper_wall_approval.json">用户确认记录</a></p></main>')
(HERE/'keeper_wall_index.html').write_text(html.replace('SOURCE_HASH',check['source_main_sha256']))
(HERE/'keeper_wall_review_manifest.json').write_text(json.dumps({'status':'PASS','main_applied':adopted,'comparison_baseline_sha256':check['source_main_sha256'],'current_source_blend_sha256':current_sha,'approval':approval and approval['question_id'],'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'keeper_wall_sections.json',HERE/'keeper_wall_verification.json',HERE/'keeper_wall_comparison.png',HERE/'keeper_wall_comparison.svg']}},indent=2)+'\n')
print('KEEPER_WALL_REVIEW',check['status'])
