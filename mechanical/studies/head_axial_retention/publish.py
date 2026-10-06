"""Publish a local candidate review; source assemblies remain immutable."""
from pathlib import Path
import json,hashlib,html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
font=FontProperties(fname='/System/Library/Fonts/Hiragino Sans GB.ttc')
plt.rcParams['font.family']=font.get_name();plt.rcParams['axes.unicode_minus']=False
r=json.loads((HERE/'candidate.json').read_text());v=json.loads((HERE/'readback.json').read_text());b=json.loads((HERE/'body_sequence.json').read_text());s=json.loads((HERE/'sections.json').read_text())
colors={'Yaw_Base':'#ADB9BE','Pitch_Yoke':'#246B8A','Yaw_Bearing':'#8974A9','Yaw_Anti_Lift_Keeper':'#E5A333'}
fig,axes=plt.subplots(1,2,figsize=(14,5.7),dpi=160)
fig.patch.set_facecolor('#F6F8FA')
for ax,key,title in zip(axes,['before','after'],['当前模型：防脱连接尚未闭合','候选：轴承下移，增加一片防脱压板']):
 ax.set_facecolor('#F6F8FA')
 for n in ['Yaw_Base','Yaw_Bearing','Pitch_Yoke','Yaw_Anti_Lift_Keeper']+[x for x in s if 'Keeper_Screw' in x or 'Keeper_Insert' in x]:
  contours=s.get(n,{}).get(key,[])
  paths=[]
  for points in contours:
   if len(points)<3:continue
   pts=[(x,-y) for x,y in points];pts.append(pts[0]);paths.append(MPath(pts,[MPath.MOVETO]+[MPath.LINETO]*(len(pts)-2)+[MPath.CLOSEPOLY]))
  if paths:
   ax.add_patch(PathPatch(MPath.make_compound_path(*paths),facecolor=colors.get(n,'#4C545B' if 'Screw' in n else '#C18E44'),edgecolor='#394753',lw=.5))
 ax.set_xlim(-37,37);ax.set_ylim(143,178);ax.set_aspect('equal');ax.set_title(title,fontproperties=font,fontsize=15,pad=19)
 ax.set_xlabel('X / mm',fontsize=10);ax.set_ylabel('Z / mm',fontsize=10);ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.1)
