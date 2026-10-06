"""Current M1.43 delivery; every completed item tied to the final model."""
import csv,hashlib,html,json
from pathlib import Path
from animation_page import generate as animation_view
from parts_classification import generate as parts_view
from wheel_interface_report import generate as wheel_view
R=Path(__file__).resolve().parents[1];PROJECT=R.parent
def read(name):return json.loads((R/name).read_text())
def generate():
    p=json.loads((PROJECT/'config/geometry.json').read_text());rev=p['revision'];q=p['assembly_issue_fixes'];source=hashlib.sha256((R/'mori_v1_2.blend').read_bytes()).hexdigest()
    fixes=read('reports/assembly_issue_validation.json');validation=read('reports/validation.json');inserts=read('reports/interface_validation.json');walls=read('reports/interface_printability.json');drivers=read('studies/interface_completion/catalogue_driver_checks.json')
    assert fixes['status']=='PASS' and validation['counts']['FAIL']==0 and inserts['status']=='PASS'
    assert all(d['source_blend_sha256']==source for d in [walls,drivers]) and fixes['source_sha256']==source
    assert drivers['status']=='PASS' and read('reports/delivery_consistency.json')['status']=='PASS'
    assert read('reports/rebuild_check.json')['status']=='PASS'
    animation=animation_view(R);am=read('animation/manifest.json');assert am['source_blend_sha256']==source and am['rendered_video']
    bom=read('reports/bom.json');exports=read('reports/export_manifest.json');previews=read('reports/parts_preview_manifest.json');count=sum(r['candidate_stl'] and r['group'] not in ['dock','coupon'] for r in bom)
    applied=[
        ('1','相机座旧孔腔','填平旧矩形避让槽；保留立柱外轮廓、相机夹持和光学位置。'),
        ('2','俯仰上侧螺母座','螺母移入现有耳座，采用 M2×8 内六角螺钉和短侧入口；螺母贴合承压面；顶壁1.2mm，下方薄边去除，原轴线保持。'),
        ('3','后侧 Yaw 螺母座','保留螺母位置，改成4.2AF槽和短前入口；承压顶壁2.6mm。'),
        ('4','四个轮驱连接螺母','采用候选配套的 DIN934 M2（AF4×1.6）和 M2×8，四处5×1.9mm侧入口；填实旧孔腔，核对装入、止转与承压。'),
        ('5','轮轴承挡边','内轴承各外移0.5mm，挡边增至1.25mm；金属轴肩延长0.5mm，内隔套改为4.5mm。'),
        ('6','机身拼缝和拆装','四组上下壳孔、螺钉和嵌件配对移至X±22/Y±71；孔口作局部导入，螺钉承压台保持。上壳携附件倾斜取出路径已检查。')]
    pending=[
        ('7','BLOCKED','WeAct E 排针/基板孔阵列及后接口 J3 与长焊脚冲突，已交「建立 MORI 硬件开发项目」处理；等待正式板卡交接后复核。'),
        ('SCS0009传动','BLOCKED','按用户选择保留SCS0009；匹配舵盘、花键、短轴及锁紧需厂家资料，继续保留占位与未定型标记。'),
        ('完整线束','NOT_TESTED','按用户要求延后；最终插头、线束弯曲、应力释放及联合运动须在接口确定后检查。'),
        ('实物与强度','NOT_TESTED','CAM/相机照片估计尺寸、SP3040耳厚、电池包与线头、PA12配合/蠕变/冲击、轴同心度和紧固力等需样件。')]
    status=dict(revision=rev,applied_items_1_to_6='PASS',project_digital_release='BLOCKED',manufacturing_release=False,source_blend_sha256=source,applied=[dict(index=a,item=b,status='PASS',detail=c) for a,b,c in applied],pending=[dict(item=a,status=b,detail=c) for a,b,c in pending],hardware_task_id=q['hardware_task_id'],part_count=count,part_count_change=0,physical_measurements='NONE')
    for name in ['interface_completion_status.json','assembly_completion_progress.json']:(R/'reports'/name).write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    build=read('reports/assembly_issue_fixes.json');build.update(status='PASS',validation='assembly_issue_validation.json',source_blend_sha256=source);(R/'reports/assembly_issue_fixes.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
    with (R/'reports/interface_print_review.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['part','sampled_minimum_mm','ray_samples','samples_under_1mm','geometry_source'])
        for row in walls['rows']:w.writerow([row['id'],row['sampled_minimum_mm'],row['samples'],row['under_1mm_samples'],source])
    results={r['id']:r for r in inserts['rows']}
    with (R/'reports/interface_insert_schedule.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['insert','host','catalogue','pilot_diameter_mm','pilot_depth_mm','entry_xyz_mm','min_wall_mm','screw','length_mm','engagement_mm'])
        for r in p['interface_completion']['inserts']:
            t=results[r['id']];w.writerow([r['id'],r['host'],r['sku'],r['pilot_mm'],r['pilot_depth_mm'],r['entry_mm'],t['min_sampled_pilot_wall_mm'],r['screw'],r.get('screw_length_mm','original'),t['nominal_thread_engagement_mm']])
    md=f'''# MORI {rev} · 六项机械问题已应用

已按用户确认将问题1–6应用到主模型，本体候选打印件仍为{count}件，无新增零件。问题7交硬件对话处理。当前状态为 **PROTOTYPE / UNVALIDATED**；六项数字检查PASS不等于整机制造放行。

|编号|已完成|结果|
|---|---|---|
'''+''.join(f'|{a}|{b}|{c}|\n' for a,b,c in applied)+'''
## 上壳拆装顺序

先禁用电机、断开电源并支撑机身。卸下轮毂/轮胎及外隔套、下壳，再卸头部组件和固定Yaw桥。卸四枚框架到上壳的螺钉；工具检查中需要时先取下电池/托盘。断开喇叭和后接口板线束，上壳可携两者一起取下。

以机身中心为参考：上壳绕X倾斜15°并抬升14mm，再向后移14mm，最后上提至140mm。369个离散姿态未检出与保留部件的实体交叠。装入顺序相反，上壳先装，固定桥和头部后装；新版动画已按此顺序排列。线束与人手未纳入这项刚体检查。

## 五金与金属件配套

轮驱四个侧装槽对应DIN934 M2、AF4mm、厚1.6mm的名义目录包络；配M2×8。不能沿用旧的2.4mm厚通用占位螺母。俯仰上耳螺母在原候选槽中向承压面贴合0.15mm，其后经用户确认去除槽下薄边、上缘加厚0.7mm至1.2mm，舵机轴线不变。上耳螺钉采用M2×8 DIN912，与下耳M2×14统一使用1.5mm内六角扳手；原十字螺丝刀刀杆会碰支架。

两只内侧686ZZ中心改为X绝对值38.5mm，外侧仍48mm；轴肩终点36mm，短金属隔套范围41–45.5mm。旧5mm短隔套不适用于此版。STEP、尺寸图和动画使用相同参数。

## 当前验证

'''+f'''主模型记录：{validation['counts']['PASS']} PASS、{validation['counts']['FAIL']} FAIL、{validation['counts']['BLOCKED']} BLOCKED、{validation['counts']['NOT_TESTED']} NOT_TESTED。专项包括：允许变更范围、打印实体闭合、螺母装入/止转/承压、轴承与隔套、上下壳装拆和螺丝刀包络、静态干涉及130个头部姿态。另有73个轮转姿态/侧、轮驱底盖和电机组件拆卸检查。

重复生成两次一致并保留非生成物体；渲染与STL同源；STL回读、PCB详细副本、动画终态和视频回读各有记录。壁厚是有限射线采样，孔口倒角、尖角和功能过渡需按位置分类，不能称为全局最小厚度证明。

源模型SHA256：`{source}`。

- [六项专项](assembly_issue_validation.json) · [整机检查](validation.json)
- [嵌件/孔壁/啮合](interface_validation.json) · [全打印件壁厚采样](interface_printability.json)
- [工具检查](../studies/interface_completion/catalogue_driver_checks.json)
- [生成与检查命令](interface_commands.json) · [壁厚/工具命令](final_seat_audit_commands.json) · [一致性](delivery_consistency.json)
- [金属STEP](wheel_metal_export.json) · [动画](../animation/index.html)

## 明确未完成的内容

'''+''.join(f'- **{a} / {b}**：{c}\n' for a,b,c in pending)+'''

接口7的硬件源文件未在本机械任务中修改，未把正在修改的PCB自动替换进机械模型。硬件正式交接后需重新导入并复核。没有采购、打印或加工下单；PA12试片用于确定孔径补偿、嵌件与螺母配合。
'''
    for name in ['接口复核_M1_43.md','REPORT.md']:(R/'reports'/name).write_text(md)
    (R/'README.md').write_text(f'# MORI {rev}\n\n问题1–6已应用，问题7已交硬件对话。[当前模型](mori_v1_2.blend) · [网页](index.html) · [实际状态](reports/接口复核_M1_43.md) · [装配动画](animation/index.html)。\n\n原型未制造放行，舵盘资料、线束与实物验证仍保留待核。\n')
    (R/'reports/组装与打印.md').write_text('# 当前装配与打印参考\n\n'+md[md.index('## 上壳拆装顺序'):])
    style='<style>*{box-sizing:border-box}body{margin:0;background:#edf1f0;color:#243a33;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1200px;margin:auto;padding:28px 24px 70px}h1{font-size:34px}h2{margin-top:36px}a{color:#146c53}.links,nav{display:flex;gap:18px;flex-wrap:wrap;margin:18px 0}.notice{padding:18px;background:#fff2d8;border:1px solid #dec59d;border-radius:10px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}figure{margin:0;background:white;border:1px solid #ccd8d1;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:12px}td,th{padding:12px;border-bottom:1px solid #ccd6d0;vertical-align:top;text-align:left}table{width:100%;border-collapse:collapse}.PASS{color:#176b49}.BLOCKED{color:#805c19}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:20px 14px}h1{font-size:27px}}</style>'
    def table(rows):return '<table>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'
    def gallery(rows):return '<div class="grid">'+''.join(f'<figure><a href="{f}"><img src="{f}?revision={rev}" alt="{html.escape(t)}"></a><figcaption>{html.escape(t)}</figcaption></figure>' for f,t in rows)+'</div>'
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev}</title>{style}<main><nav><b>MORI {rev}</b><a href="#interface">已完成1–6</a><a href="#remaining">待核事项</a><a href="#structure">结构</a><a href="#animation">动画</a></nav><h1>六项机械问题已应用。</h1><p>{count}件本体候选打印件 · 不新增零件 · 孔槽、五金和轴向堆叠配套更新</p><p class="notice">第7项WeAct E / 后接口J3已交硬件对话。SCS0009舵盘资料、线束和实物验证仍未完成，整机尚未制造放行。</p><div class="links"><a href="mori_v1_2.blend">当前Blender</a><a href="reports/接口复核_M1_43.md">详细报告</a><a href="manufacturing.html">打印件与五金</a><a href="studies/interface_completion/comparisons.html">1–7项对比图</a></div><section id="interface"><h2>已完成1–6</h2>'+table(applied)+'</section><section id="structure"><h2>当前结构</h2>'+gallery([('renders/head_section.png','头部内部：相机立柱、舵机与螺母座'),('renders/internal.png','腹部：框架、板卡和电池'),('renders/exploded.png','同源零件分解展示'),('renders/45_assembled.png','当前总装外观')])+'</section><section id="remaining"><h2>仍需完成</h2>'+table(pending)+'</section>'+animation+f'<section id="checks"><h2>验证记录</h2><p>六项专项PASS；主模型检查{validation["counts"]["PASS"]} PASS / {validation["counts"]["FAIL"]} FAIL。130个头部姿态、369个上壳拆卸姿态、螺母装入及轮驱拆卸均有实际实体采样记录。有限采样不等于实物配合或强度验证。</p><div class="links"><a href="reports/assembly_issue_validation.json">六项专项</a><a href="reports/validation.json">整机状态</a><a href="reports/interface_printability.json">壁厚采样</a><a href="reports/export_manifest.json">STL清单</a><a href="reports/wheel_metal_export.json">金属件STEP清单</a><a href="reports/interface_commands.json">实际命令</a></div></section></main></html>'
    (R/'index.html').write_text(page)
    manufacturing=parts_view(R,rev,bom,previews,exports).replace('当前SP3040用两枚试配M2×6','当前SP3040用两枚M2×5')
    (R/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">返回当前状态</a><p class="notice">零件分类与原型参考；尚未制造放行。旧5mm轮内隔套已由4.5mm替代。</p>'+manufacturing+'</main></html>')
    (R/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">返回当前状态</a><h1>{rev}部件预览</h1>'+gallery([(r['file'],r['id']+' · '+r['name']) for r in previews])+'</main></html>')
    (R/'studies/interface_completion/index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><h1>1–6已应用到{rev}</h1><p><a href="../../index.html#interface">当前总装与证据</a> · <a href="comparisons.html">保留的方案对比</a> · <a href="WEACT_E_HANDOFF.md">7：硬件交接</a></p><p>历史候选保留用于比较，当前尺寸以主模型和统一参数为准。</p></main></html>')
    wheel_view(R)
    print('SIX_FIX_REPORT_PUBLISHED',rev,source,flush=True)
