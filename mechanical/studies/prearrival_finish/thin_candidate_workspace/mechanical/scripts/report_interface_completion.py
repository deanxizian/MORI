"""Publish current adopted interfaces separately from unresolved digital work."""
import collections,csv,hashlib,html,json
from pathlib import Path
from animation_page import generate as animation_view
from parts_classification import generate as parts_view

R=Path(__file__).resolve().parents[1];P=R.parent
def read(path):return json.loads((R/path).read_text())
def generate():
 p=json.loads((P/'config/geometry.json').read_text());q=p['interface_completion'];rev=p['revision'];v=read('reports/validation.json');i=read('reports/interface_validation.json');bom=read('reports/bom.json');exports=read('reports/export_manifest.json');checks=read('reports/interface_printability.json')
 assert i['status']=='PASS' and all(not r['entry_blocked_rays'] for r in i['rows'])
 assert read('reports/delivery_consistency.json')['status']=='PASS'
 source_hash=hashlib.sha256((R/'mori_v1_2.blend').read_bytes()).hexdigest()
 assert checks['source_blend_sha256']==source_hash
 drivers=read('studies/interface_completion/catalogue_driver_checks.json');assert drivers['status']=='PASS' and drivers['source_blend_sha256']==source_hash
 for name in ['bearing_lip_candidate','yaw_nut_open_candidate']:
  evidence=read('studies/interface_completion/'+name+'.json');assert evidence['status']=='PASS' and evidence['source_blend_sha256']==source_hash
 animation=animation_view(R);am=read('animation/manifest.json');assert am['source_blend_sha256']==source_hash
 robot_count=sum(r['candidate_stl'] and r['group'] not in ['dock','coupon'] for r in bom)
 seam=min(r['min_sampled_pilot_wall_mm'] for r in i['rows'] if r['id'].startswith('Head_Seam'))
 tasks=[
  ('头部传动连接','BLOCKED','按用户选择保留 SCS0009。配套舵盘、花键、短轴与轴向锁紧等厂家资料；已列明所需图纸，原占位件没有当成已定型件。反力连杆暂未改动。'),
  ('嵌件与紧固件','BLOCKED','已采用 34 个目录嵌件、26 枚 GB823 名义包络及一枚 M2×14 内六角螺钉；已核孔口、孔壁、盲孔底和啮合。其余螺母/五金仍有候选与装入方式待确认，未把整机紧固件表标为冻结。'),
  ('WeAct 排母和对插','BLOCKED','已建 Würth 8.5 mm 排母和插头候选。A–D 针脚匹配；E 的排针方向和基板孔阵列不匹配。Rear J3 插头与排母焊脚另有约 0.314 mm³ 交叠。电路交接已写好，原生 PCB 未改。'),
  ('全部打印件与完整装配','FAIL','全件网格/壁厚采样与工具、步骤复核已做；已给相机孔腔、舵机螺母薄壁、轮轴承挡边、下壳孔口及上壳路径分别做好候选，等用户确认后应用和整机重验。当前主模型的问题仍记FAIL。')]
 remaining=[
  ('相机座旧孔腔','FAIL','当前局部约 0.362 mm；填平候选通过实体与 130 姿态检查，待用户确认。','studies/interface_completion/thin_mount_comparison.svg'),
  ('俯仰上侧螺母槽','FAIL','当前与轴承孔之间约 0.102 mm；螺母移入现有耳座、M2×8、短侧装口候选已做，待确认。','studies/interface_completion/thin_mount_candidates.json'),
  ('后侧 yaw 螺母薄壁','FAIL','原槽局部约 0.192 mm。保留螺母位置、开短前入口并重整4.2AF槽的候选已做；顶面承压材料约2.6 mm，名义装入、两种螺母包络止转和130姿态检查通过。待用户确认，未改反力连杆。','studies/interface_completion/yaw_nut_open_candidate.json'),
  ('四个轮驱连接螺母','FAIL','原封闭槽无法装入。5×1.9 mm 短侧装口候选通过插入/止转检查，等待用户选择。','studies/interface_completion/drive_nut_entry.svg'),
  ('轮轴承内侧挡边','FAIL','当前0.75 mm。候选内轴承外移0.5 mm，使挡边1.25 mm；同步延长金属轴肩、短隔套改4.5 mm。73姿态/侧及底盖、电机组件拆卸通过，待用户确认。','studies/interface_completion/bearing_lip_candidate.json'),
  ('机身下壳孔口','FAIL','当前原长沉孔留下约0.29 mm尖薄片。四拼缝点移位候选消除此处薄片，下壳采样最薄约1.74 mm；待确认并应用。','studies/interface_completion/body_seam_complete_checks.json'),
  ('机身上壳装入/取出','FAIL','现有孔位妨碍取壳。四拼缝点移至X±22/Y±71后：卸车轮、下壳及头部/固定桥，上壳带喇叭/后接口板倾斜15°、抬14 mm、后移14 mm再上提。369姿态和工具包络检查通过；尚未应用。','studies/interface_completion/body_seam_comparison.svg'),
  ('WeAct E / 后接口 J3','BLOCKED','E 需要用户选择排针路线和电路任务修孔阵列；J3 与长焊脚的冲突需电路任务处理。','studies/interface_completion/WEACT_E_HANDOFF.md')]
 report={'revision':rev,'project_digital_release':'FAIL','implemented_interface_checks':i['status'],'manufacturing_release':False,'physical_measurements':'NONE','source_blend_sha256':source_hash,'four_tasks':[dict(item=a,status=b,detail=c) for a,b,c in tasks],'remaining_digital':[dict(item=a,status=b,detail=c,evidence=d) for a,b,c,d in remaining],'user_deferred':'SCS0009 matching horn / dependent shaft and locking; cable routing'}
 (R/'reports/interface_completion_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (R/'reports/assembly_completion_progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 headers=['part','sampled_minimum_mm','ray_samples','samples_under_1mm','geometry_source']
 with (R/'reports/interface_print_review.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(headers)
  for row in checks['rows']:w.writerow([row['id'],row['sampled_minimum_mm'],row['samples'],row['under_1mm_samples'],source_hash])
 with (R/'reports/interface_insert_schedule.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['insert_id','host','catalogue','pilot_diameter_mm','blind_depth_mm','min_pilot_wall_mm','blind_end_wall_mm','screw','screw_length_mm','thread_engagement_mm','entry_screen'])
  results={r['id']:r for r in i['rows']}
  for r in q['inserts']:
   t=results[r['id']];w.writerow([r['id'],r['host'],r['sku'],r['pilot_mm'],r['pilot_depth_mm'],t['min_sampled_pilot_wall_mm'],t['sampled_blind_end_wall_mm'],r['screw'],r.get('screw_length_mm','existing nominal'),t['nominal_thread_engagement_mm'],'PASS' if not t['entry_blocked_rays'] else 'FAIL'])
 md=f'''# MORI {rev} · 接口与打样前复核

已应用用户确认的两处头壳拼缝孔配对移动：X±43→±41 mm，Z259→261 mm。最终孔口已清除旧皮膜，嵌件位置不变。两处最小采样孔壁约 {seam:.3f} mm；34 处嵌件入口各用216条轴向射线核查，孔壁、盲孔底及螺钉啮合另查。当前本体候选打印件 {robot_count} 件，没有新增机器人打印件。

34 个嵌件采用 FINE SL-M2×3 / SL-M3×4 目录包络，试配孔分别3.25 /4.05 mm；26 枚 M2 小盘头螺钉使用 GB823名义尺寸。这26处已用 Wiha42415 的PH1 /4mm×60mm刀杆和18mm手柄包络重查，分阶段工具空间通过。下方俯仰舵机保留 M2×14，采用 DIN912 内六角头；PB210.1,5（1.5 mm、50×14 mm）的长端用于单独头托装配，有限工具摆角检查通过。螺纹、压装和手持施力仍需样件。

## 四项任务的实际状态

|项目|状态|结果|
|---|---|---|
'''+ '\n'.join(f'|{a}|{b}|{c}|' for a,b,c in tasks)+'''

## 实物到货前仍要解决

'''+ '\n'.join(f'- **{a} — {b}**：{c} [证据](../{d})' for a,b,c,d in remaining)+f'''

## 本轮实际检查

已实施修改的专项检查为 PASS；主模型现有检查项计 {v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL / {v['counts']['BLOCKED']} BLOCKED / {v['counts']['NOT_TESTED']} NOT_TESTED。这个统计范围不包括上表新增的完整装配/打印缺陷，所以整机打样前数字审查仍为 FAIL。130 个头部姿态没有检出本轮新增交叠。重复生成、保留非生成对象、STL回读、渲染/导出几何一致性、详细PCB副本与动画检查均分别有报告。

- [实际流水线命令](interface_commands.json) / [接口检查](interface_validation.json)
- [全打印件采样](interface_printability.json) / [孔与嵌件清单](interface_insert_schedule.csv)
- [26处PH1实际规格工具检查](../studies/interface_completion/catalogue_driver_checks.json)
- [一致性](delivery_consistency.json) / [动画检查](../animation/validation.json)
- [电路交接](../studies/interface_completion/WEACT_E_HANDOFF.md)
- [SCS0009配套资料需求](../studies/interface_completion/SCS0009_VENDOR_REQUIREMENTS.md)

全件壁厚采用面积分层、每件最多20000个三角形中心的反向法线射线，不能当作全局最小厚度证明。恰好1 mm的薄面浮点值可能略小于1；尖角、导入边和必要过渡仍逐处分类。已知实际薄壁没有借此豁免。当前模板动画仍只表达步骤；上壳使用独立预装镜头，尚不能据动画判断可装入。

## PA12试片和到货验证

另生成一件60×40×8 mm的辅助试片：M2嵌件孔3.05–3.45、M3嵌件孔3.85–4.25 mm（各0.1 mm步进），M2/M3各三个螺母槽变体；它不是机器人新增零件。[试片STL](../studies/interface_completion/coupons/interface_coupon.stl) / [Blender](../studies/interface_completion/coupons/interface_coupon.blend) / [坐标图](../studies/interface_completion/coupons/map.svg)。同一PA12供应工艺核对孔径、嵌件装入/拉拔、螺母止转后再选择补偿；本文件没有下单。

到货后需核：SCS0009原配舵盘；CAM/相机照片估计尺寸及夹持；SP3040耳厚/孔公差；电池包、线头和绑带；排母插深、完整对插、线束及工具手握；PA12配合、紧固力、蠕变/冲击和实际运动。电气/电池/急停/平衡验证交对应任务，机械几何不代替这些资格。

目录来源：[FINE](https://www.finesz.com/shk.php)、[GB823尺寸参考](https://www.wqjgj.cn/product/luoding/shizicao/2158.html)、[M2×14 DIN912](https://www.westfieldfasteners.co.uk/Bolts-Screws-Metric/Socket-Head-Cap-Screw-M2x14-A2-Stainless.html)、[PB210](https://www.pbswisstools.com/en/tools/quality-hand-tools/precisionbits/product/pb-210)、[Wiha42415](https://wiha.com/tools/screwdrivers/precision-screwdrivers/picofinish/phillips/picofinish-fine-screwdriver/42415)。本轮没有实物测量、采购或制造放行；硬件原生文件和 components.json 保持只读。
'''
 for name in ['接口复核_M1_42.md','REPORT.md']:(R/'reports'/name).write_text(md)
 (R/'README.md').write_text(f'# MORI {rev}\n\n[当前模型](mori_v1_2.blend) · [网页](index.html) · [四项任务与未完成问题](reports/接口复核_M1_42.md)。\n\n已应用拼缝孔、目录嵌件和下侧俯仰螺钉方案。完整打样前数字审查仍有 FAIL，尚未制造放行。历史专题页不是当前状态来源。\n')
 (R/'reports/组装与打印.md').write_text('# 装配与打印状态\n\n当前没有冻结的整机装配指导。头部舵盘等待厂家资料；机身上壳拆装路径及附件步骤仍在修复。不要用演示动画代替实际装入路径。\n\n详见[本轮报告](接口复核_M1_42.md)、[工具分阶段检查](../studies/interface_completion/bench_sequence_checks.json)（其中下侧俯仰旧工具失败已由当前内六角长端方案替代）和[试片](../studies/interface_completion/coupons/manifest.json)。\n')
 style='<style>*{box-sizing:border-box}body{margin:0;background:#f1f3f2;color:#23342d;font:16px/1.7 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:30px 24px 80px}h1{font-size:34px;line-height:1.35}h2{margin-top:40px}a{color:#146c53}nav,.links{display:flex;gap:20px;flex-wrap:wrap;margin:18px 0}.notice{padding:18px 22px;background:#fff2d8;border:1px solid #dec59d;border-radius:10px}table{width:100%;border-collapse:collapse}td,th{padding:13px;border-bottom:1px solid #ccd6d0;text-align:left;vertical-align:top}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}figure{margin:0;background:white;border:1px solid #d3dad7;border-radius:10px;overflow:hidden}figure img{width:100%;display:block}figcaption{padding:14px}.FAIL{color:#a3342b}.PASS{color:#176b49}.BLOCKED{color:#805c19}small{color:#53675c}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:20px 14px}h1{font-size:27px}table{font-size:13px}}</style>'
 def table(rows):return '<table>'+''.join('<tr>'+''.join(f'<td class="{html.escape(x) if x in ["FAIL","PASS","BLOCKED"] else ""}">{html.escape(str(x))}</td>' for x in row)+'</tr>' for row in rows)+'</table>'
 def gallery(rows):return '<div class="grid">'+''.join(f'<figure><a href="{f}"><img loading="lazy" src="{f}?revision={rev}" alt="{html.escape(t)}"></a><figcaption>{html.escape(t)}</figcaption></figure>' for f,t in rows)+'</div>'
 page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 接口复核</title>{style}<main><nav><b>MORI {rev}</b><a href="#interface">本轮修改</a><a href="#remaining">四项进度</a><a href="#structure">结构</a><a href="#appearance">外观</a><a href="#checks">检查</a><a href="studies/interface_completion/comparisons.html">PNG 对比图汇总</a></nav><h1>头壳拼缝孔已调整，<br>嵌件与工具接口逐项复核。</h1><p>34处目录嵌件 · {robot_count}件本体候选打印件 · 保留SCS0009。</p><p class="notice"><b>整机打样前数字审查仍有未解决项。</b>当前专项通过，不代表全部固定、壁厚和装配路径已完成；下表列出明确问题与尚未应用的候选。</p><div class="links"><a href="mori_v1_2.blend">当前 Blender</a><a href="reports/接口复核_M1_42.md">详细报告</a><a href="manufacturing.html">打印件与五金</a><a href="mori_electronics_detail.blend">PCB详细副本</a></div><section id="interface"><h2>已应用的修改</h2><p>前后壳两处对应孔一起内移2 mm、上移2 mm；最薄采样孔壁约{seam:.2f} mm。34处嵌件按目录尺寸重建，短座、盲孔底与螺钉长度同步。下方俯仰螺钉采用M2×14内六角，在独立头托上用L形扳手长端装配。</p>'+gallery([('studies/interface_completion/seam_applied_comparison.svg','拼缝孔轴对比；最终孔口已清除薄膜'),('renders/head_section.png','当前主模型：头部内部')])+'</section><section id="remaining"><h2>四项任务的实际状态</h2>'+table(tasks)+'<h2>尚未解决的数字问题</h2>'+table([(a,b,c) for a,b,c,_ in remaining])+'<div class="links"><a href="studies/interface_completion/thin_mount_comparison.svg">相机/舵机座候选</a><a href="studies/interface_completion/drive_nut_entry.svg">轮驱螺母入口候选</a><a href="studies/interface_completion/body_seam_comparison.svg">机身移孔和取壳候选</a><a href="studies/interface_completion/remaining_seats_comparison.svg">轴承和yaw螺母座候选</a><a href="studies/interface_completion/WEACT_E_HANDOFF.md">排母和J3电路交接</a></div></section><section id="structure"><h2>当前结构</h2>'+gallery([('renders/internal.png','腹部结构与板卡'),('renders/exploded.png','实际零件分解展示；不是路径验证')])+'</section><section id="appearance"><h2>当前外观</h2>'+gallery([('renders/45_assembled.png','45°总装'),('renders/rear.png','后视与Type-C入口')])+'</section>'+animation+f'<section id="checks"><h2>验证与文件</h2><p>已实施修改专项 {v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL；完整打样前审查另有上表的FAIL/BLOCKED。34处孔口、孔壁和盲孔底通过专项采样；130个头部姿态无本轮新增干涉。渲染、STL、详细PCB副本和动画来源一致。</p><div class="links"><a href="reports/interface_completion_status.json">整体状态</a><a href="reports/interface_validation.json">接口专项</a><a href="reports/interface_printability.json">全件壁厚采样</a><a href="reports/interface_commands.json">实际命令</a><a href="reports/export_manifest.json">STL清单</a></div><h2>辅助试片</h2><p>60×40×8 mm，一件PA12孔径与螺母槽试片，不增加机器人零件。实物测试完成后再确定打印补偿与安装工艺。</p><div class="links"><a href="studies/interface_completion/coupons/interface_coupon.stl">试片STL</a><a href="studies/interface_completion/coupons/interface_coupon.blend">试片Blender</a><a href="studies/interface_completion/coupons/map.svg">孔位图</a></div><small>PROTOTYPE / UNVALIDATED。没有实物测量、采购或制造放行；有限采样不证明打印强度或实机平衡。</small></section></main></html>'
 (R/'index.html').write_text(page)
 previews=read('reports/parts_preview_manifest.json');manufacturing=parts_view(R,rev,bom,previews,exports)
 manufacturing=manufacturing.replace('当前SP3040用两枚试配M2×6','当前SP3040用两枚M2×5')
 (R/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">返回当前状态</a><p class="notice">该页是零件分类；尚未制造放行。孔口/薄壁、螺母装入、排母和机身服务路径仍见<a href="reports/接口复核_M1_42.md">当前问题清单</a>。</p>'+manufacturing+'</main></html>')
 (R/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">返回当前状态</a><h1>{rev}部件预览</h1>'+gallery([(r['file'],r['id']+' · '+r['name']) for r in previews])+'</main></html>')
 study=R/'studies/interface_completion'
 (study/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="../../index.html#interface">当前主模型与状态</a><h1>{rev}接口复核与候选</h1><p><a href="comparisons.html">打开 1–7 项 PNG 对比图汇总</a></p><p>拼缝孔和目录嵌件已应用。以下结构候选尚未应用。</p>'+gallery([('seam_applied_comparison.svg','已采用：拼缝孔配对移动'),('thin_mount_comparison.svg','待确认：填平旧相机孔腔、移入俯仰上侧螺母'),('drive_nut_entry.svg','待确认：轮驱螺母短侧装口'),('body_seam_comparison.svg','待确认：机身四处拼缝移孔与倾斜取壳'),('remaining_seats_comparison.svg','待确认：轴承挡边与yaw螺母槽'),('weact_E_alignment.svg','待电路处理：E排针/孔阵列')])+'<div class="links"><a href="../../reports/接口复核_M1_42.md">完整报告</a><a href="WEACT_E_HANDOFF.md">电路交接</a><a href="SCS0009_VENDOR_REQUIREMENTS.md">SCS0009厂家资料需求</a><a href="coupons/interface_coupon.stl">辅助试片</a></div></main></html>')
 print('INTERFACE_REPORT_PUBLISHED',rev,source_hash,flush=True)
