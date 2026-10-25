"""Record verified M1.58 adoption and mark the previous candidate as adopted."""
from pathlib import Path
import sys,json,hashlib,shutil,datetime
sys.path.insert(0,str(Path(__file__).resolve().parent))
from off_shelf_delivery import verify,sha,read,write
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'mechanical'
p,v,_=verify(check_animation=False);assert p['revision']=='V1.2-M1.58'
q=p['ups_rear_controls'];folder=(PROJECT/q['baseline']).parent;base=read(folder/'baseline.json')
check=read(ROOT/'reports/ups_controls_validation.json');gaps=read(ROOT/'reports/ups_controls_clearances.json')
exports=read(ROOT/'reports/export_manifest.json');paths=read(ROOT/'reports/body_split_validation.json')
assert all(r['status']=='PASS' for r in [check,gaps,paths])
for f,h in base['protected_video'].items():assert sha(PROJECT/f)==h
minimum=min(r['gap_mm'] for a in gaps['static'] for r in a['nearest'])
records=read(ROOT/'reports/off_shelf_commands.json')
assert all(r['returncode']==0 for r in records)
assert not any(r['stage'].startswith('animation') for r in records)
# Preserve this run's actual logs and commands independently of future runners.
out=ROOT/'reports/ups_controls_M1_58';out.mkdir(exist_ok=True)
for record in records:
 source=PROJECT/record['log'];assert sha(source)==record['log_sha256']
 shutil.copy2(source,out/source.name)
if not any(row['stage']=='controls_clearances' for row in records):
    shutil.copy2('/tmp/mori-ups-controls-main-clearances.log',out/'controls_clearances.log')
    records=records+[dict(stage='controls_clearances',command=['/Applications/Blender.app/Contents/MacOS/Blender','-b','mechanical/mori.blend','--python-exit-code','1','--python','mechanical/scripts/check_ups_controls_clearances.py'],returncode=0,log=str((out/'controls_clearances.log').relative_to(PROJECT)),log_sha256=sha(out/'controls_clearances.log'))]
write(out/'commands.json',records)
report=dict(revision=p['revision'],status='PASS',date=datetime.datetime.now().astimezone().isoformat(),approval='采用上充电、下开关',source_main_sha256=sha(ROOT/'mori.blend'),changed_prints=['Body_Rear'],unchanged_existing_parts=check['unchanged_existing_count'],retired_ids=q['retired_ids'],new_reference_ids=list(q['reference_ids']),current_parts=191,current_prints=16,robot_prints=15,dock_prints=1,coupon_exports=4,dock_soft_pad_references_not_exported=4,source_candidate_sha256=sha(folder/'candidate_meshes.json'),video_unchanged=base['protected_video'],animation_updated=False,checks=check['checks'],new_accessory_minimum_free_gap_mm=minimum,head_pose_count=gaps['head_motion']['combinations'],commands='reports/ups_controls_M1_58/commands.json',physical_fit='NOT_TESTED',complete_harness='BLOCKED',manufacturing_release=False)
write(ROOT/'reports/ups_controls_adoption.json',report)
doc=f'''# M1.58：采用上充电、下开关

2026-10-13，用户明确确认“采用上充电、下开关”。主模型、电子细模、静态图和 STL 已更新；本轮不生成视频，不提交 PR。

## 实际改动

- 上方原 DC 试配孔座保持：Ø8 孔、4 mm 座厚、原位置和法线。
- 下方原 Type-C 轴高约 108.92 mm 改为 UPS 原配开关，沿用样品 Ø12 试孔、Ø20×4 mm 一体座。两者沿机身后侧中线排列。
- 封闭旧矩形孔；删除旧接口板、USB 插座、两个固定座、两枚螺钉和两枚嵌件。仅 Body_Rear 打印件改变。
- 188 个保留件网格和位姿不变；增加两个开关／螺母样品参考体，195 件变为 191 件（含维护托架）。导出 15 件本体件、1 件维护底座及 4 件试片；场景另有四块未导出的软垫参考。

尺寸只从 geometry.json#/ups_rear_controls 生成。批准候选的独立网格只供验证，不用作建模源。没有更改原厂 CAM、WeAct 或 UPS 板上的 USB 接口。

## 保存与检查

主模型 SHA256：`{report['source_main_sha256']}`。

- 保存后的模型对照：PASS；相对批准后壳的布尔对称体积差 {check['approved_solid_difference_mm3']['Body_Rear']:.8f} mm³，为数值网格差异，不是加工公差。
- 两个孔座各 192 个材料探针、各 61 个工具位置：PASS。上方 DC 局部几何保留、单连通实体和允许区域外改动检查：PASS。
- 前后壳分别 275 个刚性平移样本：PASS；前壳／车轮等按报告保留。不包含柔性引线。
- 当前刚性件、11 个插头容量和 130 个头部组合姿态：PASS；新增开关到 UPS 最小名义间隙 {minimum:.3f} mm。连续运动和真实装件未资格化。
- 20 个 STL 均导出并回读；电子细模 833 个独立参考物体与主模型坐标匹配。9 张静态图来自保存主模型。
- 本轮统一验证：{v['counts']['PASS']} PASS、{v['counts']['FAIL']} FAIL、{v['counts']['BLOCKED']} BLOCKED、{v['counts']['NOT_TESTED']} NOT_TESTED；只代表记录中的检查。

实际命令和日志：[执行清单](../mechanical/reports/ups_controls_M1_58/commands.json)。构建环境 Blender 5.2.2 LTS d13f752e3b9c、Python 3.13.13、manifold3d 3.5.3。运行 `python3 mechanical/scripts/run_off_shelf_deliverables.py --rebuild`，控件净距检查已纳入默认流水线。本轮收尾同步机械合同的 UPS-R1 接收元数据后，完整重跑，保留生成时的实际输入哈希。

[完整主模型](../mechanical/mori.blend) · [后壳 STL](../mechanical/exports/stl/Body_Rear.stl) · [静态图册](../mechanical/index.html#controls_rear) · [范围对照](../mechanical/reports/ups_controls_validation.json) · [间隙](../mechanical/reports/ups_controls_clearances.json) · [采用凭据](../mechanical/input_assets/ups_controls_M1_58/approval.json)

## 样品与电气边界

开关及螺母引用样品 R36、核对 R55 沿用同一局部网格，按 1:1 变换，标为 PLACEHOLDER / ASSUMED。螺母对边约 13.5 mm 为用户近似测量；Ø12 是样品试孔选择，不是实测螺纹。DC 螺母约 10.5 mm 同理。杆长、尾部、法兰和螺母厚度仍估算。名义杆孔零间隙并不证明实物可装；完整尾线穿孔、PA12 配合与强度、手部操作仍 NOT_TESTED / BLOCKED。

硬件对话已收到“仅一块自制驱动／载板”的授权交接并发布 UPS-R1。它更新了合同和接线需求；原生新电路／PCB 尚未完成。机械侧保留 P5R7 载板作布局参考，未改硬件源。供电并发、满电回灌、默认禁能及真实断电功能按硬件报告继续处理。

## 版本保留

修改前完整 M1.57 保存在 `mechanical/revisions/V1.2-M1.57_before_UPS_controls/mechanical/mori_v1_2.blend`，原尺寸和接口快照在 input_assets/ups_controls_M1_58。原候选仍可查看，页面已标为 M1.58 采用。

M1.57-A1 视频与动画工程字节保持。视频 SHA256：`{base['protected_video']['mechanical/animation/MORI_assembly.mp4']}`。旧视频仍含接口板，不作为本版装配指导。后续按需更新，不自动重做。
'''
(PROJECT/'docs/M1_58_UPS_CONTROLS_ADOPTION.md').write_text(doc)
study=ROOT/'studies/off_shelf_modules_20261013/ups_controls_M1_57'
# Keep the candidate evidence immutable; only its navigation/status gets an adoption notice.
history=study/'pre_adoption_publication';history.mkdir(exist_ok=True)
for name in ['index.html','README.md','delivery.json']:
 if not (history/name).exists():shutil.copy2(study/name,history/name)
