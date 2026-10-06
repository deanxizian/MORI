"""Publish the completed lane studies and the received hardware evidence."""
from pathlib import Path
import datetime,hashlib,html,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];MECH=ROOT/'mechanical'
OUT=HERE/'remaining_routes';BASE=OUT/'nine_four_order_expanded/combined';LOCAL=OUT/'left_tall_balanced'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
proof=read(BASE/'lower_nine_screen.json');local=read(LOCAL/'neck_screen.json')
entry_file=OUT/'cam_four_tall_directed/body_prefix_screen.json';entry=read(entry_file)
upper_file=OUT/'cam_four_order_upper_diverse/local_join/local_join_screen.json';upper=read(upper_file)
receipt=read(OUT/'hardware_wire_evidence_receipt.json');render=read(LOCAL/'render_manifest.json')
for report in [proof,local,receipt,render,upper,entry]:
    for name,h in {**report.get('sources',{}),**report['inputs']}.items():assert sha(ROOT/name)==h,name
assert local['status']==receipt['status']==render['status']=='PASS'
source=sha(MECH/'mori_v1_2.blend');assert source==receipt['main_blend_sha256']
assert source==proof['sources']['mechanical/mori_v1_2.blend']
for row in render['images']:assert sha(LOCAL/row['file'])==row['sha256']
blend=LOCAL/'MORI_M1_49_late_neck_study.blend';assert sha(blend)==render['blend_sha256']
lane=next(r for r in local['results'] if r['status']=='PASS')
passed=proof['status']=='PASS';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
summary=('九条身体至颈部导线已找到同时通过有限名义检查的组合；四根CAM信号线按顺序经过既有左侧开口，电气针序保持。'
         if passed else '四根CAM线改走左侧，两根喇叭预留线放到右侧相邻位置；延后转弯的颈部局部排布通过。旧入口的九条身体线仍未找到同时通过的组合，新高位进线候选也碰到固定Yaw支架。')