axes[0].annotate('尚无独立的上提限位',xy=(14,163.7),xytext=(0,175),fontproperties=font,fontsize=11,ha='center',arrowprops={'arrowstyle':'->','color':'#58646F'})
axes[0].annotate('承压面仍是未定型包络',xy=(-13,153.5),xytext=(-34,146),fontproperties=font,fontsize=11,arrowprops={'arrowstyle':'->','color':'#58646F'})
axes[1].annotate('压板挡住蓝色轴肩向上脱出',xy=(16,161),xytext=(-5,175),fontproperties=font,fontsize=11,ha='center',arrowprops={'arrowstyle':'->','color':'#99631A'})
axes[1].annotate('名义活动间隙 0.4 mm',xy=(15,159.4),xytext=(36,171),fontproperties=font,fontsize=10,ha='right',arrowprops={'arrowstyle':'->','color':'#58646F'})
axes[1].annotate('轴承位置下移 4.5 mm',xy=(13,152.5),xytext=(36,145.5),fontproperties=font,fontsize=10,ha='right',arrowprops={'arrowstyle':'->','color':'#665084'})
legend=[Patch(facecolor=c,label=t) for (n,c),t in zip(colors.items(),['身体固定座','随头转动的支架/轴肩','轴承尺寸包络','新增防脱压板'])]
fig.legend(handles=legend,loc='lower center',ncol=4,prop=font,frameon=False,bbox_to_anchor=(.5,.008))
fig.suptitle('头身独立防脱 · 实际候选网格剖面（待确认）',fontproperties=font,fontsize=19,y=.995)
fig.subplots_adjust(left=.055,right=.98,top=.91,bottom=.16,wspace=.19)
fig.savefig(HERE/'comparison.png',facecolor=fig.get_facecolor());plt.close(fig)
readme='''# 头身独立防脱候选 A5 — 待用户确认

可以现在设计独立防脱；它不需要用未知的 SCS0009 舵盘来防止头部整体被提走。当前候选没有应用到主模型。

## 具体结构

- 候选新增一片4mm厚 PA12 C形平板，2枚名义M3×8圆头内六角螺钉、2个FINE SL-M3×4嵌件。采用已有紧固件系列；没有新增外伸耳朵。
- 压板属于身体固定侧，压板下方是随头转动的一体轴肩。正常转动留0.4mm名义间隙；向上提头时轴肩被压板挡住。这是防脱限位，并非消除轴承轴向游隙的预紧结构。
- Yaw轴承与配套机械限位下移4.5mm，轴承中心Z157→152.5mm。舵机轴、头壳、屏幕/相机、身体和车轮的位置均不变。
- 调整Yaw_Base的轴承支承环/压板座，以及Pitch_Yoke的轴颈/轴肩。采用直立环壁和平面接合，压板和螺钉头均低于原固定遮缝圈顶面。
- 以NSK6804ZZ官方20×32×7mm包络、Ø22轴肩及最大Ø30壳体肩孔为候选依据。轴承仍是尺寸/支承面包络，没有伪造内部滚道或防尘盖CAD，也没有已购实物测量。
- 候选轴颈Ø19.9、轴承孔Ø32.1均为试配尺寸；PA12补偿、尺寸公差及实际手感须经试片。未询价、未采购、未生成打印或加工订单。

## 装配顺序

先按已验证的身体顺序安装承重桥/轴承、锁紧桥脚，再让上壳落位。离机将C形压板从侧方套到Yaw转动组件上，与该组件一同从上方装入。头部俯仰总成尚未安装时，把未通电的Yaw支架手动转至+60°，从上方安装两枚压板螺钉；这是已有正常行程内的装配姿态。之后装回俯仰总成。拆卸顺序相反；拆压板螺钉之前支撑头部。

厂家的舵盘/中心螺钉和最终反力轴配套装入仍未完成；这里只核对候选新增/改变零件的刚性路径，不把未知舵盘叠层算作已验证。固定反力轴不随头转动。

## 已检查

- 130个Yaw/Pitch组合姿态：改变的连接与现有零件未检出碰撞。
- 压板121个侧向装入位置、压板与Yaw座181个竖向装入位置：名义网格检查通过。
- 两枚螺钉的装入和2AF长柄L形工具空间通过（Yaw+60°、俯仰总成未安装）。
- 保存的候选Blender回读：0.39mm上提仍有间隙，0.41mm上提被压板阻挡；13个Yaw角均一致。机械限位首次采样接触仍约±64.25°，正常控制范围仍±60°。
- 改动的两件原打印件和新压板均为单一连通实体；当前刚体静态检查通过。
- 原有身体/桥脚407个组合装配位置及M3工具路径用候选重新检查，通过。

## 未完成或未验证

本候选只解决独立防脱与名义承压几何。SCS0009舵盘、中心螺钉、最终传动轴向叠层、俯仰短轴仍待厂家证据；不能称头部传动整体完成。压板0.4mm防脱间隙不证明实际舵机轴完全不受轴向力，这还取决于最终传动连接。PA12强度、热熔嵌件抗拔、蠕变、轴承实配、转动阻力、冲击与耐久仍未测试。环壁变化占用了旧的预留走线环局部空间，完整线束仍须重做，未将其标为通过。

方案A1曾与头壳运动相撞，A2/A3出现局部重叠/连接缺陷；均为已淘汰候选。A4通过几何检查，最终A5将两枚固定螺钉改为左右对称，避免两枚螺钉都集中在前侧，重新检查装入/工具/运动。失败记录保留在attempt_*目录，不能作为当前通过结果引用。

## 资料与复现

官方轴承尺寸：https://www.nsk.com/jp-ja/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6804zz-apn.html

运行环境：Blender5.2.2 LTS / manifold3d（项目vendor）；本地发布使用mori-cad Python及Matplotlib3.11.2。实际命令与日志见manifest.json。主模型、config、STL和装配视频均未替换。
'''
(HERE/'README.md').write_text(readme)
body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 头身独立防脱候选</title><style>body{margin:0;background:#f6f8fa;color:#24313a;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1100px;margin:auto;padding:32px 24px 80px}h1{font-size:32px;line-height:1.25}h2{margin-top:36px;font-size:22px}.tag{color:#99611a;background:#fff0cc;padding:5px 12px;border-radius:20px;font-size:14px}img{display:block;width:100%;border-radius:12px;margin:18px 0;background:#e8edf0}a{color:#17617c}table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px 16px;text-align:left;border-bottom:1px solid #dbe1e5}p{max-width:950px}.warn{border-left:4px solid #df9a26;padding:12px 18px;background:#fff5df}.legend{display:flex;gap:22px;flex-wrap:wrap}.legend b{margin-right:5px}small{color:#52636f}</style><main><span class="tag">独立候选 A5 · 待确认 · 主模型仍为 M1.43</span><h1>先把头身的独立防脱做好</h1><p>可以在舵盘资料到齐前完成这部分设计。候选用一片平板式压板，挡住头部转动座下方的轴肩；正常转动留间隙。需要把Yaw轴承及配套限位下移4.5mm，头壳、屏幕和舵机保持原位。</p><img src="comparison.png" alt="当前与候选的真实网格剖面对比"><div class="legend"><span><b style="color:#246B8A">■</b>蓝：随头转动</span><span><b style="color:#9BA6AC">■</b>灰：身体固定</span><span><b style="color:#E5A333">■</b>黄：新增压板</span><span><b style="color:#8974A9">■</b>紫：轴承包络</span></div><img src="section.png" alt="候选实际网格局部剖面，显示两枚螺钉和被压板挡住的轴肩"><p><strong>增加：1件PA12打印件＋2枚M3×8螺钉＋2个M3嵌件。</strong>原Yaw承重桥和转动支架各做局部调整。螺钉头沉入压板，顶面在原遮缝圈以内；不是拧紧后夹死旋转部分。</p><table><tr><th>检查</th><th>结果与范围</th></tr><tr><td>头部运动</td><td>130个组合姿态，名义实体无新增碰撞</td></tr><tr><td>装入和螺钉操作</td><td>压板侧装/组合下落通过；Yaw手动转到+60°、俯仰总成尚未装入时，可操作两枚螺钉</td></tr><tr><td>防脱</td><td>名义间隙0.4mm；保存文件回读，13个Yaw角在上提0.41mm时均被阻挡</td></tr><tr><td>机械限位</td><td>采样接触仍约±64.25°，正常范围±60°</td></tr><tr><td>身体原装配顺序</td><td>407个位置及桥脚工具路径重新检查通过</td></tr></table><p>轴承参考<a href="https://www.nsk.com/jp-ja/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6804zz-apn.html">NSK6804ZZ官方尺寸</a>（20×32×7mm）。完整内部CAD、采购价格和实物配合没有确认，轴颈及壳孔是PA12试配尺寸。</p><p class="warn"><strong>这不是头部传动整体完成。</strong>舵盘、中心螺钉、俯仰短轴及最终轴向叠层仍待厂家资料；0.4mm防脱间隙不是轴承预紧。完整走线、打印强度、嵌件抗拔、蠕变和实际运行仍未验证。</p><p>先在离机状态把压板套到Yaw支架上，再与支架一起下落到身体轴承座，旋转至工具可达姿态后固定压板，最后装俯仰头部。拆卸时先托住头部，再按相反顺序进行。</p><p><a href="candidate.blend">打开可编辑候选 Blender</a>　<a href="README.md">完整说明</a>　<a href="candidate.json">候选检查</a>　<a href="readback.json">保存文件回读</a>　<a href="body_sequence.json">身体装配复查</a></p><small>PROTOTYPE / UNVALIDATED · 仅当前候选名义几何检查通过 · 未生成制造或采购订单。</small></main></html>'''
(HERE/'index.html').write_text(body)
assert r['status']==v['status']==b['status']=='PASS'
assert hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest()==r['source_sha256']
commands=[dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','-b','mechanical/mori_v1_2.blend','--python','mechanical/studies/head_axial_retention/'+x+'.py'],log=x+'.log') for x in ['audit_current','candidate']]
commands += [dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','-b','mechanical/studies/head_axial_retention/candidate.blend','--python','mechanical/studies/head_axial_retention/'+x+'.py'],log=log) for x,log in [('readback','readback.log'),('body_sequence_check','body_sequence.log')]]
commands += [dict(argv=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python','mechanical/studies/head_axial_retention/publish.py'])]
files=['candidate.blend','candidate.py','candidate.json','readback.json','body_sequence.json','section.png','comparison.png','index.html','README.md','readback.py','body_sequence_check.py','publish.py','inspection.json','sections.json']
manifest=dict(candidate_id='A5',status='PASS',scope='Named finite nominal geometry checks only',user_approval='BLOCKED',main_replaced=False,source_sha256=r['source_sha256'],source_unchanged=True,physical_validation='NOT_TESTED',horn_interfaces='BLOCKED',body_sequence_samples=sum(x['samples'] for x in b['paths']),commands=commands,files={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in files})
(HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('REVIEW_PUBLISHED',manifest['candidate_id'],r['status'],manifest['body_sequence_samples'])