s=(history/'index.html').read_text().replace('M1.57 基础上的独立候选 · 尚未应用主模型 · 本轮不生成视频','已按用户确认采用到 M1.58 · 下方对比保留采用前候选证据 · 本轮未生成视频').replace('当前主模型：上方圆口，下方 Type-C。','采用前 M1.57：上方圆口，下方 Type-C。').replace('>当前主模型</a>','>已更新的 M1.58 主模型</a>').replace('revision=V1.2-M1.57#dc','revision=V1.2-M1.58#controls_rear')
s=s.replace('<h1>上方充电口，下方 UPS 开关</h1>','<h1>上方充电口，下方 UPS 开关</h1><p><a href="../../../../docs/M1_58_UPS_CONTROLS_ADOPTION.md">M1.58 采用记录与保存后检查</a>；独立候选文件保留原状态，当前正式文件请从主模型链接打开。</p>')
(study/'index.html').write_text(s)
(study/'README.md').write_text('# 采用状态：已进入 M1.58\n\n用户确认“采用上充电、下开关”。当前采用结果见 [M1.58 记录](../../../../docs/M1_58_UPS_CONTROLS_ADOPTION.md)。下文和本目录 JSON 均为采用前候选证据，保留原 formal_adoption=false 和原来源哈希；它们不代表主模型仍未更新。\n\n'+(history/'README.md').read_text())
write(study/'adoption.json',dict(revision=p['revision'],approved=True,main_sha256=report['source_main_sha256'],adoption_report='../../../reports/ups_controls_adoption.json',preserved_candidate_sha256=sha(study/'ups_controls_candidate.blend'),historical_delivery='pre_adoption_publication/delivery.json'))
old=read(history/'delivery.json');old.update(formal_adoption=True,adopted_revision=p['revision'],main_unchanged=False,scope='Historical candidate outputs unchanged; formal M1.58 adoption is independently checked in main reports',adoption='adoption.json')
old['files'].update({f:sha(study/f) for f in ['index.html','README.md','adoption.json']});write(study/'delivery.json',old)
print('M1_58_ADOPTION_RECORDED',report['source_main_sha256'],flush=True)
