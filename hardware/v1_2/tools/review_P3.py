#!/usr/bin/env python3
"""Build an offline review page from the checked native KiCad exports."""
from pathlib import Path
import json

H = Path(__file__).resolve().parents[1]
O = H / 'layout_P3'
report = json.loads((O / 'reports/verification.json').read_text())
assert report['native_cad_status'] == 'PASS'
boards = []
for kind, title in [('power', '电源板'), ('motion', '运动载板'), ('imu', '身体 IMU 板')]:
    name = 'MORI_' + kind + '_P3'
    r = report['boards'][name]
    boards.append(dict(kind=kind, name=name, title=title, size=' × '.join(map(str, r['outline_mm'])),
                       copper=70 if kind == 'power' else 35, tracks=r['tracks'], vias=r['vias'],
                       counts=r['counts'], sha=r['input_hashes']['hardware/v1_2/kicad/' + name + '/' + name + '.kicad_pcb']))
html = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI P3 · 三板 Layout</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"PingFang SC",sans-serif;color:#18312e;background:#eef2ef}
*{box-sizing:border-box}body{margin:0}main{max-width:1440px;margin:auto;padding:28px 24px 48px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}h1{font-size:28px;margin:0 0 6px}p{line-height:1.6;margin:8px 0}.muted{color:#53635e;font-size:14px}.badge{border:1px solid #c78743;background:#fff0dc;color:#845224;padding:8px 12px;border-radius:20px;white-space:nowrap;font-size:12px;font-weight:700}
.toolbar{margin:20px 0 12px;background:white;padding:16px;border-radius:12px;display:flex;gap:24px;flex-wrap:wrap;align-items:center}label{font-size:14px}select{font:inherit;padding:8px 12px;border:1px solid #becdc7;border-radius:7px;background:#fff;min-width:140px}fieldset{border:0;margin:0;padding:0;display:flex;gap:14px}legend{font-size:12px;color:#697b73;margin-bottom:6px}input{accent-color:#196950}a{color:#126c53;text-underline-offset:3px}.info{display:flex;gap:16px;flex-wrap:wrap;justify-content:space-between;margin-bottom:12px}.info strong{font-size:19px}.stats{font-size:14px;align-self:center}.canvas{background:#10151c;border-radius:12px;overflow:auto;border:1px solid #243b34;text-align:center}.canvas.assembly{background:white}.canvas img{display:block;width:100%;height:auto;max-height:78vh;object-fit:contain}.links{display:flex;gap:20px;flex-wrap:wrap;margin:16px 0;font-size:14px}.note{background:#fff8eb;border:1px solid #e5d1ae;border-radius:10px;padding:13px 17px;color:#705732;font-size:14px}.hash{overflow-wrap:anywhere;font-size:11px;color:#6e7c77}footer{margin-top:16px;font-size:13px;color:#566960}@media(max-width:650px){main{padding:18px 12px}header{display:block}.badge{display:inline-block;margin-top:10px}.toolbar{gap:18px}h1{font-size:25px}}
</style>
<main>
<header><div><h1>MORI · P3 Layout</h1><p class="muted">三块原生 KiCad 工程 · 2026-09-23 · 电源板 80 × 55 mm</p></div><span class="badge">PROTOTYPE / 未台架验证</span></header>
<div class="toolbar">
<label>板卡<br><select id="board"><option value="0">电源板</option><option value="1">运动载板</option><option value="2">身体 IMU 板</option></select></label>
<fieldset><legend>观察面</legend><label><input type="radio" name="side" value="top" checked> 正面 F</label><label><input type="radio" name="side" value="bottom"> 背面 B（已镜像）</label></fieldset>
<fieldset><legend>图层</legend><label><input type="radio" name="view" value="" checked> 铜线与器件</label><label><input type="radio" name="view" value="_assembly"> 装配图</label></fieldset>
</div>
<div class="info"><strong id="title"></strong><span class="stats" id="stats"></span></div>
<div class="canvas" id="canvas"><img id="image" alt="MORI P3 原生布局导出图"></div>
<nav class="links"><a id="project">KiCad 工程</a><a id="pcb">原生 PCB</a><a id="vector" target="_blank">打开矢量大图</a><a id="drc">DRC 报告</a><a id="placement">装配坐标 CSV</a><a href="../README.md">变更与规则说明</a></nav>
<div class="note">用户布线审查 FAIL：已确认同层线路下穿器件，向外出线要求未落实完整，当前 CAD 尚未修复。ERC/DRC 等为 0 仅代表原生电气检查；不能作为布线方式验收或制造放行。<a href="../body_route_review/README.md">查看问题定位</a></div>
<footer><p>图像直接来自 KiCad 10.0.6 原生导出。背面图已镜像。裸板 STEP 不包含器件和插头，不能证明整机无干涉。</p><p class="hash" id="hash"></p></footer>
</main>
<script>
const boards=__DATA__;
const byId=id=>document.getElementById(id);
function update(){
 const b=boards[Number(byId('board').value)], side=document.querySelector('input[name=side]:checked').value, view=document.querySelector('input[name=view]:checked').value;
 const stem=b.name+'/'+side+view, base='../../kicad/'+b.name+'/'+b.name;
 byId('title').textContent=b.title+' · '+b.size+' mm';
 byId('stats').textContent='ERC 0 · DRC 0 · 未连接 0 · 差异 0  |  2 层 / '+b.copper+' μm';
 byId('image').src=stem+'.png';byId('image').alt=b.title+' '+(side==='top'?'正面':'背面（已镜像）')+' '+(view?'装配图':'铜线及器件');
 byId('canvas').classList.toggle('assembly',Boolean(view));
 byId('project').href=base+'.kicad_pro';byId('pcb').href=base+'.kicad_pcb';
 byId('vector').href=stem+'.svg';byId('drc').href='../reports/'+b.name+'/drc.json';byId('placement').href=b.name+'/placement_native.csv';
 byId('hash').textContent='当前 PCB SHA256: '+b.sha;
}
document.querySelectorAll('select,input').forEach(e=>e.addEventListener('change',update));update();
</script></html>'''
(O / 'previews/index.html').write_text(html.replace('__DATA__', json.dumps(boards, ensure_ascii=False)), encoding='utf-8')
print('P3 offline review page written from checked native exports')
