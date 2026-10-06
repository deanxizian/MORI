"""Publish read-only head wiring evidence; preserve main and earlier route reports."""
from pathlib import Path
import json,hashlib,datetime,html,re,sys,urllib.request
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Rectangle,FancyBboxPatch
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
when=datetime.datetime.now(datetime.timezone.utc).isoformat()
d=read(HERE/'head_hardware_groups.json');r=read(HERE/'head_path_review.json')
assert sha(PROJECT/'mechanical/mori_v1_2.blend')==d['source_blend_sha256']==r['source_blend_sha256']
font=FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})
from matplotlib import font_manager
font_manager.fontManager.addfont(font.get_file())
colors={'Head_Front':'#dfe5e9','Head_Rear':'#dfe5e9','Head_Lower_Guard':'#dfe5e9',
        'Pitch_Cradle':'#a5c3c9','Display_Frame':'#6e999f','Pitch_Yoke':'#b8c6d8',
        'Yaw_Servo':'#ded9cf','Pitch_Servo':'#ded9cf','CAM_Mainboard':'#237a64',
        'Camera_PCB':'#d89536','Camera_Lens':'#8d6636','Display_PCB':'#315d5b',
        'Yaw_Base':'#bac4cb','Yaw_Bearing':'#999da4','Yaw_Reaction_Link':'#b2bfd0'}

def compound(polygons):
    vertices=[];codes=[]
    for polygon in polygons:
        points=np.asarray(polygon)
        if len(points)<3:continue
        vertices.extend(points.tolist()+[points[0].tolist()]);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(points)-1)+[PlotPath.CLOSEPOLY])
    return PlotPath(vertices,codes)

fig,ax=plt.subplots(figsize=(11.5,8),dpi=160)
fig.set_facecolor('#f7f8f7');ax.set_facecolor('#f7f8f7')
sec=r['sections'][0]
for name,row in sec['layers'].items():
    ax.add_patch(PathPatch(compound(row['polygons_mm']),facecolor=colors.get(name,'#cdd2d5'),edgecolor='#526269',linewidth=.65))
a,b=np.asarray(r['camera_reach']['minimum_pair_mm'])[:,1:]
ax.plot([a[0],b[0]],[a[1],b[1]],'--',color='#ba4b39',lw=2,zorder=10)
ax.scatter([a[0],b[0]],[a[1],b[1]],s=42,color='#ba4b39',zorder=11)
ax.annotate('相机模组（照片尺寸估计）',xy=b,xytext=(35,275),fontsize=10,fontproperties=font,
            arrowprops=dict(arrowstyle='-',color='#526269'),ha='left')
ax.annotate('CAM 板相机插座',xy=a,xytext=(-66,235),fontsize=10,fontproperties=font,
            arrowprops=dict(arrowstyle='-',color='#526269'),ha='left')
ax.text(-3,250,'≥ 58.23 mm\n包络最短距离',fontsize=11,color='#9b3829',fontproperties=font,
        bbox=dict(boxstyle='round,pad=.4',facecolor='white',edgecolor='#e2d0cb'),zorder=12)
ax.text(41,206,'屏幕',fontproperties=font,fontsize=10,ha='center')
ax.text(-7,210,'Yaw 舵机',fontproperties=font,fontsize=10,ha='center')
ax.set(xlim=(-70,76),ylim=(185,286),aspect='equal',xlabel='Y / mm（向前 →）',ylabel='Z / mm')
ax.set_title('相机排线需要重新确认完整长度',fontproperties=font,fontsize=17,loc='left',pad=20)
ax.grid(alpha=.12);ax.spines[['top','right']].set_visible(False)
fig.text(.12,.035,'X = 0 实体剖面；红虚线只是距离下界，会穿过 CAM 板和 Display frame，不能作为走线路径。',fontproperties=font,fontsize=10,color='#55626a')
fig.subplots_adjust(left=.09,right=.94,bottom=.12,top=.89)
for ext in ['png','svg']:fig.savefig(HERE/('camera_reach.'+ext),facecolor=fig.get_facecolor())
plt.close(fig)

