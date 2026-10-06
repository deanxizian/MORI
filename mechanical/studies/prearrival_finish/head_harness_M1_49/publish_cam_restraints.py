"""Publish bounded restraint progress while keeping the assembly failure visible."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes';REST=OUT/'cam_restraints';VIEW=REST/'review_parts'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
paths=[REST/'material_stations.json',REST/'sliding_guide_v4/review.json',REST/'return_clamp_v3/review.json',
       REST/'return_material_stations.json',REST/'terminal_gate_v2/review.json',REST/'tool_access/review.json',
       REST/'tool_angles/review.json',REST/'tool_angles_extended/review.json',VIEW/'review.json']
reports=[read(p) for p in paths]
for r in reports:
    assert not r['main_changed']
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
for i in [0,1,2,3,4,8]:assert reports[i]['status']=='PASS'
for i in [5,6,7]:assert reports[i]['status']=='BLOCKED'
pub=read(OUT/'publication.json');assert pub['source_blend_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend') and not pub['C6_approved']
now=datetime.datetime.now(datetime.timezone.utc).isoformat();assets=[];figures=''
labels={'head_overview.png':'头部候选总览','sliding_guide.png':'偏航托架的一体滑动导向','return_clamp.png':'俯仰托架的一体夹持座与扎带','head_pitch_25.png':'抬头25°的候选姿态'}
for row in reports[-1]['images']:
    p=VIEW/row['file'];assert sha(p)==row['sha256'];assets.append(p)
    extra='局部图仅保留相应承载打印件与线束；夹持座图另保留CAM板。隐藏仅用于看清结构，干涉检查仍包含完整原生部件。' if row['file'] in ['sliding_guide.png','return_clamp.png'] else '外壳隐藏，其他原生硬件保持原尺寸与姿态。'
    figures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="{labels[row["file"]]}" style="width:100%"><figcaption>{labels[row["file"]]}。{extra}</figcaption></figure>'
blend=VIEW/'MORI_M1_49_CAM_restraint_candidate.blend';assert sha(blend)==reports[-1]['blend_sha256'];assets.append(blend)
links=''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.parent.name+" / "+p.name)}：{r["status"]}</a></li>' for p,r in zip(paths,reports))
section=f'''<!-- CAM_RESTRAINT_PROGRESS --><section id="cam-restraints"><h2>最新：CAM导向与夹持候选，装配仍有待解决项</h2>
<p><strong>主模型仍为已应用C5＋K1的M1.49。</strong>以下是独立研究，未写入主模型、STL或装配视频；C6局部开口也仍待确认。</p>
<p>本轮发现：偏航时，颈部到中间导向点的材料长度变化约8.04～8.49mm。因此中间不能夹死，必须允许滑动；真正的防拉扯夹持留在身体端和随俯仰运动的头部端。</p>
<p>新候选在Pitch_Yoke上形成5.5×2.6mm短滑动窗口；在Pitch_Cradle上形成一个夹持座，把扎带移到四根CAM线回弯后的现有直段。调整2件现有打印件，不增加独立打印件或螺钉，增加1条扎带。当前四根CAM路线及其他七条参考线全部保留。</p>
<table><thead><tr><th>检查</th><th>当前结论</th></tr></thead><tbody>
<tr><td>导向与夹持几何</td><td>PASS：130个头部组合姿态；导向1430次、夹持4290次线/特征检查，原生硬件和两处候选之间未检出所查干涉</td></tr>
<tr><td>夹持点是否拉扯活动线段</td><td>PASS：520次材料位置核对，头部固定点相对两端的数值变化均小于0.01mm；偏航中间点仍须滑动</td></tr>
<tr><td>局部穿端子空间</td><td>条件PASS：仅按1.8×1.0×4.1mm估计裸端子检查直穿窗口，不代表真实压接端子或完整穿线装配通过</td></tr>
<tr><td>扎带作业</td><td>BLOCKED：三种80mm临时长尾空间可用，但已查的17个剪钳方向均受托架或线路阻挡；需要验证预装顺序或其他可用工具路径</td></tr>
</tbody></table>
<p>拟定穿线要求：供应商先不把CAM端端子插入胶壳，穿过颈部及导向后再入壳。此要求仍需真实端子、压接尺寸和装配方法确认；不是采购或加工放行。</p>
{figures}<p><a href="{blend.relative_to(OUT).as_posix()}">可编辑独立候选</a> · <a href="CAM_RESTRAINT_PROGRESS.md">状态与下一步</a> · <a href="c6_left_slot_entry/index.html">C6待确认开口</a> · <a href="upper_connection_commands.json">实际命令和失败候选记录</a></p>
<p>下一步先验证夹持和剪尾的预装位置、对应的自由线形，以及随后装入头托的连续过程；再完成身体端固定、其余上端接口、FFC/FPC和整机带线装配。完整线束仍为BLOCKED。实际滑动磨损、夹持力、弯折寿命及打印强度仍为NOT_TESTED。</p><ul>{links}</ul></section><!-- /CAM_RESTRAINT_PROGRESS -->'''
page=OUT/'index.html';s=page.read_text();s=re.sub(r'<!-- CAM_RESTRAINT_PROGRESS -->.*?<!-- /CAM_RESTRAINT_PROGRESS -->','',s,flags=re.S)
s=s.replace('<h2>最新：CAM四线连续路径（C6条件候选）</h2>','<h2>此前：CAM四线连续路径（C6条件候选）</h2>')
s=s.replace('夹持位置复核：偏航端规划夹持点中心距','早期位置测距（下方已有新候选）：偏航端规划夹持点中心距')
s=s.replace('</main>',section+'</main>');page.write_text(s)
note=OUT/'CAM_RESTRAINT_PROGRESS.md'
note.write_text('''# CAM固定研究：局部几何通过，装配尚未关闭

主模型保持M1.49 C5＋K1，C6及本轮固定特征均未应用。现有线路没有改变；几组供电线路偏移试验失败，已保留报告，没有选用。

- 中间点需要滑动8.04～8.49mm。当前候选为Pitch_Yoke一体短导向，窗口5.5×2.6mm。
- Pitch_Cradle上的夹持座采用回弯后的15mm固定直段；扎带中心所在平面Z215mm。两个特征分别与原承载件构成单一连通实体，无新增独立打印件；拟增加1条扎带。
- 130姿态下，导向1430项线/特征检查、夹持4290项检查均通过。固定点520次材料位置检查通过。所有结果只属于名义几何。
- 局部裸端子直穿只采用1.8×1.0×4.1mm估计包络；三个先穿导线需要临时侧排。真实端子/压接尺寸、整段线形转换仍未验证。
- 扎带80mm临时长尾的0、2、4号空间通过。剪钳在当前就位装配状态下，0度、五个负角、十一个扩展角，共17个方向均未通过。不得把此夹持方案称为可完成装配。

下一步：优先检查在头托装入前完成扎带夹持和剪尾的预装方案，以及随后装入头托时的连续带线变形；不能直接删掉Pitch_Yoke等实际障碍来放行。若仍不可行，再研究工具、扎带头方向或固定位置的具体候选。完成后再请求必要的结构确认。

身体端固定、其他上端接口、FFC/FPC、供应商端头与完整带线装配仍未完成。实际PA12强度、夹持力、滑动磨损和疲劳属于待实物验证项。主模型、STL和装配视频均未采用候选。
''')
readme=OUT/'README.md';readme.write_text('''# M1.49线束候选

主模型C5＋K1已应用；C6尚待确认。最新进展见index.html#cam-restraints及CAM_RESTRAINT_PROGRESS.md。

四根CAM连续路径与新滑动导向/夹持座的运动几何通过；固定点材料位置已核对。剪扎带的操作空间仍BLOCKED，需预装与带线装入检查。候选未进入主模型/STL/装配视频，完整线束及加工放行均未完成。
''')
state=read(OUT/'continuation_status.json');state.update(utc=now,active_processes=[])
state['upper_current'].update(restraint_design='BLOCKED',restraint_geometry='PASS',sliding_guide='cam_restraints/sliding_guide_v4/review.json',
    fixed_CAM_return_clamp='cam_restraints/return_clamp_v3/review.json',fixed_material_stations='cam_restraints/return_material_stations.json',
    local_assumed_terminal_gate='cam_restraints/terminal_gate_v2/review.json',tool_access='BLOCKED',full_harness='BLOCKED')
state['next_work']=[
 'C5+K1 are already applied. C6 approval remains pending. Do not apply C6 or restraint solids to main without the user-required structural review.',
 'Preserve current cam_side_fans/c6_join/candidate_curves.npz. Power-offset trials power_clearance/v2/v3 failed and were not selected.',
 'Guide v4 and return_clamp_v3 pass native and 11-route motion checks. Return clamp uses the pitch-fixed15mm straight at Z215. Material audit passes; yaw guide must slide8.04..8.49mm.',
 'Resolve cutter work: tool_access plus tool_angles plus tool_angles_extended checked17directions, all BLOCKED. Three80mm loose tails pass. A preassembly stage may help, but must verify full wire deformation and later installation rather than dropping real obstacles from checks.',
 'Terminal gate v2 passes only an ASSUMED1.8x1.0x4.1mm bare-contact box and three temporary wire lanes. Real contact and crimp envelope and whole feed remain unresolved.',
 'Next complete body strain relief, remaining SCS/power/speaker upper endpoints, FFC/FPC and full wired assembly. Supplier lengths are not released.'
]
write(OUT/'continuation_status.json',state)
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in paths+assets+[page,note,readme,OUT/'upper_connection_commands.json']})
pub.update(utc=now,CAM_restraint_geometry='PASS',CAM_restraint_assembly='BLOCKED',full_harness='BLOCKED',
           restraint_publisher_sha256=sha(Path(__file__)),restraint_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub);print('CAM_RESTRAINT_PUBLISHED',flush=True)
