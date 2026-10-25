"""Publish accepted pre-arrival decisions without hiding remaining design gaps."""
import json,html
from pathlib import Path

def rows_update(rows):
    rows=list(rows)
    rows.insert(0,('PA12与局部试片','材料已确定；未下单','首轮全部打印件PA12。7件独立配合试片、孔位图和空白测量记录已生成；试片及整机均未采购或打印。'))
    rows.insert(1,('舵机耳座','名义设计/检查完成','4处旧嵌件改M2穿栓＋金属螺母；孔位不动，3处内螺母窝、1处贯穿长螺钉。先在脱离机身的U托上预装螺母；打印件数和紧固件总数不增加。'))
    rows.insert(2,('相机扩口','名义设计/检查完成','采用用户确认的连续椭圆扩口，镜头、夹持与LCD位置不动。775条假设视线通过，未切黑色边圈；正视连续白壳带约1.3mm，配合和强度待实测。'))
    rows.insert(3,('IMU固定','保留原两孔','用户撤回扩板与第三固定点，继续20×16mm原板和现有两个安装孔；没有新增短座、螺钉或嵌件。三点支承建议不作为本版待改板项。'))
    rows.insert(4,('其余嵌件座','仍需设计定型','已按厂家参考尺寸筛查；多处旧小嵌件座容不下常见M2嵌件所需包边。不能把候选嵌件直接填进旧孔，也不能将此项归为只等实物。'))
    return rows

def publish(root,rev,current_report):
    load=lambda n:json.loads((root/'reports'/n).read_text())
    pv=load('prearrival_validation.json');v=load('validation.json');hm=load('head_motion.json');ex=load('export_manifest.json');bom=load('bom.json');mass=load('mass_budget.json')
    assert pv['status']=='PASS' and not v['counts']['FAIL']
    robot=[x for x in bom if x['candidate_stl'] and x['group'] not in ['dock','coupon']]
    fast=[x for x in bom if any(k in x['id'] for k in ['Screw','Nut','Insert','Washer']) and not x['id'].startswith('Coupon')]
    types={k:sum(k in x['id'] for x in fast) for k in ['Screw','Nut','Insert','Washer']}
    intro=f'''# MORI {rev} · 打样前接口整理

已应用用户确认的PA12材料、4处舵机穿栓螺母和连续椭圆相机扩口。IMU保留原20×16mm及两个孔；扩板方案已撤回。机器人打印件仍为{len(robot)}件，紧固件对象{len(fast)}个（螺钉{types['Screw']}、螺母{types['Nut']}、嵌件{types['Insert']}、垫圈{types['Washer']}）。这些数量不是已放行的采购清单。

四组耳座孔位、舵机及全部PCB位置保持。M2×6、M2×25、两枚M2×14配4枚M2螺母；三处内沉槽、一处长柱贯穿。螺母在U托脱离机身时预装，再落入Yaw轴承，随后安装舵机。名义承压环、12mm螺母装入路径与静态间隙已检查，未验证PA12强度或实际拧紧力。

相机孔与批准图片保持同一连续椭圆轮廓。775条名义视线通过，黑色屏幕边圈无切除；正视白壳带约1.3mm，替代此前3mm外观目标。真实视角、孔边强度及夹持公差仍待样件。没有新增走线孔。

主模型检查：{v['counts']['PASS']} PASS、{v['counts']['FAIL']} FAIL；头部{hm['poses']}个名义联合姿态未检出穿插。全硬件资格仍受简化螺纹、未定舵盘等项目限制。有限姿态不是连续运动证明。

当前总装、STL、预览及装配动画使用同一版几何。机器人15件候选打印件以毫米导出；独立维护座、旧试片与新7件PA12局部试片分开。重复生成及保留非生成对象检查通过。实际命令、版本和日志见[prearrival_commands.json](prearrival_commands.json)，本轮专项见[prearrival_validation.json](prearrival_validation.json)。

## 仍可在实物到货前推进

- 头部舵盘与双侧短轴：当前传动连接及轴向保持未闭合。已找到微雪SC09官方舵盘CAD，但与SCS0009配套关系未确认；不能直接把短轴补长或把不同舵机资料混用。
- 其余M2嵌件：确定可购买规格后，逐处完成必要座面调整；现有多处小试配座不能直接安装常见FINE候选。
- WeAct排母及对插：原6mm堆叠仅为假设。29处插头包络已筛查，后接口J3与核心板尚有约0.0184mm³保守包络重叠，需要详细接口定型。
- 充电、断电/物理急停等电气接口依赖电路任务明确；机械不能虚构所需器件及热边界。
- 线束按用户要求延后，待安装和连接器确定后再设计有限服务环、应力释放与弯曲。

## 已为实物验证准备

全部打印件选择PA12；质量估算采用完整建模体积与参考密度1.01g/cm³，不套用FDM填充率。密度不是嘉立创批次实测值。已生成[7件配合试片](../studies/prearrival_preparation/jlc_coupons/index.html)、毫米STL、孔位索引和空白测量表；孔径/嵌件/轴承与螺母窝需同批次实测。

实物仍需核对采购件尺寸、公差、镜头视场、装入拆出、夹紧力、振动、热、线束和动态平衡。未下单、未上传制造文件、未做整机制造放行；不是“只剩实物验证”。
'''
    (root/'reports'/current_report).write_text(intro)
    (root/'reports/REPORT.md').write_text(intro)
    assembly=(root/'reports/组装与打印.md').read_text().replace('安装头部承重轴承及两轴舵机。','在脱离机身的Pitch_Yoke内先放入4枚M2金属螺母，再装Yaw承重组件和两轴舵机。耳座用M2×6、M2×25和两枚M2×14，取消该4处嵌件。')
    (root/'reports/组装与打印.md').write_text(assembly)
    page=(root/'index.html').read_text()
    page=page.replace('头壳与屏幕补齐紧固，<br>减少独立光学件。','舵机改穿栓螺母，<br>相机采用连续椭圆扩口。')
    section='<section id="prearrival"><h2>当前打样前整理</h2><p>首轮全部PA12；4处舵机耳座改穿栓螺母，无新增打印件。IMU保留原20×16mm及两个孔，扩板提案已撤回。</p><p>相机镜头与夹持位置不动；775条名义视线通过，保留黑色屏幕边圈。完整舵盘传动、其余嵌件座与排母等接口仍有设计工作。</p><div class="links"><a href="reports/prearrival_validation.json">本轮几何检查</a><a href="studies/prearrival_preparation/index.html">打样前接口检查</a><a href="studies/prearrival_preparation/jlc_coupons/index.html">7件PA12配合试片</a></div></section>'
    page=page.replace('<section id="readiness">',section+'<section id="readiness">')
    (root/'index.html').write_text(page)
    (root/'reports/prearrival_delivery_summary.json').write_text(json.dumps({'revision':rev,'scope_validation':pv['status'],'robot_prints':len(robot),'fastener_objects':len(fast),'fastener_types':types,'IMU':'20x16 original two holes; third-point proposal withdrawn','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
