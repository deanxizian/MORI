"""Publish the finite C4 result without replacing the historical C2 evidence."""
from pathlib import Path
import json, hashlib, datetime, re, html

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((HERE/n).read_text())
build=read('C4_build.json')
verify=read('C4_verification.json')
material=read('C4_material.json')
packing=read('C4_packing.json')
assert build['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assert verify['build_sha256']==material['build_sha256']==sha(HERE/'C4_build.json')
assert build['packing_sha256']==sha(HERE/'C4_packing.json')
assert material['script_sha256']==sha(HERE/'check_profile_material.py')
assert build['status']=='PASS' and not build['wire_hits']
assert verify['status']=='PASS' and material['status']=='BLOCKED'
wall=min(x['minimum']['distance_mm'] for x in material['neck_side_thickness_samples'])
overlap=material['minimum_nominal_head_shell_gap']['raw_overlap_mm3']
detail=(f'C4候选的11根局部导线、保护区及有限刚体装入检查通过；'
        f'原0.01mm³体积阈值检查未检出新增相交，但精查确认仰头25°时仍有约{overlap:.4f}mm³实体相交，'
        f'未达到0.3mm名义间隙；颈部过渡侧壁采样约{wall:.3f}mm，仍需修正。'
        '原头壳、光学件和压板高度保留，候选未应用。完整端部连接、线材/FFC、固定与应力释放、'
        '完整带线装配和供应商制作图仍未完成。')
out=dict(status='BLOCKED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='C4 follow-up; local wire clearance passes, print clearance/material review remains open',
         source_main_sha256=build['source_main_sha256'],description=detail,
         local_eleven_curves='PASS',local_pair_gap_lower_bound_mm=packing['minimum_pair_gap_lower_bound_mm'],
         thresholded_motion_screen='PASS',intersection_volume_threshold_mm3=.01,
         head_shell_gap_review='BLOCKED',minimum_gap_record=material['minimum_nominal_head_shell_gap'],
         sampled_side_wall_mm=wall,qualified_global_minimum_wall=None,
         protected_material_removed_mm3=build['protected_material_removed_mm3'],
         rigid_unwired_local_installation='PASS',normal_head_poses=130,
         full_endpoints='NOT_TESTED',wired_assembly='NOT_TESTED',actual_wire_selection='BLOCKED',
         whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
         evidence={n:sha(HERE/n) for n in ['C4_build.json','C4_packing.json','C4_verification.json','C4_material.json']})
(HERE/'C4_current_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
files=[BASE/'work_status.json',BASE/'index.html',HERE/'index.html',BASE/'whole_head_harness_M1_48/index.html']
before={str(p.relative_to(ROOT)):sha(p) for p in files}
p=BASE/'work_status.json';status=json.loads(p.read_text())
status['updated_utc']=out['utc']
status['neck_bearing_capacity_M1_48_C4']=out
status['neck_bearing_capacity_M1_48']['followup']='neck_bearing_capacity_M1_48/C4_status.html'
for row in status['remaining']:
    if row['id']=='harness':
        row.update(detail=detail,evidence='neck_bearing_capacity_M1_48/C4_status.html',
                   latest_capacity_evidence='neck_bearing_capacity_M1_48/C4_status.html',latest_capacity_detail=detail)
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
rows=''.join('<tr><td>'+html.escape(r['item'])+'</td><td>'+html.escape(r['status'])+'</td><td>'+html.escape(r['detail'])+'</td></tr>'
             for r in status['remaining'])
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · C4 进度与剩余工作</title><style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#24382f;background:#f5f6f3;margin:0}main{max-width:1000px;margin:auto;padding:30px 24px 60px}a{color:#176a51}h1{line-height:1.4;font-size:28px}.note{background:#fff0d9;padding:16px}table{border-collapse:collapse;background:white;width:100%}td,th{padding:12px;border-bottom:1px solid #d6ded6;text-align:left;vertical-align:top}</style><main>
<nav><a href="../index.html">到货前待办</a> · <a href="index.html">之前的 C2 结果</a></nav>
<h1>还剩五类到货前工作，完整线束是主要未完成项</h1>
<p class="note">'''+html.escape(detail)+'''</p>
<p>C4 的原体积阈值检查通过，并不等于有足够运动间隙。最新独立检查未通过，因此保留候选状态。主模型和装配动画仍为 M1.48 / M1.48-A1。</p>
<table><tr><th>本轮检查</th><th>结果</th></tr>
<tr><td>11 根局部导线</td><td>局部实体与线间检查通过；七根较粗线仍为空间样本，两个端点尚未连接所有真实端口。</td></tr>
<tr><td>原固定座材料</td><td>指定反力孔壁、承力连接、上部舵机座保护区移除体积为 0。</td></tr>
<tr><td>运动与净距</td><td>130 个有限姿态在 0.01 mm³ 体积阈值下未检出新增相交；精查仍有约 0.0027 mm³ 实体相交，未达到 0.3 mm 名义间隙，仍 BLOCKED。</td></tr>
<tr><td>侧壁</td><td>过渡处最近面距离采样约 '''+f'{wall:.3f}'+''' mm。这是有限采样，不是全件最小壁厚或强度合格值。</td></tr>
<tr><td>装入</td><td>轴承、压板、螺钉及工具的局部刚体路径通过。完整带线装配尚未完成。</td></tr></table>
<h2>当前剩余清单</h2><table><tr><th>类别</th><th>状态</th><th>未完成内容</th></tr>'''+rows+'''</table>
<p><a href="C4_current_review.json">本轮摘要</a> · <a href="C4_build.json">局部导线与打印实体</a> · <a href="C4_verification.json">体积阈值及装入检查</a> · <a href="C4_material.json">净距与侧壁采样</a> · <a href="../work_status.json">完整状态</a></p>
<p>PROTOTYPE / UNVALIDATED · 未应用主模型，未放行制造或采购。</p></main></html>'''
(HERE/'C4_status.html').write_text(page)
for p,link in [(HERE/'index.html','C4_status.html'),(BASE/'whole_head_harness_M1_48/index.html','../neck_bearing_capacity_M1_48/C4_status.html')]:
    text=p.read_text()
    text=re.sub(r'<aside id="C4-followup".*?</aside>','',text,flags=re.S)
    notice='<aside id="C4-followup" class="note"><b>后续 C4 结果：</b>局部11线通过，净距与过渡壁厚仍需修正，尚未采用。<a href="'+link+'">查看当前状态</a>。下方保留此前研究。</aside>'
    p.write_text(text.replace('<main>','<main>'+notice,1))
p=BASE/'index.html';text=p.read_text()
notice='<aside id="larger-neck-capacity-update" class="notice"><b>当前仍剩5类到货前工作。</b> '+html.escape(detail)+' <a href="neck_bearing_capacity_M1_48/C4_status.html">最新检查与剩余清单</a>。主模型 / 动画仍为 M1.48 / M1.48-A1。</aside>'
text,n=re.subn(r'<aside id="larger-neck-capacity-update".*?</aside>',notice,text,count=1,flags=re.S);assert n==1
text,n=re.subn(r'<tr><td>完整线束</td>.*?</tr>','<tr><td>完整线束</td><td>BLOCKED<br>机械＋硬件线材输入</td><td>'+html.escape(detail)+' <a href="neck_bearing_capacity_M1_48/C4_status.html">当前依据</a></td></tr>',text,count=1,flags=re.S);assert n==1
p.write_text(text)
(HERE/'C4_status_amendment.json').write_text(json.dumps(dict(utc=out['utc'],original_hashes=before,
    updated_hashes={str(p.relative_to(ROOT)):sha(p) for p in files},main_applied=False),ensure_ascii=False,indent=2)+'\n')
print('C4_STATUS_PUBLISHED',out['status'],'five categories remain; local candidate not adopted')
