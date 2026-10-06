"""Publish the executed head-print comparison, using actual Blender renders."""
from pathlib import Path
import json,html


def generate(root):
    p=json.loads((root.parent/'config/geometry.json').read_text())
    if not p.get('head_print_cleanup',{}).get('enabled'):return ''
    r=json.loads((root/'reports/head_cleanup_validation.json').read_text())
    v=json.loads((root/'reports/validation.json').read_text())
    motion=json.loads((root/'reports/head_motion.json').read_text())
    rev=p['revision'];dest=root/'studies/head_cleanup'
    details=[('cradle','等厚直角 U 形头托','取消轴孔两侧贴片凸台和后方切角；整个 U 形壁统一为 4.5 mm，后壁从 Y=-34 前移至 -29.5 mm，让直角轮廓留在球壳内。两侧轴孔、前壳固定孔和屏幕侧接孔保持原位。轴孔处原局部厚 5 mm，现为连续 4.5 mm 壁；几何简化不代表承载强度已验证。'),
             ('fork','等宽立柱与直角屏幕叉架','立柱原来 7/14/16 mm 的宽度台阶改为连续 16 mm；两侧搭接的外侧斜切改为直角。三个原厂 LCD 接触垫、相机容纳槽和内侧装螺母的空间有安装用途，仍保留。四枚原有螺母随头托壁内移 1.3 mm，孔后名义承压壁仍为 2 mm，原有螺钉、LCD 和相机位置不变。'),
             ('yoke','双轴内部 U 托 · 保留必要避让','沿用上一版连续底座。本次实际试填平底部两角后，中位就与前后球壳各产生约 118 mm³ 穿插，-20° 至 +25° 的 5° 采样同样有冲突，因此保留这一避让斜面。轴承台肩、舵机座、走线通道和 LCD 倾斜接触垫有明确装配用途。')]
    sections=[]
    for key,title,note in details:
        sections.append(f'<section><h2>{title}</h2><p>{note}</p><div class="grid"><figure><img src="before_{key}.png?revision={rev}"><figcaption>修改前 · M1.24</figcaption></figure><figure><img src="after_{key}.png?revision={rev}"><figcaption>当前 · M1.25</figcaption></figure></div></section>')
    before=sum(x['volume_mm3'] for x in r['before'].values());after=sum(x['volume_mm3'] for x in r['after'].values())
    delta=(after/before-1)*100
    rows=''.join(f'<tr><td>{html.escape(n)}</td><td>{r["before"][n]["volume_mm3"]/1000:.1f}</td><td>{r["after"][n]["volume_mm3"]/1000:.1f}</td></tr>' for n in r['reviewed_prints'])
    change='总材料体积基本不变' if abs(delta)<1 else f'总材料体积变化{delta:+.1f}%'
    note=f'M1.25已修改头托、屏幕相机叉架，检查双轴 U 托；仍是三个打印件，没有增加紧固件。{change}，合计约 {after/1000:.1f} cm³；这是几何体积，不是称重结果。'
    checks=f'当前专项结果 {r["status"]}；全局检查 {v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL。头部联合 {motion["poses"]} 个姿态有限采样；完整实物器件、连续运动、打印强度和装配公差仍未验证。'
    caveat='CAM 的完整装件及最终固定仍缺实物资料；不能把旧声道孔当作板卡螺孔。屏幕侧孔、轴承孔和舵机固定孔属于必要接口，没有直接封死。'
    pending=json.loads((root.parent/'contracts/mechanical_interfaces.json').read_text()).get('pending_hardware_receipt')
    if pending and pending['status']=='BLOCKED':
        caveat+=' 当前装配仍采用已接入的 P5R2 电路板；硬件任务另有 P5R4 更新，完整装件模型与配合尚待同步，本次不代表新版 PCB 已适配。'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 80px}h1{font-size:34px}h2{margin-top:45px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}td,th{padding:10px 18px;border-bottom:1px solid #cbd4cc}table{border-collapse:collapse}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 头部打印件简化</title><style>{style}</style><main><a href="../../index.html#head-cleanup">← 总装</a><h1>去掉多余台阶与切角。</h1><p>{note}</p><p><a href="../../mori_v1_2.blend">打开总装 Blender</a> · <a href="../../mori_assembly_animation.blend">装配动画 Blender</a> · <a href="../../animation/index.html">播放装配动画</a></p><div class="notice">{caveat}</div><figure><img src="after_head.png?revision={rev}"><figcaption>同一套实际几何 · 去壳头部</figcaption></figure>'+''.join(sections)+f'<h2>检查与边界</h2><p>{checks}</p><p>螺母从叉架内侧预装，孔后承压材料已检查；俯仰轴、所有现有电子器件和光学组件保持原位。整机候选打印件仍为 15 件。先试打配合小样，不宣称已能承受跌落或长期载荷。</p><table><tr><th>打印件</th><th>修改前 cm³</th><th>修改后 cm³</th></tr>{rows}</table><p><a href="../../reports/head_cleanup_validation.json">专项检查数据</a> · <a href="../../reports/validation.json">全部检查</a> · <a href="../../reports/retained_head_interfaces.json">底部切角试填平结果</a> · <a href="../../reports/head_cleanup_commands.json">实际命令</a></p></main></html>'
    (dest/'index.html').write_text(page)
    md=f'# 头部主要打印件简化 · {rev}\n\n{note}\n\n'+''.join(f'## {title}\n\n{text}\n\n' for _,title,text in details)+f'{checks}\n\n{caveat}\n\n左右四枚 M2 螺钉仍可拆；六角螺母先从叉架内侧装入，随后对接头托。完整相机/FPC/CAM固定、FDM孔配合、强度和疲劳仍为待验证。\n\n[实际渲染对比](../studies/head_cleanup/index.html)\n'
    (root/'reports/头部打印件简化.md').write_text(md)
    return f'<section id="head-cleanup"><h2>头部主要打印件已简化</h2><p>{note}</p><p>头托改为等厚直角 U 形壁；屏幕支架两侧去掉外侧斜切；相机立柱改成连续等宽。必要的光学接触垫、轴承台肩及安装孔保留。</p><div class="links"><a href="studies/head_cleanup/index.html">查看三个大件修改前后</a><a href="reports/头部打印件简化.md">用途与检查</a></div><a class="card" href="studies/head_cleanup/index.html"><img style="width:100%;max-width:880px" src="studies/head_cleanup/after_head.png?revision={rev}" alt="M1.25 实际头部支架渲染"></a></section>'
