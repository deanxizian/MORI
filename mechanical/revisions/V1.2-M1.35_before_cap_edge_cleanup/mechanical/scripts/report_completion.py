"""Current source-backed assembly-completion report, replacing the current gallery.

Historical study pages remain archived/reference material, not current truth.
"""
from pathlib import Path
import json,html,hashlib
from parts_classification import generate as manufacturing_view
from module_report import printing_audit
from animation_page import generate as animation_view

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda name:json.loads((ROOT/'reports'/name).read_text())
esc=html.escape

def generate():
 p=json.loads((PROJECT/'config/geometry.json').read_text());rev=p['revision'];v=load('validation.json');checks={c['id']:c for c in v['checks']};g=load('assembly_completion_geometry.json');a=load('assembly_completion_validation.json');native=load('native_electronics_geometry.json');nv=load('native_electronics_validation.json');ex=load('export_manifest.json');bom=load('bom.json');bm=load('build_manifest.json');rb=load('rebuild_check.json');dc=load('delivery_consistency.json');motion=load('head_motion.json');wheel=load('wheel_clearance.json');mass=load('mass_budget.json')
 assert a['status']=='PASS' and v['counts']['FAIL']==0
 assert all(x['sha256_matches'] for x in nv['sources'])
 assert rb['status']==dc['status']==load('electronics_detail_validation.json')['status']=='PASS'
 previews=load('parts_preview_manifest.json');by={b['id']:b for b in bom}
 for x in previews:x.update(name=by[x['id']]['name'],category=by[x['id']]['category'],status=by[x['id']]['data_status'])
 (ROOT/'reports/parts_preview_manifest.json').write_text(json.dumps(previews,ensure_ascii=False,indent=2)+'\n')
 con=load('part_consolidation.json');con['robot_print_after']=sum(b['candidate_stl'] and b['group'] not in ['dock','coupon'] for b in bom);con['fasteners_after']=sum(any(k in b['id'] for k in ['Screw','Nut','Insert','Washer']) and not b['id'].startswith('Coupon') for b in bom)
 con['current_completion']='CAM four integral seats/four M2 trial screws; existing-parts camera capture; battery strap. No new robot printed part.'
 (ROOT/'reports/part_consolidation.json').write_text(json.dumps(con,ensure_ascii=False,indent=2)+'\n')
 manufacturing=manufacturing_view(ROOT,rev,bom,previews,ex)
 (ROOT/'reports/打印件审查.md').write_text(printing_audit(bom))
 rear=native['rear_mount'];counts=v['counts'];pairs=load('static_interference.json')['failed_pairs']
 rows=[
 ('CAM板固定','名义设计/检查完成','32.6mm原孔网格；四个短座并入Pitch_Cradle，四枚M2×6及试配短嵌件；新增打印件0。先在台面装到头托，再安装头托。板厚、孔径、器件高度仍有照片估算。'),
 ('OV3660定位与限位','候选检查完成；依赖头壳锁紧','Display_Frame定位槽＋Head_Front两处内侧挡边，无独立压盖、螺钉或弹性卡臂。镜头座保持原重建尺寸，沿光轴退入3.8mm；外侧孔口局部扩口。侧隙0.2mm、前后各0.15mm是试配值，未宣称预紧或抗振。'),
 ('电池包固定','名义设计/检查完成','按用户选择保留71×55×20mm成品3S候选；20mm自粘绑带经托盘槽和底面绕回顶部，顶垫1mm。绑带厚1.5mm、搭接30mm为候选需求，实物和压缩待核。'),
 ('四块自绘PCB','正式交接已同步','Motion/Power/Rear采用P5R6，IMU按同一交接采用P5R4；原生板框、孔、位号、安装面和装件1:1，源文件哈希通过；没有修改电路文件。'),
 ('头壳与LCD完整紧固','未完成','已有配对孔/座面，但完整螺钉长度、实际装入路径和保持仍需逐项补齐。相机限位依赖前壳最终锁紧，不能据局部捕获测试声称整只头已可靠固定。'),
 ('面罩与光学保护片','未完成','原厂LCD已有盖板；额外面罩/保护片和独立相机窗口的保持、是否合并及拆换需确认，未虚构胶带厚度或卡扣。'),
 ('头部轴承、舵盘及短轴','待选型/实物接口','本体及输出轴按厂图重建；花键配套舵盘、轴承具体料号、轴向保持及加工配合仍未完全定版。'),
 ('WeAct排母、对插插头','待选型','原厂核心板CAD与原生基板已在模型内；6mm排母高度是安装假设，真实插座、插深及防松尚未核定。'),
 ('后接口开关可达性','BLOCKED',f'P5R6拨柄仍比USB口面缩进{rear["stem_behind_USB_mouth_mm"]:.1f}mm；操作轴高差约{rear["switch_actuator_axis_z_mm"]-rear["USB_axis_z_mm"]:.1f}mm。需要电路任务调整器件位置/选型，或确认机械拨杆，当前未擅自移动PCB位号。'),
 ('独立3S充电/PD板','待硬件选型','后接口板不是充电器。没有完整型号、尺寸、孔位及端口/热约束，不能伪造精细模型或最终固定。'),
 ('轮胎、软垫与五金配合','待试配','当前名义包络、试配孔和金属轴方案保留；不是所有供应商、公差和螺纹规格均已核定。'),
 ('线束','按用户要求延后','未新增预估走线孔。插头、弯曲、服务环、应力释放和全运动线束检查均未完成。'),
 ('强度/打印/实机平衡','NOT_TESTED','有限几何采样、名义质量估计和封闭网格不等于抗冲击、装配强度、热安全或自平衡通过。')]
 progress={'revision':rev,'completed_nominal_items':['CAM mounting','camera captive pocket','battery strap retention','P5R6 PCB receipt'],'rows':[dict(item=x,status=y,detail=z) for x,y,z in rows],'manufacturing_release':False,'physical_measurements':'NONE','wiring':'DEFERRED_BY_USER'}
 (ROOT/'reports/assembly_completion_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
 table='| 项目 | 状态 | 本版结果/下一步 |\n|---|---|---|\n'+'\n'.join(f'| {x} | {y} | {z} |' for x,y,z in rows)
 note=f'''# MORI {rev} · 装配问题逐项处理

本版补齐CAM固定、电池包绑带，生成由现有支架与前壳夹持相机的候选，并接入正式P5R6电路交接。当前本体候选打印件仍为{con['robot_print_after']}件；新增CAM固定用4枚M2×6和4枚试配嵌件。绑带/软垫为采购或裁切件，不混入硬质打印STL。

{table}

实际执行：Blender {bm['blender']}，build.py、两次重复生成、validate.py、render.py、export.py，以及PCB详细模型拆分/回读。整机报告{counts['PASS']} PASS、{counts['FAIL']} FAIL、{counts['BLOCKED']} BLOCKED、{counts['NOT_TESTED']} NOT_TESTED。源哈希、重复生成、保留非生成对象、渲染/导出一致性均通过。完整命令见assembly_completion_commands.json和commands.json。

相机局部：41个装入位置（0.5mm步长）、25个前壳闭合位置（0.5mm步长）、6个0.5mm逃逸探针均符合候选限位要求。99条假设针孔视场射线通过，外部130个头部姿态检查通过；假设水平57°/垂直44°并不是实测标定。相机与屏幕间仍有3.0mm模型白壳带。前壳/窗口材料透射、反射、照片尺寸公差、紧固后稳定性尚未验证。总轴向名义浮动0.30mm，不宣称已有预紧；到货后要实测并收紧配合。

CAM：61个0.5mm步长的台面装板位置与4支Ø3×30mm工具直杆检查通过。31mm宽的连续背板保留两侧开放进声通路；没有恢复麦克风导管。真实插拔、手握空间和声学录音未验证。

电池：拆下上下壳（扬声器/后接口板随上壳一起取走）、断开线束、卸托盘两侧螺钉后，电池/托盘/绑带/顶垫一起向前抽出；41个3mm步长位置通过。柔性绑带穿绕动作、拉紧力及耐磨未仿真；不把刚性渲染的带状网格当作硬质压盖。

全机静态实体交叠{len(pairs)}项；头部{motion['poses']}个Yaw/Pitch联合姿态无检出穿插。LCD的两处连接器仍使用保守代理，因此全硬件静态/运动资格仍BLOCKED；有限采样不是连续空间证明。全局自交及最小壁厚完整算法仍NOT_TESTED。{ex['exported_count']}个候选STL已以装配坐标导出并回读毫米尺寸，采购件未进入外壳STL。

文件：../mori_v1_2.blend 当前总装；../mori_electronics_detail.blend 逐位号模型；../studies/assembly_completion/ 当前专题图。geometry.json及mechanical_interfaces.json仍为共享尺寸/接口来源。没有采购、打印、加工或实机平衡验证。
'''
 (ROOT/'reports/装配补齐_M1_35.md').write_text(note)
 (ROOT/'reports/REPORT.md').write_text(note)
 (ROOT/'README.md').write_text(f'# MORI {rev}\n\n当前总装：[mori_v1_2.blend](mori_v1_2.blend)。[预览](index.html) · [进度与限制](reports/装配补齐_M1_35.md) · [全部检查](reports/validation.json)。\n\n共享参数：../config/geometry.json；接口：../contracts/mechanical_interfaces.json。没有制造放行或实物测量。\n')
 assembly='''# 当前组装补充

1. 按原轮驱方案预装金属法兰轴、轴承、隔套及共用底盖。金属轴、螺钉、轴承不是打印件。
2. 托板底面先装IMU和9V/6V模块，再接轮驱框架；上面装运动基板、WeAct、电源板，之后安装插接承重桥与两侧M3锁紧。
3. 台面上把小型3S电池置于托盘软垫内，穿好20mm自粘绑带、顶部软垫并搭接。随托盘滑入，锁两侧限位螺钉。绑带长度和预紧到货后确认。
4. 安装头部承重轴承及两轴舵机。先把CAM主板用四枚M2×6固定到头托的一体短座，再装头托与两侧短轴；舵盘/轴向保持仍需实物接口核定。
5. 固定屏幕叉架；相机小模组从光轴前侧放入定位槽。合上前壳时，两处内侧挡边限制镜头塑料座，不压镜筒/FPC。头壳完整锁紧和LCD三处座的紧固件仍待补齐，不是最终可制造装配指导。
6. 喇叭与后接口板先固定在拆下的上壳，再合壳、装轮。后板开关可达性尚未解决；不宣称充电器已完整选定或可以上电。

线束设计按用户要求延后。动画只解释名义零件位置和步骤，没有柔性穿带/走线仿真或连续装配路径证明。候选打印前需同材料/方向试打平面缝、嵌件孔和局部接口；不可把任一间隙值推广到所有打印机。
'''
 (ROOT/'reports/组装与打印.md').write_text(assembly+'\n完整状态见[装配补齐_M1_35.md](装配补齐_M1_35.md)。\n')
 sources='\n'.join(f'- {r["board"]}: `{r["native_file"]}`；哈希匹配{r["sha256_matches"]}，最大导入顶点误差{r["max_import_vertex_error_mm"]:.5f}mm；这只验证导入，不是实物精度。' for r in nv['sources'])
 source_doc=f'''# 电子模型与来源 · {rev}

正式交接：hardware/v1_2/handoff/mechanical_P5R6.json；motion/power/rear为P5R6，IMU为P5R4。硬件原生文件和components.json保持只读。

{sources}

原厂LCD与WeAct保留原厂CAD1:1；CAM33700按官方37×37mm板框、32.6mm孔网格与官方照片重建，OV3660按对应照片重建。照片估计的孔径、厚度、器件高度不是厂商完整CAD，更不是MEASURED。相机装配位置本轮退入3.8mm，镜头和载板尺寸没有缩放。电池仍为Tenergy31013的71×55×20mm候选包络，未实测出线/BMS/公差。

电源板的两路5V降压已集成在U60/U70，未额外建两块5V模块。当前另两块工程参考是轮驱9V D36V50F9、头部6V D24V22F6，依硬件交接保留；实际电气/热能力及预算未获资格验证。

查看每个器件的evidence、dimension_basis、limitations和source_native_sha256。原厂CAD、原生布局、库模型、厂图重建和照片估算分开标记。没有采购件被标为MEASURED。全体未完成项见[装配补齐_M1_35.md](装配补齐_M1_35.md)。
'''
 for f in ['电路板精细模型.md','采购件选型.md','purchased_dimensions.md','设计与选型分工.md','外购与自制.md']:(ROOT/'reports'/f).write_text(source_doc)
 feedback=f'''# 后接口PCB机械反馈 · {rev}

以正式P5R6原生文件为准。板框24×25×1.6mm，H1/H2为原生(3,11)/(21,11)，机械侧未移动位号。壳体一体座及底部两枚M2×6保留。

SW1拨柄比USB口面缩进{rear['stem_behind_USB_mouth_mm']:.1f}mm，操作轴间距{rear['switch_actuator_axis_z_mm']-rear['USB_axis_z_mm']:.1f}mm，外壳正常操作仍BLOCKED。移动整板不会改变两器件的相对差值。建议电路任务评估SW1向原生−Y移约8.8mm或重新选更长拨柄；需核对背面USB、焊脚、器件公差和操作空间，未在机械模型里虚构改板。另一个备选是独立机械拨杆，但需用户确认新增零件。

独立3S充电/PD模块尚未选定；接口板本身不是充电器。给出准确型号、尺寸、孔位、对插及出线/热需求后，再补完整固定。无独立function/reset按钮。完整几何数据见reports/rear_interface_geometry.json。
'''
 (ROOT/'INTERFACE_PCB_REQUIREMENTS.md').write_text(feedback)
 (ROOT/'PCB_LAYOUT_FEEDBACK_M1_23.md').write_text(feedback+'\n此文件名保留兼容旧链接，正文为当前正式交接反馈。\n')
 style='''<style>*{box-sizing:border-box}body{margin:0;background:#edf0ed;color:#20312c;font:16px/1.7 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1200px;margin:auto;padding:28px 24px 80px}a{color:#17694f}nav{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #c7d2cb;padding-bottom:16px}h1{font-size:36px;line-height:1.3}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}figure{margin:0;background:white;border:1px solid #d1d9d3;border-radius:12px;overflow:hidden}img{display:block;width:100%}figcaption{padding:14px}.notice{background:#fff6dc;border:1px solid #e2cf9c;padding:16px 20px;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;border:1px solid #cbd6cc;text-align:left;vertical-align:top}h2{margin-top:42px}.links{display:flex;flex-wrap:wrap;gap:18px;margin:22px 0}.PASS{color:#187744}.FAIL{color:#c22}.BLOCKED,.NOT_TESTED{color:#926317}small{color:#657269}@media(max-width:700px){.grid{grid-template-columns:1fr}main{padding:20px 14px}h1{font-size:29px}table{font-size:12px}}</style>'''
 def gallery(items):return '<div class="grid">'+''.join(f'<figure><a href="{path}"><img loading="lazy" src="{path}?revision={rev}" alt="{esc(title)}"></a><figcaption>{esc(title)}</figcaption></figure>' for path,title in items)+'</div>'
 tr=''.join(f'<tr><td>{esc(x)}</td><td>{esc(y)}</td><td>{esc(z)}</td></tr>' for x,y,z in rows)
 page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev}</title>{style}<main><nav><b>MORI · {rev}</b><a href="#completion">本轮固定</a><a href="#structure">内部结构</a><a href="#appearance">外观</a><a href="#remaining">剩余事项</a><a href="#checks">检查</a></nav><h1>CAM 与电池补齐固定，<br>相机由现有零件限位。</h1><p>本体仍为{con['robot_print_after']}件候选打印件；相机没有新增压盖、螺钉或卡臂。四块自绘板已同步正式P5R6交接（IMU为P5R4）。</p><div class="links"><a href="mori_v1_2.blend">当前总装 Blender</a><a href="mori_electronics_detail.blend">逐位号 Blender</a><a href="reports/装配补齐_M1_35.md">装配进度与限制</a><a href="manufacturing.html">打印件与五金</a></div><p class="notice">相机、CAM等细节仍包含照片估算。头壳/LCD完整紧固、保护片保持、舵盘/排母/充电板选型及后开关可达性仍有待完成；无实物测量、打印或整机制造放行。</p><section id="completion"><h2>当前固定结构</h2>'''
 page+=gallery([('studies/assembly_completion/cam_mount.png','CAM四孔固定；短座并入原头托'),('studies/assembly_completion/battery.png','20mm柔性绑带与电池托盘；不是打印压盖'),('studies/assembly_completion/camera_pocket.png','原屏幕支架上的相机定位槽'),('studies/assembly_completion/camera_rear.png','前壳两处内侧挡边捕获塑料镜头座')])
 page+='<p>先把相机放入定位槽，再合上前壳。局部限位、装入/合壳采样与假设视场通过；尚未实测夹持力、预紧或抗振。相机的最终保持依赖头壳紧固完成。</p></section><section id="structure"><h2>同一套模型的内部结构</h2>'
 page+=gallery([('studies/assembly_completion/head.png','头部内部；两轴及CAM安装'),('renders/internal.png','电池与四块自绘PCB'),('renders/head_section.png','双轴头部剖视'),('renders/exploded.png','装配分解展示；STL仍按装配坐标导出')])+'</section><section id="appearance"><h2>外观与正交检查图</h2>'
 page+=gallery([(f'renders/{n}.png',title) for n,title in [('45_assembled','45°总装'),('front','前视'),('side','侧视'),('rear','后视；开关操作仍待完善'),('top','顶视'),('bottom','底视'),('clearance','离地与轮壳间隙')]])+'</section>'
 animation=animation_view(ROOT);page+=animation
 page+=f'<section id="remaining"><h2>逐项进度</h2><table><tr><th>项目</th><th>状态</th><th>结果及下一步</th></tr>{tr}</table></section>'
 cr=''.join(f'<tr><td>{esc(c["id"])}</td><td class="{c["status"]}">{c["status"]}</td><td>{esc(c["summary"])}</td></tr>' for c in v['checks'])
 page+=f'''<section id="checks"><h2>实际执行与检查</h2><p>{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['BLOCKED']} BLOCKED / {counts['NOT_TESTED']} NOT_TESTED。静态检出交叠{len(pairs)}项；头部{motion['poses']}个联合姿态。两处LCD连接器使用保守代理，完整硬件资格仍未通过。重复生成与渲染/导出一致性均PASS；{ex['exported_count']}个候选STL已回读单位和尺寸。</p><div class="links"><a href="reports/validation.json">完整检查</a><a href="reports/assembly_completion_validation.json">本轮固定专项</a><a href="reports/commands.json">运行命令</a><a href="reports/bom.csv">部件表</a><a href="reports/export_manifest.json">STL清单</a><a href="reports/组装与打印.md">组装顺序</a><a href="INTERFACE_PCB_REQUIREMENTS.md">接口板反馈</a></div><details><summary>展开各项检查</summary><table>{cr}</table></details><p><small>Blender {bm['blender']}；所有图均来自本版实际模型。有限采样、名义质量与网格检查不证明连续运动、材料强度、热性能或实机平衡。</small></p></section></main></html>'''
 (ROOT/'index.html').write_text(page)
 (ROOT/'manufacturing.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'+style+'<main><a href="index.html">返回当前装配</a>'+manufacturing+'</main></html>')
 cards=gallery([(x['file'],x['id']+' · '+x['name']+' · '+x['category']) for x in previews])
 (ROOT/'parts.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'+style+f'<main><a href="index.html">返回当前装配</a><h1>{rev} · 部件目录</h1>'+cards+'</main></html>')
 # Same current geometry and evidence, with local paths rewritten for the study.
 study=ROOT/'studies/assembly_completion';study.mkdir(exist_ok=True)
 (study/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'+style+f'<main><a href="../../index.html">当前总装</a><h1>{rev} · 固定补齐</h1>'+gallery([(n+'.png',t) for n,t in [('cam_mount','CAM四孔短座'),('battery','电池绑带'),('camera_pocket','相机定位槽'),('camera_rear','前壳内侧限位'),('head','头部装配')]])+f'<table>{tr}</table><a href="../../reports/assembly_completion_validation.json">本轮实际模型检查</a></main></html>')
 print('COMPLETION_REPORT_COMPLETE',rev)

if __name__=='__main__':generate()