branches=[
 dict(id='H06',name='运动板 J5 → CAM UART',conductors=4,a='body',b='pitch',crosses=['yaw','pitch'],source='hardware/v1_2/prearrival_20261002/harness_detail.csv',notes='板端 PH；CAM 厂配 SH 尾线及接续未定。3V3 线只供逻辑电平转换参考。'),
 dict(id='P_J18',name='电源板 J18 → CAM USB 5V',conductors=2,a='body',b='pitch',crosses=['yaw','pitch'],source='hardware/v1_2/prearrival_20261002/harness_detail.csv',notes='USB 供电尾线完整型号未定；屏蔽/备用芯线不在此最小计数中。'),
 dict(id='SPK',name='CAM SPK → 肚子外壳上的 SP3040',conductors=2,a='pitch',b='body',crosses=['yaw','pitch'],source='mechanical/sources/waveshare_detail/cam_schematic.pdf + selected SP3040 drawing',notes='厂配 200mm / 1.25 标注不能确认完整插头系列；BTL 双线均不能接地。'),
 dict(id='P_J9',name='电源板 J9 → 头部舵机链',conductors=3,a='body',b='yaw',crosses=['yaw'],source='hardware/v1_2/prearrival_20261002/harness_detail.csv',notes='两只舵机机身均在 yaw 组；原厂端视图、线序和线材仍需核实。'),
 dict(id='SERVO_LINK',name='Yaw 舵机 ↔ Pitch 舵机机身',conductors=3,a='yaw',b='yaw',crosses=[],source='head_hardware_groups.json + FEETECH A/0',notes='相对固定；首只/次只连接次序、原配端子仍未定。'),
 dict(id='LCD_FFC',name='CAM DISPLAY → LCD 外接 18 针插座',conductors=18,a='pitch',b='pitch',crosses=[],source='hardware/v1_2/handoff/mechanical_P5R7_prearrival_A5_harness.json',notes='原配 18P / 0.5mm / 200mm / 同面接触有厂家依据；宽厚、折弯半径及 CAM 配对方向待核。'),
 dict(id='CAMERA_FPC',name='CAM CAMERA → OV3660',conductors=24,a='pitch',b='pitch',crosses=[],source='mechanical/sources/waveshare_detail/cam_schematic.pdf',notes='完整 FPC 长度和供应料号未知；10.5mm 只是模型参考照片的可见段。')]
assert all(next(x for x in d['parts'] if x['name']==n)['group']==g for n,g in [('Yaw_Servo','yaw'),('Pitch_Servo','yaw'),('CAM_Mainboard','pitch'),('Display_PCB','pitch'),('Camera_PCB','pitch'),('Speaker','body')])
yaw_count=sum(x['conductors'] for x in branches if 'yaw' in x['crosses'])
pitch_count=sum(x['conductors'] for x in branches if 'pitch' in x['crosses'])
assert (yaw_count,pitch_count)==(11,8)
sources=[PROJECT/'config/geometry.json',PROJECT/'contracts/electrical_interfaces.json',
 PROJECT/'hardware/v1_2/prearrival_20261002/harness_detail.csv',
 PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A5_harness.json',
 PROJECT/'mechanical/sources/waveshare_detail/source_manifest.json',
 PROJECT/'mechanical/sources/waveshare_detail/cam_schematic.pdf',
 PROJECT/'mechanical/sources/v1_2_verified_dimensions/1.85inch_touch_lcd_module-3d.stp']
out=dict(status='PASS',scope='Connectivity inventory and rigid-group classification only',
 revision=d['revision'],source_blend_sha256=d['source_blend_sha256'],sources={str(p.relative_to(PROJECT)):sha(p) for p in sources},
 minimum_functional_conductors_crossing_yaw=yaw_count,minimum_functional_conductors_crossing_pitch=pitch_count,
 physical_bundle_size='BLOCKED; cable construction, shields, gauges, jackets and anchors unselected',branches=branches,
 actual_cable_route='NOT_TESTED',strain_relief='NOT_TESTED',dynamic_fatigue='NOT_TESTED',main_geometry_changed=False)