summary+='两根喇叭线仍只预留颈部空间，当前细线为未选定目录参考。打印件、PCB及主模型保持；完整端部、上部连接、固定、FFC/FPC和带线装配未完成，完整线束仍BLOCKED。'
upper_status='PASS，限局部颈段与CAM上段同时存在' if upper['status']=='PASS' else 'BLOCKED，单根上段有解，四根的组合未通过'
count=sum(proof['candidate_counts'].values());gap=min(r['gap_lower_bound_mm'] for r in lane['pair_checks'])
status='PASS，限九条下部候选同时存在' if passed else 'BLOCKED，未找到同时通过的组合'
style='''<style>body{margin:0;background:#f1f5f6;color:#203a44;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:28px 24px 64px}h1{font-size:30px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:14px}.notice{background:#fff0d5;padding:18px;border-radius:10px}a{color:#17687b}td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #c3d3d8}table{width:100%;border-collapse:collapse}code{overflow-wrap:anywhere}@media(max-width:760px){main{padding:18px 12px}.grid{grid-template-columns:1fr}}</style>'''
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.49 · 线束入口组合复核</title>{style}<main>
<a href="../../neck_adoption/index.html">← 已应用的颈部结构</a><h1>线束入口与整束组合</h1><p>{stamp}</p>
<p class="notice">完整线束仍为 BLOCKED。这些是独立候选；主模型、STL和M1.49-A1装配视频没有加入这些导线。没有采购或制造放行。</p>
<p>{html.escape(summary)}</p><div class="grid">
<figure><img src="left_tall_balanced/neck_entry.png"><figcaption>新的颈部局部：CAM在左侧，喇叭预留在右侧，Z149才开始转弯。橙色导线是未选定参考，开放端还没有接至两端。</figcaption></figure>
<figure><img src="left_tall_balanced/neck_exposed.png"><figcaption>隐藏部分结构查看11条局部曲线；间隙检查仍包含完整实体。这不是整机接线完成图。</figcaption></figure></div>
<h2>本次实际检查</h2><table><tr><th>范围</th><th>结果</th></tr>
<tr><td>左侧颈部11条局部曲线</td><td>PASS。{lane['checks']}项实体分组检查、{len(lane['pair_checks'])}组线间检查；最小间隙下界{gap:.3f}mm，最小采样弯曲半径{lane['minimum_sampled_bend_mm']:.2f}mm。限定于13个偏航、10个俯仰离散姿态及所用数学曲线。</td></tr>
<tr><td>九根身体线同时存在（旧Z142入口）</td><td>{status}。本次参与组合的独立选项共{count}条；单线通过不代表能同时装入。</td></tr>
<tr><td>新Z149入口的身体过渡</td><td>BLOCKED。本轮重算与从外侧进入的圆弧均未找到通过路径；高位入口局部放得下，不等于身体导线能穿入。</td></tr>
<tr><td>头部上端连接（Z142研究）</td><td>{upper_status}。已重新生成上部连接；四线组合仍有冲突，也尚未与新的Z149局部排布联合检查。</td></tr>
<tr><td>端头与线材</td><td>已接收硬件资料复核。部分目录字段匹配；压接、供电全过程、完整USB尾线和舵机分线板仍未定型。</td></tr>
<tr><td>完整线束与制造</td><td>BLOCKED。固定、应力释放、FFC/FPC、带线装配及制作图尚未完成。动态回弹、疲劳、温升和实配NOT_TESTED。</td></tr></table>
<p>五条供电/舵机线采用未选定Alpha2622的最大外径1.1684mm参考；两条喇叭局部线采用未选定Alpha2626的0.889mm参考；CAM信号线为0.6604mm参考。所需0.3mm表面间距是规划值，并非已验证的生产公差。没有缩放真实硬件或降低检查阈值。</p>
<h2>硬件资料新增结论</h2><p>无N后缀的XH端子与2622仅AWG和绝缘外径两项匹配；带N后缀的版本不匹配。Adafruit5978原装CC配置是受电端，不能直接作为合格CAM供电端。已取得GCT裸公头厂图，但它还不是完整带线组件。较粗的Alpha6713条件备选不能直接替换R6.5路径，尚未应用。</p>
<p><a href="HARDWARE_REVIEW_RECEIPT.md">机械接收说明</a> · <a href="../../../../../hardware/v1_2/harness_feasibility_20261006/README.md">硬件完整证据与压降计算</a> · <a href="hardware_wire_evidence_receipt.json">75文件只读接收记录</a></p>
<h2>证据与剩余工作</h2><p><a href="nine_four_order_expanded/combined/lower_nine_screen.json">Z142入口九线组合</a> · <a href="cam_four_tall_directed/body_prefix_screen.json">Z149进线检查</a> · <a href="cam_four_order_upper_diverse/local_join/local_join_screen.json">CAM上段组合</a> · <a href="left_tall_balanced/neck_screen.json">当前颈部局部检查</a> · <a href="left_tall_balanced/MORI_M1_49_late_neck_study.blend">局部Blender研究</a> · <a href="ENDPOINT_REQUIREMENTS.md">端部输入与下一步</a> · <a href="INTERFACE_NOTES.md">线材与功能依据</a> · <a href="lane_height_commands.json">本轮实际命令</a> · <a href="commands.json">前期命令</a></p>
<details><summary>保留的其他研究</summary><p><a href="nine_lane_swap/combined/lower_nine_screen.json">交换机械排列</a> · <a href="nine_height_entry/combined/lower_nine_screen.json">错开汇入高度</a> · <a href="stagger_neck_spk26_phase2/neck_screen.json">错层方案局部段</a> · <a href="CAM_swap_pair_diagnosis.json">交换排列的全局距离诊断</a></p><p>有限候选失败只说明这些路线不能同时满足约束，不证明所有布线方式均不可行。</p></details>
<small>当前主模型SHA256：<code>{source}</code>。PROTOTYPE / UNVALIDATED。</small></main></html>'''
(OUT/'index.html').write_text(page)
(OUT/'README.md').write_text('# M1.49 线束入口组合复核\n\n'+summary+'\n\n入口为 index.html。当前曲线长度不是下料尺寸。硬件资料补充见 HARDWARE_REVIEW_RECEIPT.md。\n')
work=read(HERE.parent/'work_status.json');row=next(r for r in work['remaining'] if r['id']=='harness')
rel='head_harness_M1_49/remaining_routes/index.html'
row.update(detail=summary,evidence=rel,latest_M1_49_joint_route_detail=summary,latest_M1_49_joint_route_evidence=rel,
           latest_wire_electrical_evidence='head_harness_M1_49/remaining_routes/HARDWARE_REVIEW_RECEIPT.md')
work['updated_utc']=stamp
work['completed']=[r for r in work['completed'] if r['id'] not in ['M1_49_lower_nine','M1_49_CAM_nine_coexistence']]
if passed:work['completed'].append(dict(id='M1_49_lower_nine',status='PASS',detail='左侧分流的九条下部导线组合有限检查通过；头部上端与完整线束仍未完成。',evidence=rel))
write(HERE.parent/'work_status.json',work)
status_report=read(MECH/'reports/interface_completion_status.json')
status_report['pending']=[r for r in status_report['pending'] if r.get('id')!='harness']+[row]
write(MECH/'reports/interface_completion_status.json',status_report)
index=MECH/'index.html';text=index.read_text()
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}'+(f' <a href="studies/prearrival_finish/{r["evidence"]}">检查记录</a>' if r.get('evidence') else '')+'</td></tr>' for r in work['remaining'])
block='<section id="remaining"><h2>当前剩余项目</h2><table>'+rows+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>'
text,n=re.subn(r'<section id="remaining">.*?</section>',lambda _:block,text,flags=re.S);assert n==1
banner='<p id="M1-49-route-progress">'+('九条下部路线已找到通过的组合；完整线束仍未完成。' if passed else '颈部局部路线通过；九线完整组合仍未通过。')+f'<a href="studies/prearrival_finish/{rel}">查看当前研究与剩余项</a>。</p>'
text,n=re.subn(r'<p id="M1-49-route-progress">.*?</p>',lambda _:banner,text,flags=re.S);assert n==1;index.write_text(text)
subprocess.run([sys.executable,str(MECH/'scripts/publish_animation_update.py')],cwd=ROOT,check=True)
files=[OUT/'index.html',OUT/'README.md',OUT/'HARDWARE_REVIEW_RECEIPT.md',OUT/'hardware_wire_evidence_receipt.json',
       OUT/'ENDPOINT_REQUIREMENTS.md',OUT/'INTERFACE_NOTES.md',OUT/'lane_height_commands.json',OUT/'commands.json',
       BASE/'lower_nine_screen.json',upper_file,entry_file,OUT/'execution_failures.json',LOCAL/'neck_screen.json',LOCAL/'render_manifest.json',blend,
       *[LOCAL/r['file'] for r in render['images']]]
write(OUT/'publication.json',dict(status='PASS',utc=stamp,source_blend_sha256=source,
    files={str(p.relative_to(ROOT)):sha(p) for p in files},lower_nine=proof['status'],CAM_rejoined='NOT_TESTED',CAM_upper_local=upper['status'],new_tall_body_entry=entry['status'],
    main_geometry_changed=False,full_harness='BLOCKED',manufacturing_release=False,script_sha256=sha(Path(__file__))))
print('LANE_PROGRESS_PUBLISHED',proof['status'],flush=True)
