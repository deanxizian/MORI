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
    details=[('cradle','低背头托','后方四孔是两代声道开口；已取消导管，现在改为整个顶部开放。两侧俯仰轴孔、前壳固定孔及屏幕侧接孔保留。'),
             ('fork','屏幕与相机叉架','清除旧侧耳、叠块及竖向凹槽，改成一次挤出的短搭接。三个原厂 LCD 安装点、独立相机位置和 10° 光学倾角保持。左右各两枚螺钉用于限制叉架转动；四枚原有螺母内移 1.3 mm，孔后承压塑料从约 0.7 增至 2 mm。'),
             ('yoke','双轴内部 U 托','旧转台和 U 托已合并，原来的分层接合轮廓改为连续斜面底座。两侧轴承孔、反力轴通道、舵机安装位、走线通道和薄遮光边仍有实际作用。')]
    sections=[]
    for key,title,note in details:
        sections.append(f'<section><h2>{title}</h2><p>{note}</p><div class="grid"><figure><img src="before_{key}.png?revision={rev}"><figcaption>修改前 · M1.23</figcaption></figure><figure><img src="after_{key}.png?revision={rev}"><figcaption>修改后 · M1.24</figcaption></figure></div></section>')
    before=sum(x['volume_mm3'] for x in r['before'].values());after=sum(x['volume_mm3'] for x in r['after'].values())
    delta=(after/before-1)*100
    rows=''.join(f'<tr><td>{html.escape(n)}</td><td>{r["before"][n]["volume_mm3"]/1000:.1f}</td><td>{r["after"][n]["volume_mm3"]/1000:.1f}</td></tr>' for n in r['changed_prints'])
    change='总材料体积基本不变' if abs(delta)<1 else f'总材料体积变化{delta:+.1f}%'
    note=f'三个主要支架仍是三个打印件，本次没有增加紧固件。{change}，合计约 {after/1000:.1f} cm³；这是几何体积，不是称重结果。'
    checks=f'当前专项结果 {r["status"]}；全局检查 {v["counts"]["PASS"]} PASS / {v["counts"]["FAIL"]} FAIL。头部联合 {motion["poses"]} 个姿态有限采样；完整实物器件、连续运动、打印强度和装配公差仍未验证。'
    caveat='CAM 的完整装件及最终固定仍缺实物资料；不能把旧声道孔当作板卡螺孔。屏幕侧孔、轴承孔和舵机固定孔属于必要接口，没有直接封死。'
    style='*{box-sizing:border-box}body{margin:0;background:#eef0ed;color:#233432;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 80px}h1{font-size:34px}h2{margin-top:45px}a{color:#216556}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white;border-radius:12px;overflow:hidden}img{width:100%;display:block}figcaption{padding:12px 18px}.notice{padding:18px;background:#fff4d9;border-radius:10px}td,th{padding:10px 18px;border-bottom:1px solid #cbd4cc}table{border-collapse:collapse}@media(max-width:700px){.grid{grid-template-columns:1fr}}'
    page=f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 头部打印件简化</title><style>{style}</style><main><a href="../../index.html#head-cleanup">← 总装</a><h1>头部打印件，清理旧孔与叠层。</h1><p>{note}</p><p><a href="../../mori_v1_2.blend">打开总装 Blender</a> · <a href="../../mori_assembly_animation.blend">装配动画 Blender</a> · <a href="../../animation/index.html">播放装配动画</a></p><div class="notice">{caveat}</div><figure><img src="after_head.png?revision={rev}"><figcaption>同一套实际几何 · 去壳头部</figcaption></figure>'+''.join(sections)+f'<h2>检查与边界</h2><p>{checks}</p><p>螺母从叉架内侧预装，孔后承压材料已检查；俯仰轴、所有现有电子器件和光学组件保持原位。整机候选打印件仍为 15 件。先试打配合小样，不宣称已能承受跌落或长期载荷。</p><table><tr><th>打印件</th><th>修改前 cm³</th><th>修改后 cm³</th></tr>{rows}</table><p><a href="../../reports/head_cleanup_validation.json">专项检查数据</a> · <a href="../../reports/validation.json">全部检查</a> · <a href="../../reports/head_cleanup_commands.json">实际命令</a></p></main></html>'
    (dest/'index.html').write_text(page)
    md=f'# 头部主要打印件简化 · {rev}\n\n{note}\n\n'+''.join(f'## {title}\n\n{text}\n\n' for _,title,text in details)+f'{checks}\n\n{caveat}\n\n左右四枚 M2 螺钉仍可拆；六角螺母先从叉架内侧装入，随后对接头托。完整相机/FPC/CAM固定、FDM孔配合、强度和疲劳仍为待验证。\n\n[实际渲染对比](../studies/head_cleanup/index.html)\n'
    (root/'reports/头部打印件简化.md').write_text(md)
    return f'<section id="head-cleanup"><h2>头部主要打印件已简化</h2><p>{note}</p><p>取消后托的四个旧声道孔和高耳；屏幕叉架清理竖槽与叠块；转台下方改为连续底座。必要轴承、安装和走线接口保留。</p><div class="links"><a href="studies/head_cleanup/index.html">查看三个大件修改前后</a><a href="reports/头部打印件简化.md">用途与检查</a></div><a class="card" href="studies/head_cleanup/index.html"><img style="width:100%;max-width:880px" src="studies/head_cleanup/after_head.png?revision={rev}" alt="M1.24 实际头部支架渲染"></a></section>'