write(HERE/'head_connectivity.json',out)

requirements='''# 头部线束资料及机械要求（未下单）

本页基于 M1.47 已保存模型；未修改任何主模型、硬件源文件、针脚或打印孔。

## 已确定的运动归属

- 两只头部舵机的机身均属于 yaw 组：两者之间的连线不跨俯仰关节。
- CAM、LCD、相机属于 pitch 组：若全部固定点同属 pitch，则头内两条排线按静态布置处理。
- 身体与 yaw 之间至少有 11 根功能导线，其中 8 根还跨 pitch；包含回到身体喇叭的双线。不含屏蔽层、备用芯线和未知 USB 线材结构，不能据此直接给出总束径。

## 相机连接：需要在打样前解决的资料问题

当前相机插座与模组包络相距至少 **58.23mm**。这只是名义包络下界；最短直线穿过 CAM 板和 Display_Frame，所以实际布线会更长。完整原配 FPC 长度未确认。模型中的 10.5mm 是照片可见段，绝不能当作原配总长。

请硬件任务优先核对原配 OV3660 的完整 FPC 图纸和料号。如长度不足，查询与 CAM33700 同电气接口、同接触方向的加长模组或厂家支持的延长方案，先交接候选，不改正式电路，不把任意 24P/0.5mm 线认作兼容。

所需输入：端子到模组的有效长度、两端插入长度、全宽/窄尾宽、厚度与补强板、最小静态折弯半径、插座开口/接触面/锁扣打开空间、延长后 DVP 信号完整性约束。若要增加中继插座/小转接板，需完整实体、固定和插拔空间；不能悬放。未知尺寸仍列 ASSUMED/BLOCKED。先保留已确认的板位、镜头和打印件。

## LCD 排线

官方照片与 STEP 对应的外接 18PIN 插座是 Display_PCB 的 Connector_108（电气 L1）。Connector_107 是屏本体内部排线座，不能接错。厂配 18P/0.5mm/200mm/同面接触有资料依据；CAM 端配对方向、宽厚、允许折弯和可收纳长度尚缺。不能用照片上的引脚文字替代已核对的原理图，尤其保留电气任务对 16–18 脚的 NC 结论。

## 动态线及装配要求

H06、CAM USB 供电、喇叭双线需分别跨 yaw/pitch；舵机上游三线只跨 yaw。每个跨关节段要有两侧真实固定点、端子后直段、有限服务环、最小半径及极限姿态下的松量；固定点不得跨到另一运动组而把静态排线变成动态排线。

尚需厂家/供应商输入：线材最大外径、静态与动态半径、压接后直段与出线位置、允许扭转/循环寿命、插头与尾套全包络。现有导线目录的静态弯曲半径不能代替往复寿命。

头身拆装要明确先断开哪些连接；安装顺序需能操作相机/LCD锁扣并保留取板余量。任何需要新增开孔、改固定点/打印轮廓、增加零件或改变已选器件的方案先提供可审查候选，再请用户确认。

以上是可在到货前完成的资料和方案工作；实际接插件配合、PA12公差、动态寿命和通电表现仍需实物验证。没有制造/采购/上电放行。
'''
(HERE/'HEAD_HARNESS_REQUIREMENTS.md').write_text(requirements)

