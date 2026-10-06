"""Publish C6 as an unapproved candidate, retaining the current M1.49 assembly."""
from pathlib import Path
import datetime,hashlib,html,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes';C6=OUT/'c6_left_slot_entry'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
proof=read(C6/'combined/lower_nine_screen.json');geom=read(C6/'geometry_review.json');render=read(C6/'render_manifest.json')
assert proof['status']==geom['status']==render['status']=='PASS' and not proof['approved']
for report in [proof,geom,render]:
    for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
for row in render['images']:assert sha(C6/row['file'])==row['sha256']
assert sha(C6/'MORI_M1_49_C6_entry_candidate.blend')==render['blend_sha256']
main=sha(ROOT/'mechanical/mori_v1_2.blend');assert main==proof['sources']['mechanical/mori_v1_2.blend']
gap=min(r['gap_lower_bound_mm'] for r in proof['whole_pairs']);volume=geom['construction']['removed_volume_mm3']
style='''<style>body{margin:0;background:#f1f5f6;color:#203a44;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:28px 24px 60px}h1{font-size:30px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:14px}.notice{background:#fff0d5;padding:18px;border-radius:10px}a{color:#17687b}td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #c3d3d8}table{width:100%;border-collapse:collapse}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style>'''
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · C6 左侧穿线口候选</title>{style}<main>
<a href="../index.html">← 线束检查总览</a><h1>C6：现有左侧穿线口加宽 0.8 mm</h1>
<p class="notice">待用户确认，尚未应用。主模型、STL和 M1.49-A1 视频仍是已确认的 C5＋K1。下部线束的名义几何检查通过，完整线束仍为 BLOCKED。</p>
<p>把 Yaw_Base 现有左侧弧形开口的外缘半径从 11.7 增至 12.5 mm，开口宽度由 2.15 增至 2.95 mm。实际只削去下方承台内缘约 {volume:.2f} mm³ 材料；不增加零件、螺钉或外部凸台。开口角度、轴承座接触面、头部位置和 K1 压板固定孔保持。</p>
<figure><img src="section_comparison.png"><figcaption>实际实体剖面对比。橙色为删去的窄边；仅扩大已有开口。修改只落在 R11.7～12.5、Z145.5～147 mm 的局部范围。</figcaption></figure>
<div class="grid"><figure><img src="body_entry_rear.png"><figcaption>九根身体到颈部导线的共同候选：3 根舵机总线、2 根 CAM 供电、4 根 CAM 信号。线径为未选定的资料参考；上端开放。两根喇叭局部预留线未在此图显示。</figcaption></figure>
<figure><img src="body_entry_under.png"><figcaption>下方视角。外壳等遮挡物在图中隐藏；碰撞检查仍包含完整实体和接插件预留。</figcaption></figure></div>
<table><tr><th>检查范围</th><th>结果及界限</th></tr>
<tr><td>零件修改</td><td>仅 Yaw_Base 删减材料，仍为一个连续实体；R11.69以内和R12.51以外的材料未改变。轴承与紧固件未移动。</td></tr>
<tr><td>九根下部导线共同存在</td><td>PASS。选中的9条连续路线经过当前候选实体、13个偏航／10个俯仰离散姿态和自身回绕检查。失败的其他候选保留在原记录中。</td></tr>
<tr><td>线间与连接</td><td>PASS。含2根喇叭局部预留，共715组完整线间检查，最小保守间隙下界 {gap:.3f} mm，要求0.3 mm；117处连接坐标吻合。</td></tr>
<tr><td>未完成</td><td>CAM上段汇合、其余端部、固定与应力释放、FFC/FPC及带线装配。C6通过的是下部路线，不能与未通过的上段拼成完整线束。</td></tr>
<tr><td>实物验证</td><td>PA12强度、实际线束成形／回弹、动态疲劳、端子与安装公差仍为 NOT_TESTED；曲线长度不是供应商下料尺寸。</td></tr></table>
<p><a href="MORI_M1_49_C6_entry_candidate.blend">可编辑 Blender 候选</a> · <a href="combined/lower_nine_screen.json">九线完整下部检查</a> · <a href="geometry_review.json">材料变化与连通性</a> · <a href="../entry_topology_review/radial_sections.png">原结构入口剖面</a> · <a href="../entry_topology_review/cam34_overlap.png">原回弯交叉位置</a></p>
<p>确认范围仅为上述0.8 mm开口变化。其余打印件、承力连接、孔位、硬件及运动范围不在本候选的改动范围内。</p></main></html>'''
(C6/'index.html').write_text(page)
# Preserve the former publication and evidence paths, then add a clearly
# separate current candidate. The prior publisher does not modify geometry.
subprocess.run([sys.executable,str(HERE/'publish_lane_progress.py')],cwd=ROOT,check=True)
main_page=OUT/'index.html';text=main_page.read_text()
block=f'''<section id="entry-c6" class="notice"><h2>最新：C6 下部线束候选通过，待确认</h2><p>原结构下的错层进线组合仍未通过。独立 C6 候选将现有左侧开口加宽0.8 mm，九根下部线找到共同通过的组合；715组线间检查最小间隙下界{gap:.3f} mm。头部上段仍有冲突，完整线束仍未完成，主模型没有采用C6。</p><p><a href="c6_left_slot_entry/index.html">查看结构差异、九线候选和确认范围</a> · <a href="entry_topology_review/xy_sections.png">实际剖面</a> · <a href="nine_lower_entry_stagger/combined/lower_nine_screen.json">原结构四层入口检查</a> · <a href="cam_cross_order_upper/local_join/local_join_screen.json">上部另一排列的检查</a> · <a href="entry_commands.json">本轮实际命令</a></p></section>'''
text=text.replace('<h1>线束入口与整束组合</h1>','<h1>线束入口与整束组合</h1>'+block);main_page.write_text(text)
summary='已应用C5＋K1。原结构下九线错层组合仍未通过；独立C6候选把现有左侧开口加宽0.8mm后，九条下部导线共同通过有限名义检查，715组线间检查最小下界0.308mm。C6尚未确认或应用；CAM上段、端部、固定、FFC/FPC和带线装配仍未完成，完整线束BLOCKED。'
(OUT/'README.md').write_text('# M1.49 线束入口组合复核\n\n'+summary+'\n\nC6对比入口：c6_left_slot_entry/index.html。主模型和动画未加入候选导线。\n')
work_file=HERE.parent/'work_status.json';work=read(work_file);row=next(r for r in work['remaining'] if r['id']=='harness')
row.update(detail=summary,latest_M1_49_joint_route_detail=summary,latest_unapproved_candidate='head_harness_M1_49/remaining_routes/c6_left_slot_entry/index.html',candidate_requires_user_approval=True)
work['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(work_file,work)
status_path=ROOT/'mechanical/reports/interface_completion_status.json';status=read(status_path)
status['pending']=[r for r in status['pending'] if r.get('id')!='harness']+[row];write(status_path,status)
index=ROOT/'mechanical/index.html';text=index.read_text()
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}'+(f' <a href="studies/prearrival_finish/{r["evidence"]}">检查记录</a>' if r.get('evidence') else '')+'</td></tr>' for r in work['remaining'])
text,n=re.subn(r'<section id="remaining">.*?</section>',lambda _: '<section id="remaining"><h2>当前剩余项目</h2><table>'+rows+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>',text,flags=re.S);assert n==1
text,n=re.subn(r'<p id="M1-49-route-progress">.*?</p>',lambda _:'<p id="M1-49-route-progress">C6下部九线候选通过，待确认结构；完整线束尚未完成。<a href="studies/prearrival_finish/head_harness_M1_49/remaining_routes/c6_left_slot_entry/index.html">查看候选与检查范围</a>。</p>',text,flags=re.S);assert n==1;index.write_text(text)
subprocess.run([sys.executable,str(ROOT/'mechanical/scripts/publish_animation_update.py')],cwd=ROOT,check=True)
publication=read(OUT/'publication.json')
files=[main_page,OUT/'README.md',OUT/'entry_commands.json',OUT/'execution_failures.json',C6/'index.html',C6/'geometry_review.json',C6/'plot_manifest.json',C6/'section_comparison.png',C6/'render_manifest.json',C6/'MORI_M1_49_C6_entry_candidate.blend',C6/'combined/lower_nine_screen.json',*[C6/r['file'] for r in render['images']],OUT/'entry_topology_review/sections.json',OUT/'entry_topology_review/xy_sections.png',OUT/'entry_topology_review/radial_sections.png',OUT/'entry_topology_review/cam34_overlap.png',OUT/'entry_topology_review/closest_cam34.json',OUT/'nine_lower_entry_stagger/combined/lower_nine_screen.json',OUT/'cam_cross_order_upper/local_join/local_join_screen.json']
publication['files'].update({str(p.relative_to(ROOT)):sha(p) for p in files})
publication.update(utc=work['updated_utc'],C6_lower_nine='PASS',C6_approved=False,C6_main_applied=False,C6_gap_lower_bound_mm=gap,current_main_lower_nine='BLOCKED',full_harness='BLOCKED',entry_publisher_sha256=sha(Path(__file__)))
write(OUT/'publication.json',publication);print('ENTRY_CANDIDATE_PUBLISHED',gap,flush=True)
