"""Publish the bounded complete-wire PH entry result and its remaining work."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,platform

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'PH_guided_wire_entry';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={}


def receive(path,script):
    result=read(path)
    assert result['script_sha256']==sha(A8/script),script
    for p in [path,A8/script]:inputs[str(p.relative_to(ROOT))]=sha(p)
    for name,h in result.get('source_files',{}).items():assert sha(ROOT/name)==h,name;inputs[name]=h
    for name,h in result.get('protected_sources',{}).items():assert sha(ROOT/name)==h,name
    for name,h in result.get('outputs',{}).items():
        assert sha(path.parent/name)==h;inputs[str((path.parent/name).relative_to(ROOT))]=h
    return result


source=receive(OUT/'screen.json','screen_PH_guided_wire_entry.py')
verified=receive(OUT/'verification.json','verify_PH_guided_wire_entry.py')
continuous=receive(OUT/'full_wire_continuous.json','verify_PH_guided_full_wire_continuous.py')
plot=receive(OUT/'plot.json','plot_PH_guided_wire_entry.py')
prior=receive(STOCK/'PH_attached_wire_entry/screen.json','screen_CAM_PH_attached_wire_entry.py')
assert source['status']==verified['status']==continuous['status']==plot['status']=='PASS'
assert prior['status']=='BLOCKED' and len(prior['trials'])==5
assert source['curves_sha256']==sha(OUT/'curves.npz')
assert verified['source_report_sha256']==continuous['source_report_sha256']==sha(OUT/'screen.json')
assert continuous['source_verification_sha256']==sha(OUT/'verification.json')
assert verified['wire_finite_positions']==171 and verified['continuous_sweeps']==875
assert continuous['continuous_guide_intervals']==174 and len(continuous['terminal_pair_intervals'])==54
assert source['complete_attached_assembly']==continuous['complete_attached_assembly']=='BLOCKED'
assert not source['main_applied'] and not continuous['manufacturing_release']
inputs[str((OUT/'curves.npz').relative_to(ROOT))]=sha(OUT/'curves.npz')
commands=[]
for script,log in [('screen_CAM_PH_attached_wire_entry.py','PH_attached_wire_entry.log'),
                   ('screen_PH_guided_wire_entry.py','PH_guided_wire_entry.log'),
                   ('verify_PH_guided_wire_entry.py','PH_guided_wire_verification.log'),
                   ('verify_PH_guided_full_wire_continuous.py','PH_guided_full_wire_continuous.log')]:
    p=A8.parent/'verification_logs'/log
    assert p.is_file() and 'Traceback (most recent call last)' not in p.read_text()
    inputs[str(p.relative_to(ROOT))]=sha(p)
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 2 --python mechanical/studies/prearrival_finish/harness_A8/'+script,
                         log=str(p.relative_to(ROOT)),exit_code=0))
lengths='、'.join(f'{x:.2f}' for x in source['original_nominal_lengths_mm'])
now=datetime.now(timezone.utc).isoformat()
md=f'''# PH 插头带四根完整导线的装配路径

更新时间：{now}。主模型 M1.47 未修改。候选图示拔出，装入按反序；四根自由线尾先留在颈部外侧，再另行处理穿颈。

![完整导线与插头动作](route.png)

## 已完成的名义几何检查

- 四根完整导线的171个位置复核通过；每根名义总长仍为 {lengths} mm，未借此增加裁线长度。
- 插头与四根前5mm直段：875个连续扫掠包络通过。
- 四根全线：174个连续区间通过。固定弯道的剩余部分始终是原曲线的子集；上方直线余料用覆盖范围验证，移动线根另做扫掠与线间检查。
- 四个自由端的竖直移动，以及54个关联端子对区间通过。端子形状仍是注明的预留，并非实际压接成品尺寸。
- 采用0.6604mm线外径、0.3mm间隙、至少9mm解析弯曲半径。最初8mm插合段沿用已记录的自身插座重叠例外，实际插合仍未验证。

模型检查中的“最大余线覆盖范围”是数学验证用的并集，不是给供应商追加的线材。每个实际姿态保持原来的四根总长。

## 装配前提

上壳保持16°并抬高14mm，固定承重桥已就位。H02/H03共4根身体线及24个其他插头空间参与检查；H01/H04的10根线和4个插头明确延后。
本研究仍使用此前记录的未采用通道候选，不能直接视为主模型整机装配通过。

## 为什么改变穿线顺序

原来先让线尾进入颈部，再抬升PH插头的五种线尾高度方案，在初始8mm抬升位置附近均遇到承重桥或轴承间隙问题。
新候选保持自由线尾在颈外，插头随圆滑路径转向。它关闭了这一段带线插接的几何缺口，不代表后续工序已经通过。

## 仍需在到货前完成

自由线尾从本页临时位置穿入颈部，并接上已研究的头部穿线与回位动作；H01/H04后装、其他跨关节线与FFC、扎带固定、手部工具和完整装配顺序；逐线最终长度及供应商制作图。
这些仍是项目设计工作。实际端子、线材、压接及未公开配件尺寸另等厂家资料/实物确认。

供应商按图制作已确定。PH/SH官方目录已有外形、适用线径和工装资料；具体压接工艺与资料版本边界见[完整端子工艺记录](../../../../../../../../../TOOLING_DETAILS.md)。本研究没有发布制造图、联系供应商或下单。

[171位置与来源](screen.json) · [875个连续包络](verification.json) · [全线连续检查](full_wire_continuous.json) · [命令及校验](publication.json)
'''
# Compute links explicitly to avoid errors in this deeply nested review directory.
import os
tooling=os.path.relpath(A8/'TOOLING_DETAILS.md',OUT)
overview=os.path.relpath(A8/'supplier_source_update/index.html',OUT)
old=os.path.relpath(STOCK/'PH_attached_wire_entry/screen.json',OUT)
md=md.replace('../../../../../../../../../TOOLING_DETAILS.md',tooling)
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MORI · PH带线插接</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1150px;margin:24px auto;padding:0 24px 48px;background:#f2f6f6;color:#284750}}section{{background:white;border-radius:10px;padding:22px;margin:18px 0}}.note{{background:#fff0d8}}a{{color:#076b80}}img{{width:100%;height:auto}}li{{margin:8px 0}}.numbers{{font-size:20px;color:#177c73}}</style>
<p><a href="{overview}">← 资料与设计进度</a></p><h1>PH 插头已能带四根完整导线走完这一段路径</h1>
<section><p class="numbers">171 个全线位置 · 174 个全线连续区间 · 875 个插头与线根扫掠包络</p><p>四根自由线尾先留在颈部外侧，插头沿圆滑通道转向。图示拔出，装入按反序；随后还须穿颈和收线。</p><a href="route.png"><img src="route.png" alt="插头就位、随弯道转向、到达上方空间三种状态的侧视和正视源模型投影"></a></section>
<section><h2>没有增加线材或修改结构来取得通过</h2><p>四根原名义总长为 {lengths} mm。0.6604mm线外径、0.3mm间隙保持；新路径的解析弯曲半径不小于9mm。尾部覆盖范围只是验证用的并集，不是额外裁线长度。</p><p>最初8mm插合段保留自身原生插座的有限重叠例外。PH完整预留、自由端子外形及真实压接仍有资料限制，不能视为实物插合合格。</p></section>
<section><h2>这段路径成立的装配条件</h2><p>上壳16° / +14mm，承重桥就位。H02/H03共4根身体线和24个其他插头空间保留；H01/H04的10根线和4个插头延后。研究使用此前记录的未采用通道候选，主模型M1.47未改。</p><p>旧顺序把线尾先穿入颈部，五种抬升方案都在初始动作中碰到桥/轴承间隙问题；<a href="{old}">失败记录</a>保留。</p></section>
<section class="note"><h2>完整线束仍未完成</h2><ul><li>把本页的临时自由线尾穿入颈部，衔接头部装配、回位与固定。</li><li>完成H01/H04后装、其他跨关节线、FFC、扎带和手部工具检查。</li><li>核定逐线长度、实际配套端子和供应商制作图。</li></ul><p>供应商按图制作已经确定。公开的<a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST PH</a>、<a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH</a>资料及<a href="{tooling}">逐料号工艺记录</a>继续作为来源；未公开尺寸和实际工艺组合仍需确认。本页不是制造放行。</p></section>
<p><a href="README.md">详细说明</a> · <a href="screen.json">171位置</a> · <a href="verification.json">插头与线根连续包络</a> · <a href="full_wire_continuous.json">全线连续检查</a> · <a href="publication.json">来源、命令和边界</a></p></html>'''
(OUT/'index.html').write_text(html)
report=dict(status='PASS',scope='Publication of one complete-wire insertion stage; whole harness incomplete',
    generated_utc=now,script_sha256=sha(SCRIPT),source_files=inputs,protected_sources=source['protected_sources'],
    outputs={n:sha(OUT/n) for n in ['index.html','README.md','route.png']},commands=commands,
    versions=dict(blender='5.2.2 LTS d13f752e3b9c',publisher_python=platform.python_version()),
    PH_with_full_CAM_wire_finite='PASS',finite_positions=171,PH_and_root_sweeps=875,
    PH_with_full_CAM_wire_continuous='PASS',full_wire_intervals=174,terminal_pair_intervals=54,
    full_harness='BLOCKED',subsequent_neck_threading='NOT_TESTED',supplier_cut_lengths=False,
    main_applied=False,manufacturing_release=False,physical_fit='NOT_TESTED')
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
state_path=A8.parent/'work_status.json';state=read(state_path)
state['CAM_PH_guided_wire_entry']=dict(publication=str((OUT/'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT/'publication.json'),finite='PASS',finite_positions=171,
    continuous='PASS',continuous_intervals=174,PH_and_root_sweeps=875,whole_harness='BLOCKED',main_applied=False)
item=next(r for r in state['remaining'] if r['id']=='harness')
item['latest_PH_attached_evidence']=str((OUT/'index.html').relative_to(A8.parent))
item['latest_PH_attached_detail']='采用颈外自由线尾临时排布，PH随圆滑路径转向；171位置、174全线连续区间及875插头/线根包络通过。自由端后续穿颈、H01/H04和完整制作图仍未完成；主模型不变。'
state['updated_utc']=now
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('GUIDE_PUBLICATION_DONE PASS; whole harness BLOCKED; main unchanged')