table=''.join('<tr><td>'+html.escape(b['name'])+'</td><td>'+str(b['conductors'])+'</td><td>'+('＋'.join(b['crosses']) or '同一刚体内固定')+'</td></tr>' for b in branches)
neck=read(HERE/'central_gap_check.json');turn=read(HERE/'outer_neck_turn.json');azimuths=read(HERE/'neck_azimuths.json')
assert all(v['source_blend_sha256']==d['source_blend_sha256'] for v in [neck,turn,azimuths])
assert neck['sample_plus_gap_screen']=='FAIL' and turn['solid_checks'][0]['static_status']=='PASS'
assert turn['solid_checks'][0]['fixed_occupancy_motion_status']=='FAIL'
loop_source=read(HERE/'loop_source_solids.json');loop_curves=read(HERE/'split_planar_loops_refined.json')
assert loop_source['status']=='PASS' and loop_source['source_blend_sha256']==d['source_blend_sha256']
assert loop_source['source_loops_sha256']==sha(HERE/'split_planar_loops_refined.json')
assert len(loop_source['groups'])==2 and all(g['status']=='PASS' for g in loop_source['groups'])
assert next(g for g in loop_curves['groups'] if g['id']=='UART')['status']=='BLOCKED'
entry=read(HERE/'head_entry_shortest.json');smooth=read(HERE/'head_entry_smooth.json')
assert entry['status']=='PASS' and entry['source_blend_sha256']==d['source_blend_sha256']
assert smooth['source_shortest_path_sha256']==sha(HERE/'head_entry_shortest.json')
assert entry['source_obstacle_mesh_sha256']==sha(HERE/'head_entry_obstacle_union.npz')
assert smooth['status']=='BLOCKED' and not smooth['selected']
a7=read(PARENT/'hardware_A7_J10_C4_receipt.json')
assert a7['status']=='PASS' and a7['main_sha256']==d['source_blend_sha256']
loop_studies=['yaw_loop_space.json','planar_yaw_loops.json','split_yaw_space.json','split_planar_loops.json',
              'split_planar_loops_refined.json','loop_source_solids.json','uart_rising_loops.json',
              'rising_loop_source.json','uart_rising_loops_refined.json','uart_flat_space.json','uart_flat_planar_loop.json']
loop_summary=dict(updated_utc=when,source_blend_sha256=d['source_blend_sha256'],
    status='BLOCKED',scope='Local yaw service-loop planning; complete head harness remains unresolved',
    source_reports={name:sha(HERE/name) for name in loop_studies},
    local_group_allocations=[dict(id=g['id'],status=g['status'],member_count=len(g['members']),
        group_centreline_length_mm=g['selected']['centreline_length_mm'],plane_z_mm=g['plane_z_mm'],
        planning_diameter_mm=g['diameter_mm'],source_solid_poses=130,
        fourteen_static_wires='PASS',individual_wire_lengths='NOT_TESTED')
        for g in loop_curves['groups'] if g['status']=='PASS'],
    UART_four_wire_route='BLOCKED',minimum_inter_group_surface_gap_bound_mm=loop_source['inter_group'][0]['surface_gap_lower_bound_mm'],
    neck_rise='NOT_TESTED',pitch_loop='NOT_TESTED',connector_approaches='NOT_TESTED',actual_anchors='NOT_TESTED',
    physical_cable_selection='BLOCKED',physical_bundle_construction='BLOCKED',installation_path='NOT_TESTED',
    main_geometry_changed=False,complete_harness_adopted=False,
    independent_head_entry_corridors='PASS',head_entry_bends='BLOCKED',
    simultaneous_head_entry_groups='NOT_TESTED',actual_SH_tail_selection='BLOCKED',
    limitations=['Nominal unselected wire samples and assumed SPK gauge; actual jackets, shielding and factory tails unknown.',
        'The two group-centreline lengths are not wire cut lengths or proof of individual wire length constancy.',
        '0.386mm nominal inter-group bound is not a physical tolerance allowance or motion-lifetime qualification.',
        'Failed finite families do not prove that all possible UART routes are blocked.'])
