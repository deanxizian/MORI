"""Current M1.10 report and gallery from actual Blender evidence."""
from pathlib import Path
import json,html,math
from module_report import printing_audit
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text())
esc=html.escape
p=json.loads((PROJECT/'config/geometry.json').read_text());v=load('validation.json');mass=load('mass_budget.json');ex=load('export_manifest.json');bm=load('build_manifest.json');motion=load('head_motion.json');wm=load('wheel_clearance.json');parts=load('parts_preview_manifest.json');consistency=load('delivery_consistency.json');rebuild=load('rebuild_check.json');bom=load('bom.json');structure=load('structure_changes.json');hardware=json.loads((PROJECT/'contracts/components.json').read_text());details=load('detail_fit_validation.json')
checks={c['id']:c for c in v['checks']};whole=mass['totals']['whole_robot'];hp=mass['totals']['head_pitch'];size=checks['assembled_size']['measurement']['xyz_mm']
structure['geometry_status']='FAIL' if v['counts']['FAIL'] else 'BLOCKED';structure['validation_summary']=v['counts'];(ROOT/'reports/structure_changes.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2))
hz=load('derived.json')['head_z'];c=hp['center_mm_rounded'];torque=[{'pitch_deg':a,'gravity_Nm':round(abs((c[1]*math.cos(math.radians(a))-(c[2]-hz)*math.sin(math.radians(a)))/1000*hp['mass_g_rounded']/1000*9.81),4)} for a in range(-20,26,5)]
(ROOT/'reports/head_load_estimate.json').write_text(json.dumps({'status':'ASSUMED','gravity_samples':torque,'sampled_max_Nm':round(max(x['gravity_Nm'] for x in torque),3),'inertia_kg_m2':hp['inertia_at_head_joint_kg_m2'][0][0],'dynamic_equation':'gravity+Ixx*alpha+cable/friction; continuous torque not qualified','mass_uncertainty_percent':35},indent=2))
selection='''# 采购件选型与尺寸依据 · M1.10

用户本轮授权确定型号；以下锁定建模使用的版本。没有执行购买，也没有把原厂数据标成实物测量。硬件主契约components.json保持只读；这些机械选型需由硬件任务接收，不能成为另一份相互矛盾的电气BOM。

| 器件 | 当前建模型号 | 几何依据 | 尚未完成 |
|---|---|---|---|
| 圆屏 | 微雪35079，1.85inch Touch LCD Module | 原厂113实体STEP，1:1；有效显示Ø45.68，玻璃Ø55，CAD厚9.35 | 两连接器网格有缺陷，检查用保守代理；购买版本、排线、CAD/PDF0.25mm厚度差需核 |
| 交互板/相机 | 微雪33700 ESP32-S3-CAM-OV3660 | 原厂板框37×37、孔中心32.6×32.6 | 公开资源仅原理图和图片；没有完整装件STEP。PCB厚1.6、镜筒/FPC包络、USB和麦克风位置仍是ASSUMED，不能做最终孔位 |
| 麦克风 | 33700板上MIC1、MIC2，随板购买 | 本次新增两颗器件实体、声孔及各自声道；位置按37mm原厂正视图估计 | 微雪未给麦克风MPN/封装图/坐标；约±1mm位置不确定，声道不准打印定型。没有追加独立麦克风、ADC或功放 |
| 运动MCU | WeAct STM32F4 64Pin CoreBoard V1.1，STM32F412RET6选项 | 原厂224实体STEP，未缩放；33.22×约41.63×11.99mm完整CAD范围 | 保留所有原始网格。微小装件接触联合网格存在精度问题，检查用全板保守外接实体；运动载板/排母堆叠还未匹配 |
| 扬声器 | Same Sky CMS-4017-34SP，4Ω/3W | 厂图Rev1.02，Ø40×17.5mm，公差±0.3；磁体Ø23，25g；垫圈Ø38.8/36×1.2 | 按图建名义阶梯包络，未标尺寸的篮架锥面保守取外径；焊片局部形状、密封、音量及啸叫待测 |
| 电池几何主选 | Tenergy31013，3S1P 11.1V 2600mAh，成品带保护 | 官方71×55×20mm、150g、连续5A；按原托盘底面放置 | 没有给尺寸公差/导线出口。NTC需另配、均衡未说明、3S USB-C充电仍未匹配，国内含运税价未核。状态为GEOMETRY_CANDIDATE，采购仍BLOCKED |
| 轮驱/头部 | S288×2、SCS0009×2 | 原厂尺寸图的名义外形/安装耳/输出端；四执行器 | 真实舵盘、轴承/轮轴、线口和紧固接口待试配；无输出力矩实测 |
| 自制电源/运动/IMU载板 | 硬件V1.2-H0.3-S3 / P2 | 保留硬件契约，显示明确的安装容量 | S3只有原理图，新电源PCB尚无板框/装件CAD；不能采购一个“微雪电源板”冒名替代它 |
| USB-C与物理开关 | 原有接口/手指/插头预留，已竖排 | 位置确定，未知模块仍橙色 | 精确3S充电模块、开关型号和模块固定孔未确定 |

原厂依据：[微雪33700](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)、[微雪公开硬件资源](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)、[Same Sky尺寸图](https://www.sameskydevices.com/product/resource/cms-4017-34sp.pdf)、[Tenergy31013](https://power.tenergy.com/at-tenergy-li-ion-11-1v-2600mah-rechargeable-battery-pack-w-pcb-3s1p-28-86wh-5a-rate/)。实际下载文件与SHA256在contracts/mechanical_interfaces.json的vendor_geometry_sources中。

Tenergy官方页面列51.99美元且为按单组装；这不是国内报价，也未证明≤1000元整机预算。没有为了套进现有空间改变成品尺寸。GlobTek同容量包的资料亦已核对，但其2.6A连续输出、16–20V内置充电输入与当前目标不直接匹配，所以未选。DNK页面同一料号出现多种包尺寸，未用来冒充唯一精确产品。采购关口：国内渠道、NTC/均衡、充电器和整机峰值/回灌匹配。
'''
assembly=f'''# M1.10 结构、组装与打印

这次保留M1.9横躺轮驱、头内倒装Yaw及降低安装板的方案；只改局部光学、音频、接口和已查到的采购件几何。主体支撑仍为{structure['support_printed_parts_after']}件。

屏幕后完整圆环已删除，换成三个原厂螺柱座的平条叉架，沿用四处侧向短螺钉。相机座是叉架上方的短宽安装舌；最终相机压片/固定方式仍需真实FPC镜头尺寸。原厂LCD螺柱位置不改。

扬声器由身体上壳内侧的环形台阶和两个局部螺丝座定位，用独立后盖压紧；内框架不承载喇叭。原厂1.2mm垫圈提供名义振膜退让，后盖是独立声腔；不能据几何推断音效。两麦在头内交互板，各自声道，不共用喇叭腔。

装配顺序：

1. 托架支撑并禁驱，先装轮轴承和横躺S288，再从下方装共用短底盖、输出连接和轮毂。真实舵盘、轴承保持和轮轴需先试配。
2. 装侧板、滑轨电池托盘、可换软垫、束带及主安装板。电池实际主选71×55×20；80×65×30只作为隐藏空间储备。原有前抽维护顺序仍需拆壳、卸轮/抽轴和断开电池插头。
3. 装电源平托板。S3电源板不是已知实物，禁止按占位盒钻最终PCB孔。WeAct整板CAD已放入后部，排母/载板堆叠还未定型，不可据本图声称板卡可直接固定。
4. 装Yaw承重桥/轴承、转台、可拆固定反力轴，再套上U托并装倒置Yaw。两轴关系和重量承载路径保持M1.9；真实20T舵盘与夹紧强度待测。
5. 先在台面将圆屏装到三个后柱座，再装相机及叉架，侧面四螺钉连接pitch头托；装头内CAM。麦克风声道须实板测量后试打，暂不批准定型。
6. 在独立身体上壳内装扬声器垫圈、喇叭、后盖和两枚M2×6试配螺钉。嵌件座为内侧盲孔，正面不设紧固件孔。连接可断开的两线BTL线束，保留抬壳服务余量，再与框架合壳。维修先断开线束；不是把上壳拉着导线悬挂。
7. 后部开关居上，USB-C居下，中心距17mm。另一个原有圆按钮明确定义功能/停止运动，非RESET；不生成外置重置开关。板上原生BOOT/复位特征是采购CAD本身，不能从实物中删掉。

默认头姿态上仰10°，机械零位仍为0°；限制是绝对pitch−20°～+25°、yaw±60°。不要把10°再加到上限25°上。实际仰头渲染中，头部前下缝仍可见部分关节，遮光和开口接受程度尚未定型。Blender中的CTRL_Pitch可回零进行装配量测，导出始终用装配坐标而非爆炸或默认仰头坐标。

打印建议：外壳先用PLA/PETG外观样件；承重件材料、层向与填充需承载试验。直板/叉架优先宽平面落床，孔与短台阶局部支撑需切片确认。扬声器后盖开口朝上；壳体boss可能需要局部支撑。候选STL不是生产发布，采购件、软轮胎和光学平片不混入STL。热熔嵌件、平缝和夹口先用已有阶梯小样试打，不宣称统一0.3mm可适用所有机器。

尚未通过：全局自交、全壁厚、FDM强度/疲劳、卡线/线束弯曲寿命、真实工具手柄和手指、相机窗口反射、音腔密封和声学、实际板卡堆叠、整机动态平衡。
'''
for n,t in [('采购件选型.md',selection),('purchased_dimensions.md',selection),('组装与打印.md',assembly),('结构简化说明.md',assembly),('设计与选型分工.md',selection),('外购与自制.md',selection+'\n打印件见bom.json和候选STL清单。软轮胎/光学片/紧固件分开采购。\n'),('打印件审查.md',printing_audit(bom))]:(ROOT/'reports'/n).write_text(t)
rows='\n'.join(f"| {c['id']} | {c['status']} | {c['summary']} |" for c in v['checks'])
report=f'''# MORI {p['revision']} · 局部安装与采购件几何

已实际重建Blender并运行验证、渲染、导出。相机镜筒/窗口收进头球轮廓；默认头部仰起10°，圆屏和相机一起转动。扬声器改为身体上壳定位座加可拆压盖，后面圆形结构只承担声腔功能。屏幕后整圈支架换成三点平条叉架。后开关/USB竖排，两颗板载MIC及各自声道已示意。保留功能/停止按钮，未设置外置重置。

采购件按证据分级：LCD和WeAct保留原厂完整CAD，1:1导入；扬声器和成品电池按所选型号的原厂尺寸建名义包络。CAM完整板厚/装件位置、镜头FPC以及USB-C充电模块等仍缺原厂尺寸，不能称“全部精准建模”。[具体选型、来源与缺项](../mechanical/reports/采购件选型.md)。硬件契约{hardware['revision']}未修改；本轮机械选型位于mechanical_interfaces.json，待硬件接收。

零位宽×深×高：{size[0]:.1f}×{size[1]:.1f}×{size[2]:.1f}mm。默认仰头的宽×深×高约：{'×'.join(f'{b-a:.1f}' for a,b in details['default_pose']['bounds_xyz_mm'])}mm。轮径105、轮宽18、腹部离地20mm，轮壳最小实际采样间隙{wm['minimum']['distance_mm']:.2f}mm。原球形意图、两轮接地、四执行器和独立维护托架保留。

头部联合姿态：{motion['poses']}组，yaw−60～60°/10°步长、pitch−20～25°/5°步长，全动作包围尺寸{[round(x,1) for x in motion['size_xyz_mm']]}mm。默认10°属于该绝对范围。±15°身体倾斜只作几何测试。实际三角实体交集用于干涉；AABB只初筛，有限采样不是连续空间证明。LCD两连接器和WeAct细小装件联合网格有精度限制，保守碰撞代理已披露，完整精确适配仍BLOCKED。

估重约{whole['mass_g_rounded']/1000:.2f}kg；估计质心{whole['center_mm_rounded']}mm；pitch运动件约{hp['mass_g_rounded']}g。PLA1.24g/cm³与有效填充、板卡附件假设详见mass_budget.json；新电池150g/喇叭25g采用厂标名义值，其余未实测。至少±35%不确定，不证明头部连续扭矩或平衡稳定。头部惯量/重力矩见head_load_estimate.json；相机外参保留机械零位及默认姿态说明。

实际检查：{v['counts']}。Blender {bm['blender']}，Python {bm['python']}，Manifold {bm['manifold3d']}。可重复重建：{rebuild['status']}，模型/渲染/导出/来源一致性：{consistency['status']}。{ex['exported_count']}件候选STL已重新导入验证毫米尺寸；所有图片来自同一真实几何。

| 检查 | 结果 | 说明 |
|---|---|---|
{rows}

[装配和打印说明](../mechanical/reports/组装与打印.md)。托架支撑时必须禁轮驱；不代表断电自立。未打印、未装实物、未测音频/温升/扭矩/续航/平衡。Tenergy主选的国内成本、NTC、均衡和3S USB-C充电未闭合，整机1000元预算没有通过。S3电源PCB仍待布局。
'''
(PROJECT/'reports/mechanical_v1_2.md').write_text(report)
# Compose current contact sheets from the actual rendered files; never reuse old montages.
from PIL import Image,ImageDraw,ImageFont
import hashlib
font_path='/System/Library/Fonts/Helvetica.ttc'
font=ImageFont.truetype(font_path,24) if Path(font_path).exists() else ImageFont.load_default(size=24)
smallfont=ImageFont.truetype(font_path,14) if Path(font_path).exists() else ImageFont.load_default(size=14)
sheets=[]
for target,folder,row_names,col_names,w in [('structure_comparison.jpg','structure',['whole','belly'],['before','after'],800),('appearance_comparison.jpg','appearance',['before','after'],['front','side','oblique'],600),('v1_2_shape_comparison.jpg','variants',['A','B'],['front','side','45'],480)]:
    sheet=Image.new('RGB',(len(col_names)*w,len(row_names)*(w+35)),'#edf0ed');draw=ImageDraw.Draw(sheet)
    for ri,r in enumerate(row_names):
        for ci,col in enumerate(col_names):
            filename=f'{col}_{r}.png' if folder=='structure' else f'{r}_{col}.png'
            with Image.open(ROOT/'renders'/folder/filename) as im:sheet.paste(im.convert('RGB').resize((w,w)),(ci*w,ri*(w+35)+35))
            label=f'{r} / {col}'
            if folder=='structure':label=(p['structure']['comparison_baseline']['revision'] if col=='before' else p['revision'])+' / '+r
            if folder=='appearance':label=(p['structure']['comparison_baseline']['revision'] if r=='before' else p['revision'])+' / '+col
            draw.text((ci*w+12,ri*(w+35)+4),label,fill='#24343d',font=font)
    sheet.save(ROOT/'renders'/target,quality=94);sheets.append('renders/'+target)
for page_no in range(math.ceil(len(parts)/20)):
    group=parts[page_no*20:(page_no+1)*20];sheet=Image.new('RGB',(1250,50+math.ceil(len(group)/5)*300),'#eeeeea');draw=ImageDraw.Draw(sheet)
    draw.text((20,10),p['revision']+f' | PARTS {page_no+1}',fill='#24343d',font=font)
    for i,part in enumerate(group):
        x=i%5*250;y=i//5*300+50
        with Image.open(ROOT/part['file']) as im:sheet.paste(im.convert('RGB').resize((245,245)),(x,y))
        draw.text((x+5,y+248),part['id'][:24],fill='#24343d',font=smallfont)
    path=f'renders/parts_sheet_{page_no+1:02}.jpg';sheet.save(ROOT/path,quality=92);sheets.append(path)
(ROOT/'reports/presentation_manifest.json').write_text(json.dumps({'revision':p['revision'],'files':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sheets}},indent=2))
# Keep the browser report concise; data files retain the engineering detail.
view_names={'weact_detail':'WeAct V1.1 原厂224实体CAD','45_assembled':'默认仰头10°','front':'前视','side':'侧视','rear':'后视 · 开关在USB上方','top':'顶视','bottom':'底视','face_detail':'相机收进球壳轮廓','screen_outline_review':'三柱平条叉架 · 无完整圆环','speaker_shell_detail':'扬声器压盖及壳体固定接口','mic_detail':'头内两颗MIC及独立声道 · 位置待测','internal':'内部布局','head_section':'头部双轴剖视','belly_detail':'电池与板卡空间','yaw_drive_detail':'头内Yaw与固定反力轴','exploded':'总装爆炸图','structure_only':'简单支撑件','structure_exploded':'结构拆解','clearance':'腹部离地/轮壳间隙','pose_up':'联合姿态：仰头','pose_down':'联合姿态：低头','docked':'独立维护托架','balance_side':'质量假设与质心','head_support':'头托','deck_detail':'主板区','wheel_gap_detail':'轮壳局部间隙'}
def card(name):return f'<figure><a href="renders/{name}.png"><img loading="lazy" src="renders/{name}.png" alt="{esc(view_names.get(name,name))}"></a><figcaption>{esc(view_names.get(name,name))}</figcaption></figure>'
appearance=''.join(card(n) for n in ['45_assembled','face_detail','front','side','rear','top','bottom'])
structure_cards=''.join(card(n) for n in ['screen_outline_review','speaker_shell_detail','mic_detail','weact_detail','internal','head_section','belly_detail','yaw_drive_detail','exploded','structure_only','structure_exploded','clearance','pose_up','pose_down','docked'])
partcards=''.join(f'<figure class="part"><a href="{esc(a["file"])}"><img loading="lazy" src="{esc(a["file"])}"></a><figcaption>{esc(a.get("label",a.get("name",a["id"])))}<br><small>{esc(a["id"])}</small></figcaption></figure>' for a in parts)
statusrows=''.join(f'<tr><td>{esc(a["id"])}</td><td class="{a["status"]}">{a["status"]}</td><td>{esc(a["summary"])}</td></tr>' for a in v['checks'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {p['revision']}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#11151a;color:#e3e8ed;font:16px/1.7 system-ui,sans-serif}}main{{max-width:1300px;margin:auto;padding:32px}}h1{{font-size:36px;margin:0}}h2{{margin-top:56px}}p{{max-width:1000px;color:#bfcbd4}}a{{color:#85dce8}}nav{{position:sticky;top:0;padding:12px;background:#11151af2;display:flex;gap:24px;flex-wrap:wrap;border-bottom:1px solid #33404c}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}}.parts{{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}}figure{{margin:0;background:#242b33;border-radius:12px;overflow:hidden}}img{{width:100%;display:block}}figcaption{{padding:12px}}small{{color:#a6b4bf}}.note{{padding:20px;background:#25333d;border-radius:12px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #33404c}}.PASS{{color:#8de0ae}}.FAIL{{color:#ff7777}}.BLOCKED,.NOT_TESTED{{color:#efbf7c}}.links{{display:flex;flex-wrap:wrap;gap:20px;margin:20px 0}}code{{color:#9fe2da}}@media(max-width:600px){{main{{padding:18px}}}}
</style><main><h1>MORI <small>{p['revision']}</small></h1><p>相机内收 · 默认仰头10° · 喇叭固定到身体外壳 · 三点屏幕叉架 · 采购件按来源建模</p><nav><a href="#appearance">外观</a><a href="#structure">结构</a><a href="#procurement">采购件</a><a href="#parts">全部零件</a><a href="#checks">检查</a></nav><div class="links"><a href="mori_v1_2.blend">打开/下载Blender模型</a><a href="../reports/mechanical_v1_2.md">完整报告</a><a href="reports/采购件选型.md">型号与真实尺寸依据</a><a href="reports/组装与打印.md">组装与打印</a><a href="reports/export_manifest.json">候选STL清单</a></div>
<div class="note">已实际生成、检查与渲染。<b>{v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL</b>；其余未测/阻塞见下表。原厂CAD不等于实物测量。橙色是资料未全或待选的预留，电池/充电与S3电源PCB仍未达到采购/制造放行条件。</div>
<section id="appearance"><h2>默认姿态与外形</h2><p>机械零位保持屏幕在头部正前中心；保存的默认姿态上仰10°。摄像头和屏幕同属pitch组件。轮胎和双轴方案延续M1.9。只有功能/停止键，没有外置RESET。</p><div class="grid">{appearance}</div></section>
<section id="structure"><h2>本次局部结构</h2><p>屏幕后完整圆环改为三柱平条叉架。喇叭定位座连在上壳内侧，后盖由两枚短螺钉固定，音腔不接内框架。MIC1/MIC2是微雪板载件，声道和封装位置仍需实板核对。</p><div class="grid">{structure_cards}</div></section>
<section id="procurement"><h2>已选型号与精度边界</h2><table><tr><th>器件</th><th>模型依据</th><th>状态</th></tr><tr><td>LCD35079</td><td>原厂113实体STEP，1:1</td><td>版本/排线待核</td></tr><tr><td>WeAct F412RET6 V1.1</td><td>原厂224实体STEP，1:1</td><td>载板/排母堆叠未适配</td></tr><tr><td>CMS-4017-34SP</td><td>Ø40×17.5mm，±0.3mm</td><td>已选几何；声学/焊线待测</td></tr><tr><td>Tenergy31013</td><td>71×55×20mm，2600mAh，150g</td><td>几何主选；采购仍阻塞</td></tr><tr><td>微雪33700 / 两颗MIC</td><td>37×37板框已核；装件位置为照片示意</td><td>不能声称全板精准适配</td></tr><tr><td>3S充电 / S3电源板</td><td>明确空间预留</td><td>精确模块选型/PCB待完成</td></tr></table><p><a href="reports/采购件选型.md">查看原厂链接、缺失尺寸和采购条件</a>。采购件未混入外壳STL；通用轮胎、光学片、轴承和紧固件另列。</p></section>
<section id="parts"><h2>全部零件 · {len(parts)}项</h2><p><a href="reports/bom.csv">部件表CSV</a> · <a href="reports/打印件审查.md">打印件审核</a> · {ex['exported_count']}件候选STL，已回读核对毫米单位。</p><div class="grid parts">{partcards}</div></section>
<section id="checks"><h2>实际验证记录</h2><p>Blender {bm['blender']}。重建{rebuild['status']}，输入/渲染/STL一致性{consistency['status']}。130组头部离散姿态；有限采样不证明连续空间。估重约{whole['mass_g_rounded']/1000:.2f}kg，质心假设{whole['center_mm_rounded']}mm，至少±35%不确定，未实机验证平衡。</p><table>{statusrows}</table></section></main></html>'''
(ROOT/'index.html').write_text(page)
print('REPORT_COMPLETE',p['revision'])
