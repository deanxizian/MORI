"""Publish verified drawing interfaces, simple seats and deferred routing."""
import json


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text());s=p.get('head_servo_detail',{})
    if not s.get('enabled'):return ''
    r=json.loads((root/'reports/head_servo_validation.json').read_text())
    motion=json.loads((root/'reports/head_motion.json').read_text())
    static=json.loads((root/'reports/static_interference.json').read_text())
    v=json.loads((root/'reports/validation.json').read_text());rev=p['revision']
    summary='两只SCS0009按厂家尺寸图重建：修复安装耳悬空，纠正耳座高度，补齐输出端。固定支架改为连续底面和简单耳座，撤掉预估走线孔、斜切和线夹。'
    interface='安装耳总跨度32.5 mm，孔距28.5 mm，两个Ø2 mm孔；安装耳从壳底16.8 mm到18.4 mm，厚1.6 mm。输出端按20T、外径3.95 mm、伸出3.2 mm定位。'
    precision='依据FEETECH SCS0009 A/0规格书第4、6页重建，未找到原厂STEP，也没有实物测量。第4页表格长度23.2 mm与第6页尺寸图23.3 mm存在差异，本模型采用图纸23.3 mm；壳宽12.1 mm，含齿轮顶盖高25.25 mm，含输出端总高28.45 mm。'
    assumptions='壳体倒圆、盖缝、未标尺寸的齿轮凸包及花键齿根仅作外形示意；20T不等于已还原可加工齿形。Yaw_Horn和Pitch_Horn仍是占位舵盘，需确认随购舵盘、啮合深度、锁紧螺钉与机械零位后再冻结传动接口。'
    mounting='Yaw舵机仍倒置、输出向下；Pitch壳体绕原输出轴翻转180°，长端向下，让两个安装耳都落在左侧支架的两个固定面上。两轴输出端坐标与轴线保持原位。两只舵机各用两枚M2×5螺钉锁入一体耳座内的试配嵌件；螺钉和嵌件是五金，不是打印件。俯仰两侧轴承与Yaw承重轴承继续承担头部载荷。'
    assembly='先在空U托上装四枚试配嵌件；Pitch舵机从中央空位沿−X装入，锁紧两个耳孔；随后由上方装倒置Yaw舵机并锁紧。最后装头托、光学件和头壳。Pitch拆出按+X方向，需先拆光学/俯仰头总成和Yaw舵机。插入路径按1 mm采样35 mm，四处按Ø4.2 mm、长30 mm直柄工具检查；这些采样不覆盖手柄、热熔工具和连续空间全部状态。'
    routing='走线按用户要求延后：旧线束示意移入隐藏构造集合，头部预估线孔、斜向扫掠槽和C形线夹撤掉。支架保留的中心通道用于Yaw反力轴，两侧大孔用于俯仰轴承，四个小孔用于舵机耳固定。现有身体接口不在本次重设计范围内。线束、服务环、应力释放和动态弯折明确为NOT_TESTED。'
    checks=f'小舵机专项 {r["status"]}：两只壳体各为一个连续实体；耳孔孔径、耳厚、耳面高度、四处座面材料和装配工具已核对。与M1.29逐件比较，只有声明的舵机、输出端、U托、显示支架及相关五金变化，其他部件网格与装配矩阵一致。静态模型穿插{len(static["failed_pairs"])}项；头部{motion["poses"]}个联合姿态的刚性模型穿插{len(motion["failures"])}项（Yaw 10°、Pitch 5°步长）。整机仍有缺资料的LCD接插件代理，因此不称完整实物装配通过。'
    limit='未进行打印、嵌件抗拔、预紧、疲劳、持续载荷或实机平衡试验。M2嵌件的外径/长度、导孔和螺钉长度均为试配候选，必须用所购物料做小样。模型与动画保持传动占位状态，不作为已验证的装机工艺。'
    if p.get('head_mount_simplification',{}).get('enabled'):
        checks=checks.replace('只有声明的舵机、输出端、U托、显示支架及相关五金变化，其他部件网格与装配矩阵一致。','累计修改仅限已声明部件；M1.33微雪器件与M1.34头壳配对孔/平齐舵机座分别通过专项范围核对。')
    title='小舵机与固定座已重建'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 70px}h1{font-size:34px}h2{margin-top:36px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:#fff;border-radius:12px;overflow:hidden}img{display:block;width:100%}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}td,th{padding:10px;border-bottom:1px solid #ccd}table{border-collapse:collapse;width:100%}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    def fig(key,label):return f'<figure><a href="{key}.png"><img src="{key}.png?revision={rev}" alt="{label}"></a><figcaption>{label}</figcaption></figure>'
    comparisons='<h2>安装耳真正连接到壳体</h2><div class="grid">'+fig('before_servo','M1.29 · 旧简化模型，安装耳断开')+fig('after_servo',rev+' · 连续壳体、耳孔与输出端')+'</div>'
    comparisons+='<h2>实际孔位与包络</h2><p>'+precision+'</p><p>'+interface+'</p><div class="grid">'+fig('after_servo_top','输出端正视 · 孔距28.5 mm')+fig('after_servo_side','侧视 · 耳底16.8 / 耳顶18.4 mm')+'</div>'
    comparisons+='<h2>简化舵机固定支架</h2><div class="grid">'+fig('before_yoke','M1.29 · 旧线孔、夹子和叠加的耳座')+fig('after_yoke',rev+' · 连续底面、简单固定座')+'</div><p>'+routing+'</p>'
    comparisons+='<h2>两只舵机的实际安装方向</h2><p>'+mounting+'</p><div class="grid">'+fig('after_mounted','同一套模型 · 两只舵机装入U托')+fig('after_pitch_seats','俯仰耳座与螺钉 · 先卸Yaw，从中央侧操作')+'</div><p>'+assembly+'</p>'+fig('after_head','当前去壳头部 · 无预估线束')
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 小舵机与固定座</title><style>{style}</style><main><a href="../../index.html#head-servos">← 当前总装</a><h1>{title}</h1><p>{summary}</p><p><a href="../../mori_v1_2.blend">总装 Blender</a> · <a href="../../animation/index.html?revision={rev}">装配动画版本说明</a> · <a href="../../mori_assembly_animation.blend">动画 Blender</a></p>{comparisons}<h2>检查结果与待确认项</h2><p>{checks}</p><div class="notice"><p>{assumptions}</p><p>{limit}</p></div><p><a href="../../sources/v1_2/scs0009_spec.pdf">厂家规格书</a> · <a href="../../reports/head_servo_validation.json">专项检查</a> · <a href="../../reports/head_servo_commands.json">执行命令</a> · <a href="after_render_manifest.json">渲染来源</a></p></main></html>'
    (root/'studies/head_servo_detail/index.html').write_text(page)
    doc=f'# SCS0009模型与固定座 · {rev}\n\n'+ '\n\n'.join([summary,precision,interface,mounting,assembly,routing,checks,assumptions,limit])+'\n\n[模型实际渲染](../studies/head_servo_detail/index.html) · [厂家尺寸图](../sources/v1_2/scs0009_spec.pdf) · [专项检查](head_servo_validation.json)\n'
    (root/'reports/小舵机与固定座.md').write_text(doc)
    for path in [root/'README.md',root/'reports/REPORT.md']:
        old=path.read_text();first,rest=old.split('\n',1);link='小舵机与固定座.md' if path.parent.name=='reports' else 'reports/小舵机与固定座.md'
        path.write_text(first+f'\n\n{summary} [本轮修改与精度范围]({link})\n\n走线已延后；舵盘配合和打印强度未验证。\n'+rest)
    return f'<section id="head-servos"><h2>{title}</h2><p>{summary}</p><p>{interface}</p><div class="links"><a href="studies/head_servo_detail/index.html?revision={rev}">模型与固定方式</a><a href="reports/小舵机与固定座.md">来源与检查</a></div><div class="grid"><a class="card" href="studies/head_servo_detail/index.html"><img src="studies/head_servo_detail/after_servo.png?revision={rev}" alt="连续小舵机壳体与安装耳"></a><a class="card" href="studies/head_servo_detail/index.html"><img src="studies/head_servo_detail/after_mounted.png?revision={rev}" alt="两只小舵机实际装入"></a></div><p>{assumptions}</p></section>'