write(HERE/'yaw_loop_progress.json',loop_summary)
loop_html='''<h2 id="yaw-loops">Yaw 活动环：两组局部占位通过，完整线束未完成</h2>
<p>已把跨 Yaw 的 11 根功能导线分组研究，检查环段在 −60°～+60° 转动时的长度和间隙。下图显示的是两组未选型圆束占位；端点还没有实际固定结构。</p>
<img src="yaw_loop_review.png" alt="供电喇叭与舵机两组局部活动环在正负60度和零位的形状，对应不同高度，UART及完整路径仍未完成">
<table><thead><tr><th>分组</th><th>规划占位</th><th>本次结果</th></tr></thead><tbody>
<tr><td>CAM 供电＋喇叭，4 根</td><td>Ø3.505 mm；平面 Z151.5；环段中心线约261.0 mm</td><td>PASS，仅局部占位</td></tr>
<tr><td>头部舵机上游，3 根</td><td>Ø3.123 mm；平面 Z155.2；环段中心线约340.1 mm</td><td>PASS，仅局部占位</td></tr>
<tr><td>UART，4 根</td><td>圆束平面环、抬升环、四根分层排列的有限试算</td><td>BLOCKED，尚无通过的完整局部候选</td></tr>
</tbody></table>
<p>两组通过的占位已核对当前实体、已有14根固定线，以及13个Yaw角×10个Pitch角。两组外表面的全局间隙下界约 <b>0.386 mm</b>，比项目试算的0.3 mm只多约0.086 mm；这不是实物公差或耐久保证。</p>
<p>环段中心线长度保持，并不证明圆束内每根线的长度、滑移和扭转都合适，以上数字也不能作为下料长度。UART的失败仅针对列出的有限路线，不能推断所有路线都无解。</p>
<aside>仍需完成：UART路径、板端到环段、环段进入头部、俯仰活动段、真实固定点、插头出线及拆装松量。已确认供应商按图制作；实际线材和最终逐线图仍待完成。本次没有新增打印孔、夹具或正式线束，也没有修改主模型与装配视频。</aside>
<details><summary>可核验的局部研究与失败记录</summary><p>
<a href="yaw_loop_progress.json">当前研究状态</a> · <a href="loop_source_solids.json">两组环段的实体与130姿态检查</a> ·
<a href="split_planar_loops_refined.json">固定长度曲线与有限搜索</a> · <a href="rising_loop_source.json">抬升UART第一批源实体余量不足</a> ·
<a href="uart_rising_loops_refined.json">抬升UART后续有限试算</a> · <a href="uart_flat_planar_loop.json">四根分层排列试算</a> ·
<a href="hardware_followup_loop_review.json">继续补齐硬件审查和线缆资料的交接记录</a></p></details>'''
entry_html='''<h2 id="head-entry">进入头部：现有空隙有路，折弯与合束尚未完成</h2>
<p>按当前实体和有限组合姿态建立通道图后，供电／喇叭、舵机、UART三个规划束径各自找到了连续折线路径。对应名义表面间隙下界约为0.347、0.322、0.329 mm。起止点只是研究位置，还没有连接到活动环或插头。</p>
<img src="head_entry_review.png" alt="三种束径各自的进入头部折线路径，部分重叠，尚不是最终线束">
<aside>三条路线分别检查，空间有重叠，不能说11根线已经全部排下。折线尖角还不是允许的导线弯曲；25,000个有限五次曲线试算尚未找到通过候选。这只排除了该曲线族，没有证明必须开孔或改变结构。</aside>
<p>新收到的硬件资料还确认：SH候选端子允许的绝缘外径0.4–0.8 mm，小于此前Alpha5853研究样本0.889–1.0922 mm。需要先定厂配细尾线及接续，或实际兼容线材；不能继续把样本直压到CAM接头。实际SH/GH型号、相机完整FPC和舵机物理针号视图仍待确认。</p>
<details><summary>通道证据与原生剖面</summary><img src="lateral_neck_sections.png" alt="不同俯仰角和侧向位置的头颈结构实体剖面"><p><a href="head_entry_space.json">扫掠实体通道图</a> · <a href="head_entry_shortest.json">三组独立路径与间隙界</a> · <a href="head_entry_smooth.json">有限平滑曲线试算</a> · <a href="../hardware_A7_J10_C4_review.html">A7新资料接收</a></p></details>'''
neck_html='''<h2>颈部通道：零位能放下，还不能直接采用</h2>
<p>反力轴与转动轴套之间最窄名义环隙约 <b>1.6 mm</b>。按项目试算每侧保留 0.3 mm，单根导线外径上限约 <b>1.0 mm</b>；当前 1.4224 mm 样本虽不裸碰实体，计入该余量就不通过。这个间隙不能直接当作整束通道。</p>
<img src="neck_motion.png" alt="颈部后侧剖面：3毫米固定圆束试算在零位通过，抬头20度时被后壳扫到">
<p>轴承外侧有一条 <b>3 mm 圆束规划段</b>在零位实体检查通过，包含每侧 0.3 mm 余量；最小曲率半径约 22.73 mm。它固定在身体坐标中，130 姿态里 57 个会被后壳扫到，<b>不能作为实际方案</b>。将同一曲线每 5° 转到其他方位的 72 个有限试算也未找到通过者。</p>
<p>这只排除了这些固定占位曲线，<b>没有证明活动线束无路可走</b>。下一步需用真实线材、固定点和两侧活动余量设计动态段；路线与固定方式未确认前，不新增打印孔。3 mm 是研究尺寸，不是选定束径。</p>
<details><summary>各高度通道与详细证据</summary><img src="neck_sections.png" alt="10个高度的现有关节实体切面"><p><a href="central_gap_check.json">中心间隙单线检查</a> · <a href="outer_neck_turn.json">外侧固定曲线与130姿态</a> · <a href="neck_azimuths.json">72个方位试算</a> · <a href="neck_side.png">后侧纵剖面</a></p></details>'''
style='body{margin:0;background:#f3f5f5;color:#203239;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1050px;margin:auto;padding:36px 24px 70px}h1{font-size:32px;line-height:1.3}h2{font-size:22px;margin-top:36px}p{max-width:900px}a{color:#17637b}img{max-width:100%;height:auto;background:white;border:1px solid #d9e1e3;border-radius:10px}table{width:100%;border-collapse:collapse;background:white}td,th{padding:12px;text-align:left;border-bottom:1px solid #dce3e5}aside{background:#fff4dd;border-left:5px solid #c58b20;padding:16px 20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}small{color:#62747c} @media(max-width:760px){.grid{grid-template-columns:1fr}}'
body=f'''<main><p><a href="../index.html">返回打样前工作</a> · M1.47 独立资料核对</p>
<h1>头部布线：固定排线与跨关节线</h1>
<aside><b>分类与名义尺寸核对完成；完整线束仍未完成。</b><br>相机原配排线长度、LCD排线折弯参数，以及动态线束/插头和固定点仍需定型。没有修改主模型或增加走线孔。</aside>
<h2>相机需要多长的排线</h2><p>当前插座与模组包络的最短距离为 <b>58.23 mm</b>。直线会穿过 CAM 板和 Display frame，实际走线还要更长。CAM/相机部分尺寸来自官方照片估算，这不是实物量测。</p>
<img src="camera_reach.png" alt="X零剖面，显示相机插座到模组至少58.23毫米，直线被结构阻挡">
<p>原配 FPC 的完整长度尚未查到。历史模型的 <b>10.5 mm 只是可见段</b>，不能作为总长或直接判定原配排线必然不足。优先取得完整料号/图纸，再评估原配、加长模组或厂家支持的延长方案；板位和镜头不动。</p>
<h2>哪些线需要活动余量</h2><table><thead><tr><th>连接</th><th>功能导线数</th><th>跨越关节</th></tr></thead><tbody>{table}</tbody></table>
<p>Yaw 边界至少 <b>11 根功能导线</b>，其中 <b>8 根</b>还跨 pitch；不含未知线缆的屏蔽层和备用芯线。不能用这个计数直接推出总束径。两只舵机机身都在 yaw 组；CAM、LCD、相机都在 pitch 组，头内排线可按静态布置，前提是固定点也在同一刚体。</p>
{neck_html}
{loop_html}
{entry_html}
<h2>LCD 插座已对应到正确位置</h2><div class="grid"><div><img src="sources/lcd_connector_photo.webp" alt="微雪官方LCD接口图，左侧18PIN外接FPC，中央是屏内部排线座"><p><small>微雪官方接口照片，仅用来对应物理插座；针脚定义仍以已核对的原理图为准。</small></p></div><div><p>外接 18PIN 对应 STEP 的 <b>Connector_108</b>（电气 L1）。中央 Connector_107 是屏本体排线座。</p><p>随屏 18P / 0.5 mm / 200 mm / 同面接触排线有厂家依据，但宽厚、允许半径及 CAM 端配对方向仍待确认。</p><p><a href="https://docs.waveshare.com/1.85inch_Touch_LCD_Module">LCD 官方接口</a> · <a href="https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm">官方配件列表</a></p></div></div>
<h2>接下来可以在到货前完成</h2><p>补齐相机完整排线资料；明确 USB/SH/喇叭及舵机线的实际插头、出线尺寸；线束已确认由供应商按图制作，逐线图纸和实际线材仍需完成。然后规划现有空隙内的路线、固定点和拆装松量，复核组合姿态。需要改打印结构时先提供候选确认。</p>
<p><a href="HEAD_HARNESS_REQUIREMENTS.md">给硬件任务的输入清单</a> · <a href="head_connectivity.json">连接与运动分组证据</a> · <a href="head_path_review.json">名义端点/剖面报告</a> · <a href="head_hardware_groups.json">保存模型回读</a></p>
<p><a href="../harness_A2/assembly_safe_review/index.html">此前通过的14根固定线候选</a>仍保留：静态、130头部姿态和407身体装配位置通过，完整线束和实物资格未完成。</p>
<p><small>PROTOTYPE / UNVALIDATED。130姿态的端点回读不是线束动态寿命或连续无干涉证明。主模型及装配视频保持。</small></p></main>'''
(HERE/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 头部线束核对</title><style>'+style+'</style>'+body+'</html>')

status=read(PARENT/'work_status.json');row=next(v for v in status['remaining'] if v['id']=='harness');old=row['detail']
new='14根身体固定线候选及两组局部Yaw活动环检查通过。新找到三种束径各自进入头部的折线通道，但路线重叠、弯曲半径及合束未通过，尚未连到插头。A7确认研究用Alpha5853不能直接压接SH候选端子，实际厂配尾线/接续待定。UART活动环、俯仰段、固定点、逐线长度及完整相机FPC仍未完成。所有研究线束均未应用主模型。'
row['detail']=new;row['evidence']='head_harness/index.html';status['updated_utc']=when
add=status['prearrival_wire_addendum']
# Preserve the original candidate's actual failure under an explicit history
# record; unqualified top-level fields must refer to the current candidate.
if 'historical_static_candidate' not in add:
    add['historical_static_candidate']={k:add[k] for k in ['wire_gap_lower_bound_mm','body_sequence_with_static_wires'] if k in add}
    add['historical_static_candidate']['report']='harness_A2/fourteen_body_sequence.json'
current=read(PARENT/'harness_A2/assembly_safe_review/fourteen_validation.json')
add['wire_gap_lower_bound_mm']=min(x['conservative_inflated_capsule_gap_lower_bound_mm'] for x in current['wire_to_wire'])
add['body_sequence_with_static_wires']='PASS';add['current_fixed_wire_report']='harness_A2/assembly_safe_review/fourteen_body_sequence.json'
add['head_connectivity_inventory']='PASS';add['head_routing']='BLOCKED';add['camera_FPC_reach']='BLOCKED';add['head_review']='head_harness/index.html'
add['central_gap_sample_plus_allowance']='FAIL';add['outer_neck_fixed_probe_motion']='FAIL';add['actual_dynamic_neck_route']='NOT_TESTED'
add['two_local_yaw_group_allocations']='PASS';add['two_local_yaw_source_pose_count']=130
add['local_yaw_all_eleven_conductors']='BLOCKED';add['yaw_loop_review']='head_harness/index.html#yaw-loops'
add['two_local_yaw_surface_gap_lower_bound_mm']=loop_summary['minimum_inter_group_surface_gap_bound_mm']
add['independent_head_entry_corridors']='PASS';add['head_entry_bends']='BLOCKED'
add['simultaneous_head_entry_groups']='NOT_TESTED';add['head_entry_review']='head_harness/index.html#head-entry'
add['A7_head_interface_receipt']='PASS';add['actual_SH_tail_selection']='BLOCKED'
write(PARENT/'work_status.json',status)
page=PARENT/'index.html';s=page.read_text().replace(html.escape(old),html.escape(new)).replace(old,new)
s=re.sub(r'<section id="head-harness-update">.*?</section>','',s,flags=re.S)
s=s.replace('<main>','<main><section id="head-harness-update"><h2>头部排线与动态线</h2><p><a href="head_harness/index.html">查看新增核对</a>：区分固定排线与跨关节线；相机完整排线长度及动态线束资料仍缺。主模型保持。</p></section>',1);page.write_text(s)

checks=[]
for page in [HERE/'index.html',PARENT/'index.html']:
    missing=[]
    for ref in re.findall(r'(?:href|src)=["\']([^"\']+)',page.read_text()):
        if ref.startswith(('http:','https:','#','data:','mailto:')):continue
        if not (page.parent/ref.split('#')[0].split('?')[0]).resolve().exists():missing.append(ref)
    assert not missing,(page,missing)
    url='http://127.0.0.1:58201/'+str(page.relative_to(PROJECT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as res:code=res.status
    assert code==200;checks.append(dict(page=str(page.relative_to(PROJECT)),http_status=code,missing=missing))

core=read(PARENT/'M1_47_delivery.json')
for path,digest in core['files'].items():
    if path.endswith('/work_status.json'):core['files'][path]=sha(PROJECT/path)
    else:assert sha(PROJECT/path)==digest,path
write(PARENT/'M1_47_delivery.json',core)
a2=read(PARENT/'harness_A2/delivery.json')
for page in [PARENT/'index.html',PARENT/'work_status.json']:
    a2['files'][str(page.relative_to(PROJECT))]=sha(page)
a2['head_review']='../head_harness/index.html';a2['verified_utc']=when;write(PARENT/'harness_A2/delivery.json',a2)
files={str(p.relative_to(PROJECT)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='delivery.json' and '__pycache__' not in str(p)}
commands=[
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/inspect_head_endpoints.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/inspect_head_paths.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/inspect_neck_sections.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_central_gap.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_outer_neck_probes.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_outer_neck_wide.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_outer_neck_wide.py -- --turn',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_neck_azimuths.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/inspect_neck_motion.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/plot_neck_sections.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/plot_neck_motion.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_yaw_loop_space.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_planar_yaw_loops.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_split_yaw_space.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_split_planar_loops.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_split_planar_loops.py --refine',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_loop_source_solids.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_uart_rising_loop.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_rising_loop_source.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_uart_rising_loop.py --refine',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_uart_flat_space.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/check_uart_flat_loop.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/plot_yaw_loop_review.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/inspect_lateral_neck.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/plot_lateral_neck.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/head_harness/check_head_entry_space.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background --python mechanical/studies/prearrival_finish/head_harness/check_head_entry_shortest.py',
 '/Applications/Blender.app/Contents/MacOS/Blender --background --python mechanical/studies/prearrival_finish/head_harness/check_head_entry_smooth.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/plot_head_entry.py',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/head_harness/publish_head_review.py']
write(HERE/'delivery.json',dict(verified_utc=when,source_main_sha256=d['source_blend_sha256'],main_geometry_changed=False,
    sources=out['sources'],files=files,commands=commands,local_links=checks,geometry_release=False,manufacturing_release=False,
    versions=dict(python=sys.version,matplotlib=matplotlib.__version__,numpy=np.__version__,blender='5.2.2 LTS d13f752e3b9c; inspection.log')))
assert sha(PROJECT/'mechanical/mori_v1_2.blend')==d['source_blend_sha256']
print('HEAD_HARNESS_PUBLISHED',len(files),'files',yaw_count,'yaw conductors',pitch_count,'pitch conductors','main unchanged')
