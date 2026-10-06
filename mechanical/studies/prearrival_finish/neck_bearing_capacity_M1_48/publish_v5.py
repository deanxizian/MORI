"""Publish the checked C5 proposal, preserving the unapproved main model."""
from pathlib import Path
import json,hashlib,datetime,re
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((HERE/n).read_text())
b=read('C5_build.json');v=read('C5_verification.json');m=read('C5_material.json');p=read('C4_packing.json')
assert b['status']==v['status']==m['status']=='PASS'
assert v['build_sha256']==m['build_sha256']==sha(HERE/'C5_build.json')
assert b['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
for report,script in [(b,'build_candidate_v5.py'),(v,'verify_candidate_v5.py'),(m,'check_profile_material_v5.py')]:
    assert report['script_sha256']==sha(HERE/script)
assert b['neck_helper_sha256']==sha(HERE/'profile_neck_v5.py')
assert read('C5_review_sections.json')['script_sha256']==sha(HERE/'render_v5.py')
wall=min(r['minimum']['distance_mm'] for r in m['neck_side_thickness_samples'])
assert wall>=2.2
gap=m['minimum_nominal_head_shell_gap']['gap_mm']
ygap=min(r['gap_mm'] for r in m['head_shell_gap_rows'] if r['part']=='Pitch_Yoke')
detail=(f'C5独立候选已通过11根局部导线、130姿态的实体检查、头壳净距与过渡壁厚采样，'
        f'最小已查头壳名义间隙{gap:.3f}mm、过渡侧壁采样约{wall:.3f}mm；局部无新增软线的轴承/压板/螺钉装入和工具路径通过。'
        '需将偏航轴承20×32×7改为30×42×7并调整3件现有打印件，候选尚待用户确认，未应用主模型。'
        '完整端部连接、实际线材/FFC、固定与应力释放、完整带线装配及供应商制作图仍未完成。')
assets=['C5_supports.png','C5_neck.png','C5_sections.png','C5_sections.svg','C5_review.blend']
for n in assets:assert (HERE/n).is_file()
review=dict(status='PASS',scope='Finite local candidate checks only; not complete wiring or manufacturing approval',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_main_sha256=b['source_main_sha256'],
    changed_prints=['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper'],
    bearing_reference=dict(original='NSK6804ZZ',candidate='NSK6806ZZ',dimensions_mm=[[20,32,7],[30,42,7]],
        source_manifest_sha256=sha(HERE/'sources/manifest.json'),nominal_bearing_only_mass_delta_g=7.,
        evidence='VENDOR_DOCUMENTED boundary and approximate catalogue mass; not physical fit',price=None,stock=None),
    added_printed_parts=0,added_fasteners=0,keeper_fastener_pose_change_mm=0,
    local_eleven_curves='PASS',pair_gap_lower_bound_mm=p['minimum_pair_gap_lower_bound_mm'],
    head_poses=130,thresholded_pair_pose_checks=v['distinct_pair_pose_checks'],
    head_shell_minimum_checked_gap_mm=gap,yoke_shell_minimum_checked_gap_mm=ygap,
    sampled_side_wall_mm=wall,qualified_global_minimum_wall=None,
    protected_material_removed_mm3=b['protected_material_removed_mm3'],
    finite_rigid_local_service='PASS',stop_contact_sample_deg=[r['hit']['first_sampled_overlap_deg'] for r in v['stop_contacts']],
    raw_zero_intersection_not_inferred_from_volume_threshold=True,
    full_endpoints='NOT_TESTED',actual_wire_selection='BLOCKED',wired_assembly='NOT_TESTED',
    whole_harness='BLOCKED',strength='NOT_TESTED',main_applied=False,approval='PENDING_USER',manufacturing_release=False,
    next_work='Complete the endpoint routes, anchors, supplier inputs and full wired assembly on an approved structural basis.',
    evidence={n:sha(HERE/n) for n in ['C5_build.json','C5_verification.json','C5_material.json','C4_packing.json','C5_review_sections.json']+assets})
(HERE/'C5_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
url='https://www.oss.nsk.com/tw/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6806zz-apn.html'
body=f'''# C5：较大内孔轴承与连续颈部通道候选

候选局部数字检查 PASS；完整线束 BLOCKED；未应用主模型，尚待用户确认。

{detail}

| 修改 | 候选范围 |
|---|---|
| 轴承 | NSK6804ZZ 20×32×7 → NSK6806ZZ 30×42×7；分别按厂家边界重建，没有缩放硬件 |
| 打印件 | Yaw_Base、Pitch_Yoke、Yaw_Anti_Lift_Keeper 三件；无新增件、无新增紧固件 |
| 原位置 | 保持头壳、LCD、相机、舵机与四枚压板紧固件的位置；压板恢复原高度 |
| 保护区 | 原D形反力孔壁、两条原承力连接及上部舵机座保护区移除体积均为0 |
| 运动范围 | 保留正常 yaw ±60°、pitch −20°～+25°；限位首次采样相交在 ±64.25° |

![独立候选](C5_supports.png)

蓝绿色是候选打印件；橙色是11根局部空间样本。头壳、屏幕等为观察隐藏，数字检查仍包括它们。两端是Z130/Z200临时端点，尚未全部连接真实接口。

![颈部细节](C5_neck.png)

上图隐藏固定桥和压板以观察旋转颈部；既有螺钉/嵌件因此悬空显示，并非最终装配状态。承力面和实体拓扑与检查使用相同NPZ，渲染仅按主模型的平面/曲面法线规则显示，没有改变顶点或三角形。

![实际实体剖面对比](C5_sections.png)

左为主模型，中为此前未通过的C4，右为C5。上排是Z166截面；下排是X8.5截面，均使用原后壳仰头25°后的实际实体。圆点只示意线径，图不是完整扫掠。

数字检查：11根局部路线与当前209实体、29对插包络、14根已有候选固定线检查通过；线间保守下界{p['minimum_pair_gap_lower_bound_mm']:.3f}mm。7根OD1.4224mm仍是空间样本，未选定或验证SH/GH压接线；4根OD0.6604mm使用Alpha2841/7目录最大外径参考，不是已采购线束。

130个有限姿态、{v['distinct_pair_pose_checks']}个去重零件—姿态检查通过；原0.01mm³相交体积阈值保留，同时另行检查实际表面净距。颈部与原后壳最小已查间隙{ygap:.3f}mm；三件候选与头壳的最小值{gap:.3f}mm出现在压板附近。过渡侧壁内外面顶点和三角形中心的最近面距离采样最小{wall:.3f}mm，不是全局最小壁厚证明或承载资格。

压板侧装、支撑与压板成对落座、轴承竖直装入、两枚螺钉和2AF工具局部路径通过；这些检查不含新增软线，也未解决旧反力夹初装。防脱仍保留0.4mm名义游隙，0.39/0.41/1.0mm抬升采样得到预期自由/止挡关系，不是预紧或最终舵盘叠层合格结论。

[NSK6806ZZ来源]({url})与[存档清单](sources/manifest.json)：目录质量24g，原6804ZZ17g，轴承增加7g；没有据此声称整机重量增加7g。价格、库存、精密滚道CAD及实际配合未确认；不放行采购或制造。

仍需：真实接口端部、线材/FFC、固定和应力释放、完整带线装配、反力夹初装、供应商制作图、质量/驱动预算。PA12工艺、承载、磨损、线缆寿命等实物验证单列NOT_TESTED。

可编辑文件：[C5_review.blend](C5_review.blend)。检查：[构建](C5_build.json)、[实体与装入](C5_verification.json)、[净距与材料](C5_material.json)、[摘要](C5_review.json)。

工具：Blender5.2.2 LTS d13f752e3b9c，项目manifold；Python3.12.14。实际运行命令为同目录 build_candidate_v5.py、verify_candidate_v5.py、check_profile_material_v5.py、render_v5.py（Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python）；plot_v5.py 和 publish_v5.py 用项目Python运行。日志均保存在本目录。
'''
(HERE/'C5_README.md').write_text(body)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · C5颈部通道候选</title>
<style>body{{margin:0;background:#f3f5f2;color:#24392f;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 22px 70px}}h1{{font-size:29px;line-height:1.4}}a{{color:#176e52}}figure{{margin:25px 0;background:white;border:1px solid #cbd7ce}}img{{display:block;width:100%}}figcaption{{padding:14px}}.note{{background:#fff0d9;padding:18px}}td,th{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #cbd7ce}}table{{border-collapse:collapse;width:100%;background:white}}</style><main>
<nav><a href="../index.html">到货前待办</a> · <a href="C4_status.html">C4未通过记录</a></nav>
<h1>连续颈部通道已通过局部检查，等待结构方案确认</h1>
<p class="note"><b>这是独立候选，主模型仍为M1.48。</b> 需要更换轴承型号并调整三件现有打印件；完整线束尚未完成，未放行采购或制造。</p>
<table><tr><th>方案取舍</th><th>具体变化</th></tr><tr><td>轴承</td><td>20×32×7 → 30×42×7（NSK6806ZZ目录边界）。轴承目录质量增加7g；整机质量仍需重算，价格及库存未确认。</td></tr>
<tr><td>支撑</td><td>调整固定桥、旋转支撑、防脱压板三件，不新增打印件或紧固件。原反力孔壁、承力连接、上部舵机座保留。</td></tr>
<tr><td>外观与位置</td><td>原头壳、屏幕、相机、舵机和压板紧固件位置保持，保留正常yaw±60° / pitch−20°～+25°。</td></tr>
<tr><td>局部数字结果</td><td>130姿态；最小已查头壳间隙{gap:.3f}mm；过渡侧壁采样约{wall:.3f}mm；11线局部与无软线刚体装入检查通过。</td></tr></table>
<figure><a href="C5_supports.png"><img src="C5_supports.png" alt="C5三件支撑与局部导线候选"></a><figcaption>候选支撑；为观察隐藏头壳和屏幕等零件，检查仍包括它们。橙色为局部线材空间样本，尚未连接完整端口。</figcaption></figure>
<figure><a href="C5_sections.png"><img src="C5_sections.png" alt="当前主模型与C4、C5在仰头25度的实际截面对比"></a><figcaption>左：当前主模型；中：此前C4；右：C5。右下连续过渡解决了原薄壁与局部壳体接触；这是有限姿态和采样检查。</figcaption></figure>
<figure><a href="C5_neck.png"><img src="C5_neck.png" alt="隐藏固定桥和压板后的旋转颈部细节"></a><figcaption>隐藏固定桥和压板后的细节。螺钉/嵌件因此悬空显示；不是最终装配状态。</figcaption></figure>
<h2>还没有完成的内容</h2><p>真实接口端部、实际线材与FFC、固定和应力释放、完整带线装配、供应商制作图及反力夹初装仍未完成。七根较粗线只是空间样本；这些局部几何通过不能证明实际线缆会自然保持数学路线。PA12强度、实际配合与磨损寿命需实物验证。</p>
<p><a href="C5_review.blend">可编辑Blender候选</a> · <a href="C5_README.md">完整范围与来源</a> · <a href="C5_review.json">检查摘要</a> · <a href="C5_material.json">间隙与壁厚采样</a> · <a href="C5_verification.json">装入与运动</a> · <a href="../work_status.json">完整剩余清单</a></p>
<p>PROTOTYPE / UNVALIDATED · 需要用户确认结构变更后才能应用。</p></main></html>'''
(HERE/'C5_index.html').write_text(page)
statuspath=BASE/'work_status.json';status=json.loads(statuspath.read_text());status['updated_utc']=review['utc']
status['neck_bearing_capacity_M1_48_C5']=review
status['neck_bearing_capacity_M1_48_C4']['followup']='neck_bearing_capacity_M1_48/C5_index.html'
for row in status['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='neck_bearing_capacity_M1_48/C5_index.html',latest_capacity_evidence='neck_bearing_capacity_M1_48/C5_index.html',latest_capacity_detail=detail)
statuspath.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
for name,link in [('index.html','C5_index.html'),('C4_status.html','C5_index.html'),('../whole_head_harness_M1_48/index.html','../neck_bearing_capacity_M1_48/C5_index.html')]:
    f=HERE/name;text=f.read_text();text=re.sub(r'<aside id="C5-followup".*?</aside>','',text,flags=re.S)
    note='<aside id="C5-followup" class="note"><b>最新C5候选：</b>局部11线、运动净距与过渡壁厚检查已通过，尚待结构确认；完整线束仍未完成。<a href="'+link+'">查看候选与检查范围</a>。下方保留之前研究。</aside>'
    f.write_text(text.replace('<main>','<main>'+note,1))
f=BASE/'index.html';text=f.read_text()
note='<aside id="larger-neck-capacity-update" class="notice"><b>C5候选的颈部净距和过渡薄壁已修正。</b> '+detail+' <a href="neck_bearing_capacity_M1_48/C5_index.html">查看具体候选</a>。仍剩5类到货前工作。</aside>'
text,n=re.subn(r'<aside id="larger-neck-capacity-update".*?</aside>',note,text,count=1,flags=re.S);assert n==1
text,n=re.subn(r'<tr><td>完整线束</td>.*?</tr>','<tr><td>完整线束</td><td>BLOCKED<br>机械＋硬件线材输入</td><td>'+detail+' <a href="neck_bearing_capacity_M1_48/C5_index.html">最新依据</a></td></tr>',text,count=1,flags=re.S);assert n==1
f.write_text(text)
print('C5_PUBLISHED candidate PASS; whole harness BLOCKED; approval PENDING_USER')
