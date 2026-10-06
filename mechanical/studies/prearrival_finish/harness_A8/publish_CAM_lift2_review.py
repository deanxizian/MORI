"""Publish the useful board descent result and the real forming blocker."""
from pathlib import Path
import hashlib,json,shutil,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3];OUT=A8/'cam_wire_forming/lifted_end2'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=read(OUT/'board_descent_continuous.json');p=read(OUT/'packing_screen.json');w=read(OUT/'packing_collision_witness.json')
i=read(OUT/'continuous_interrupted.json');v=read(OUT/'render_manifest.json')
seq=read(OUT/'contact_refined_forming/screen.json');seqvis=read(OUT/'contact_refined_forming/render_manifest.json')
continuous=read(OUT/'contact_refined_forming/continuous/screen.json')
distance=read(OUT/'contact_refined_forming/continuous/first_failure_segment_distance.json')
conflictvis=read(OUT/'contact_refined_forming/continuous/render_manifest.json')
corridor=read(OUT/'contact_refined_forming/return_corridor/screen.json')
corridor_cont=read(OUT/'contact_refined_forming/return_corridor/continuous/screen.json')
critical=read(OUT/'contact_refined_forming/critical_return_continuous/screen.json')
current_file=OUT/'contact_refined_forming/negative_complete/screen.json'
current=read(current_file)
newvis=read(OUT/'contact_refined_forming/negative_return_branch/render_manifest.json')
housing=read(OUT/'contact_refined_forming/housing_approach/screen.json')
housingvis=read(OUT/'contact_refined_forming/housing_approach/render_manifest.json')
rootdir=OUT/'contact_refined_forming/root_tie_access'
roottool=read(rootdir/'screen.json');rootvis=read(rootdir/'render_manifest.json');rootfeed=read(rootdir/'contact_feed.json')
seatingdir=OUT/'contact_refined_forming/root_seating/aligned_tails'
seating=read(seatingdir/'verification.json');seatingvis=read(seatingdir/'render_manifest.json')
assert seating['status']==seatingvis['status']=='PASS' and seating['continuous_intervals']==256
assert seating['script_sha256']==sha(A8/'verify_CAM_root_seating.py')
assert seating['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
for filename,digest in seating['source_files'].items():assert sha(ROOT/filename)==digest,filename
assert roottool['status']==rootvis['status']=='PASS' and rootfeed['status']=='BLOCKED'
assert roottool['source_forming_sha256']==rootfeed['source_forming_sha256']==sha(current_file)
assert rootvis['source_screen_sha256']==sha(rootdir/'screen.json')
assert rootvis['physical_source_objects_preserved']==214
for row in rootvis['images']:assert row['sha256']==sha(rootdir/row['file'])
assert housing['status']==housingvis['status']=='PASS'
assert housing['source_forming_sha256']==sha(current_file)
assert housingvis['source_screen_sha256']==sha(OUT/'contact_refined_forming/housing_approach/screen.json')
assert housing['contact_insertion_process']=='NOT_TESTED' and housing['terminal_cavity_and_lance_fit']=='BLOCKED'
for row in housingvis['images']:assert row['sha256']==sha(OUT/'contact_refined_forming/housing_approach'/row['file'])
assert current['status']=='PASS' and current['complete_four_wire_forming_coverage']
assert current['script_sha256']==sha(A8/'verify_CAM_complete_forming.py')
assert current['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
for name,digest in current['source_files'].items():assert sha(ROOT/name)==digest,name
assert newvis['physical_source_objects_preserved']==214
for row in newvis['images']:assert row['sha256']==sha(OUT/'contact_refined_forming/negative_return_branch'/row['file'])
assert continuous['status']=='BLOCKED' and not continuous['complete_coverage']
assert distance['real_intersection']=='FAIL' and distance['closest']['polyline_distance_mm']+distance['closest']['smooth_curve_error_sum_mm']+distance['closest']['numeric_guard_mm']<.6604
assert corridor['status']=='PASS' and corridor_cont['status']=='BLOCKED'
assert not critical['complete_last_wire_coverage'] and not critical['main_applied']
for report,script in [(continuous,'check_CAM_sequential_continuous.py'),(distance,'diagnose_CAM_continuous_margin.py'),
    (conflictvis,'render_CAM_continuous_return_conflict.py'),(corridor,'refine_CAM_return_corridor.py'),
    (corridor_cont,'check_CAM_return_corridor_continuous.py'),(critical,'plan_CAM_critical_return_continuous.py')]:
    assert report['script_sha256']==sha(A8/script) and report['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
for row in conflictvis['images']:assert row['sha256']==sha(OUT/'contact_refined_forming/continuous'/row['file'])
assert conflictvis['physical_source_objects_preserved']==214
outer=read(OUT/'outer_first_forming/screen.json');outercontacts=read(OUT/'outer_first_forming/contacts.json')
assert seq['status']==outer['status']=='PASS' and seq['wire_order']==[3,2,1,0]
assert len(seq['all_contact_positions'])==644 and all(x['status']=='PASS' for x in seq['all_contact_positions'])
assert seq['generic_0_3mm_contact_packing']=='BLOCKED' and seq['continuous_motion']=='NOT_TESTED'
assert outercontacts['nominal_nonpenetration']=='BLOCKED'
for data,script in [(seq,'refine_CAM_outer_contact_path.py'),(seqvis,'render_CAM_contact_refined_forming.py'),
                    (outer,'plan_CAM_outer_first_forming.py'),(outercontacts,'check_CAM_outer_first_contacts.py')]:
    assert data['script_sha256']==sha(A8/script) and data['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
    assert not data['main_applied'] and data['whole_harness']=='BLOCKED'
for row in seqvis['images']:assert row['sha256']==sha(OUT/'contact_refined_forming'/row['file'])
assert seqvis['physical_source_objects_preserved']==214
trials={name:read(OUT/name/'screen.json') for name in ['apex_revision','side_turn','sequential_bends','one_wire_at_a_time']}
assert b['status']=='PASS' and b['complete_coverage'] and not b['unproved_intervals'] and not b['error']
assert p['status']==p['wire_packing_status']=='BLOCKED' and w['status']=='FAIL'
assert w['upper_bound_actual_centre_distance_mm']<w['combined_radii_mm']
assert all(d['status']=='BLOCKED' and d.get('selected',d.get('selected_amplitude_mm')) is None for d in trials.values())
assert not i['complete_coverage'] and i['status']=='NOT_TESTED'
for d in [b,p,w,i,v,*trials.values()]:
    assert d['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend') and not d['main_applied']
for filename,script in [('board_descent_continuous.json','check_CAM_lift2_board_descent.py'),
                       ('packing_screen.json','check_CAM_lift2_forming_packing.py'),
                       ('render_manifest.json','render_CAM_lift2_review.py')]:
    assert read(OUT/filename)['script_sha256']==sha(A8/script)
for row in v['images']:assert row['sha256']==sha(OUT/row['file'])
assert v['physical_source_objects_preserved']==214
for source,target in [('/tmp/mori_lift2_apex_revision.log','apex_revision/screen.log'),
    ('/tmp/mori_lift2_side_turn.log','side_turn/screen.log'),('/tmp/mori_lift2_sequential_bends.log','sequential_bends/screen.log'),
    ('/tmp/mori_lift2_one_wire.log','one_wire_at_a_time/screen.log'),('/tmp/mori_lift2_render.log','render.log')]:
    if Path(source).is_file():shutil.copyfile(source,OUT/target)
    else:assert (OUT/target).is_file(),f'Missing preserved execution log: {OUT/target}'
count=len(b['passed_intervals']);sep=w['upper_bound_actual_centre_distance_mm'];diam=w['combined_radii_mm']
table='\n'.join(f'| {label} | {len(trials[name]["trials"])} | BLOCKED；保留首个失败位置 |' for name,label in [
    ('apex_revision','提高临时回环'),('side_turn','减小抬高或侧转整组线'),('sequential_bends','先弯尾部两个90°弯，再弯主回环'),('one_wire_at_a_time','其余线保留，逐根弯线')])
md=f'''# CAM临时抬高2mm：板卡下降已核查，弯线顺序仍需修正

本页更新上一版“有限位置通过”的结论。主模型M1.47、STL、PCB和正式装配动画均未改；这是未采用的线束工序研究，不是供应商裁线图或制造放行。

## 已完成：板卡从8mm下降到2mm

保持插头与四线在最终位置上方2mm，CAM板从上方8mm降到2mm。对当时的结构件、固定插头和四线，用{count}个带运动距离上界的区间覆盖整个6mm行程，结果PASS。各区间首尾连续，不是只检查若干截图。

![板卡在上方8mm](board_at8.png)
![板卡降到上方2mm](board_at2.png)

两张图中插头和线的位置保持不动，只有绿色板卡下降。图中金黄色座与线束通道仍属于已有独立候选；颜色用于区分几何对象，不代表采购配色或电气针序。

先前的距离上界算法无法判定插头与板上相邻平面几乎贴合的情况。现用**凸插头沿直线运动的完整扫掠体**直接与原板卡实体求交，未删除接合面，也没有缩小插头；名义相交体积为0。该处约0.00000057mm的模型面间距不能解释为实物装配余量。

这里只排除插头与其配对UART插座的预期接合，导线对板卡的普通区域仍保留0.3mm裕量。CAM实际插座完整料号、插合深度、端子入壳及插入力仍未验证。后续2→0mm落座属于原0→6mm已查曲线的子区间；本页未据此声称整条工序完整。

## 新发现：弯线时会碰到上游另一根线

![两根线在弯曲途中相交](upstream_collision.png)

上图只显示两根相关导线，以免支架遮挡。青色为正在弯曲的线0，橙色为上游线1；两根线都保留原0.6604mm最大外径。

在原9mm抬高、2mm自由端候选的成形参数0.8处，两条中心线的距离上界为**{sep:.6f}mm**，小于两线半径之和**{diam:.4f}mm**。因此这不是仅仅没留够0.3mm余量，而是当前名义线径模型确实相交。41位置线间检查在0.75、0.775、0.8、0.825附近均给出失败；完整线束不得标PASS。

发现这一确定障碍后，已停止只检查线对结构件的长时间连续计算，保留日志及停止原因。该计算没有覆盖全过程，状态NOT_TESTED，不能用已经算过的一部分区间支持完整路线通过。

## 已比较的临时动作

| 路线类别 | 本轮候选数 | 结果 |
|---|---:|---|
{table}

提高回环会让端子进入俯仰舵机；侧转和逐根操作的既定路径仍有支架或线间冲突。以上是这些具体路线的失败记录，不能据此推断所有装配方法都不可行。没有为此给支架新增孔槽或缩小硬件。

散端子仍按[JST官方SH目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)尺寸跨度构造估算盒，真实压接外形并未得到认证。在1mm节距下，其0.8mm宽度只剩0.2mm名义间距，导线接近相邻端子的工序余量也未闭合；没有把这一点静默放宽为0.3mm通过。

## 后续工作

需要继续设计弯线的先后顺序及暂放位置，再把初次颈部穿线、端子入壳、扎带安装与已通过的板卡下降/落座步骤连成完整工序。其余七根跨关节线、USB、LCD排线、相机FPC和身体固定段仍在总待办中。没有新的结构变更需要本页代替用户确认。

[连续板卡下降](board_descent_continuous.json) · [线间筛查](packing_screen.json) · [确实相交的数值证据](packing_collision_witness.json) · [停止原因](continuous_interrupted.json) · [逐根弯线记录](one_wire_at_a_time/screen.json) · [独立Blender](review.blend) · [命令和版本](commands.json) · [交付清单](review_manifest.json)
'''
(OUT/'README.md').write_text(md)
sequence_md='''# 新进展：四线逐根弯线候选已找到

原来的同步弯线会与上游导线相交。改为按**几何槽位3→2→1→0**依次安装，并为最后一根线安排侧绕及临时抬高后，四段路径共644个检查位置通过线/结构筛查及名义散端子不相交检查。槽位数字和颜色仅标识几何位置，不替代电气针脚或供应商线色。

| 项目 | 当前结果 |
|---|---|
| 四段路径的节点及四分之一、中点、四分之三位置 | 每段161处，共644处；有限位置检查通过，尚非连续证明 |
| 普通导线对结构、其他导线；活动端子对结构 | 普通区域保留0.3mm筛查裕量；既有固定/落座接触区按原边界检查，不新增排除 |
| 全部散端子对四条自由线、上游过渡、身体线及其他端子 | 644处名义不相交检查通过；自身压接附近2mm局部区间按既有模型定义排除 |
| 静置导线和端子对结构 | 4根×初始/最终两态，共8项通过 |
| 相邻散端子的通用0.3mm裕量 | 仍未通过：1mm节距减0.8mm目录宽度只余0.2mm；没有把它改写为0.3mm |
| 连续过程、真实压接外形与端子入壳 | 未完成；不得据此放行供应商裁线或整机装配 |

![初始状态：四根线尾向上](contact_refined_forming/start.png)

初始状态假定四根线已穿过颈部，并在现有独立固定座候选处接续。上图中的初始穿入、暂放与固定仍需连成完整工序；不能从这张图推定已经能操作。显示支架、CAM板和头壳尚未安装。

![最后一根线暂时侧绕并抬高](contact_refined_forming/last_wire_sideways.png)

前三根保持已经摆好的位置，最后一根青色线在这个姿态暂时侧转48°，抬高参数为10.5mm，随后归位。所有线和端子始终参与检查，没有暂时删除妨碍装配的线。端子仍是JST目录尺寸跨度构造的估算盒，未经实物或完整压接CAD确认。

![四根线到达临时落座状态](contact_refined_forming/all_four_positioned.png)

四根线到达最终位置上方2mm的状态，线长、线径和正式机器人实体不变。该状态与下文已检查的CAM板8→2mm下降衔接；端子装入胶壳、扎带安装、连续弯线、合壳及其余七根跨关节线等仍未完成。

本轮先保留了一个只通过导线筛查的候选。补入端子后，在最后一根线参数0.825处未通过与三根已摆好导线的不相交界限；随后把该处抬高参数7.5→10.5mm，并重新检查四段共644个位置。这个修正只改变临时装配动作，不改变最终线形或机器人零件。

[修正后的完整位置记录](contact_refined_forming/screen.json) · [独立Blender](contact_refined_forming/review.blend) · [图像来源](contact_refined_forming/render_manifest.json) · [修正前端子问题](outer_first_forming/contacts.json) · [反向顺序搜索](outer_first_forming/screen.json)

以下保留之前的同步路线失败和已完成的板卡下降证明，二者不覆盖或替代本轮新路线的未完成检查。

'''
latest_md=f'''# 连续检查更新：原逐根路线仍有中途相交

此前644处有限位置筛查通过的记录保留，但不能用于放行完整装配。连续检查在最后一根线参数0.846875、侧角约6°时发现遗漏；对相关线段重新计算后，中心线距离约{distance['closest']['polyline_distance_mm']:.6f}mm，小于两线半径之和0.6604mm，名义导线包络确实相交。

![原逐根路线在两次采样之间相交](contact_refined_forming/continuous/conflict_closeup.png)

上图隔离两根相关导线，保留真实模型线径，没有把导线加粗。完整结构及四条线仍参加数值检查。原路线连续审查只通过{len(continuous['passed_intervals'])}个局部区间后停止，整体BLOCKED；它不是仅差实物验证。

随后加密到0.0025参数步长的局部修正，虽然离散位置再次通过，连接动作依然未通过连续检查。因此后续搜索改为**每段动作先通过连续界限，再接受这一段**。最新关键中段搜索为{critical['status']}，范围只涵盖最后一根线的0.75→0.875；完整四线成形、初始穿线、端子入壳与扎带仍未闭合。通用0.3mm端子操作裕量仍BLOCKED，主模型M1.47未改。

[原路线连续记录](contact_refined_forming/continuous/screen.json) · [相交数值复核](contact_refined_forming/continuous/first_failure_segment_distance.json) · [整机上下文图](contact_refined_forming/continuous/conflict_context.png) · [独立Blender](contact_refined_forming/continuous/conflict_review.blend) · [加密局部路线失败](contact_refined_forming/return_corridor/continuous/screen.json) · [关键中段连续搜索](contact_refined_forming/critical_return_continuous/screen.json)

下面的644位置PASS属于此前有限筛查，已被本次连续失败限定，不能理解为当前完整路线通过。

'''
current_md=f'''# 当前结果：四根CAM线的规定成形动作连续通过

最后一根线改为从负侧小角度绕开，再逐步回正；原来从48°直接归位的相交路线保留为失败记录。按几何槽位3→2→1→0操作，四段动作共{current['continuous_interval_count']}个自适应区间完整覆盖，每段起点到终点均已检查，8个边界姿态与下一步骤保留的导线和端子一致。

| 项目 | 当前结果 |
|---|---|
| 四根线各自从初始竖直姿态弯至临时落座姿态 | PASS；四段连续覆盖0→1，固定的其他三根线、上游线和身体段始终保留 |
| 普通线间及线对结构 | 保持0.6604mm线径与0.3mm筛查裕量；既有功能接触区按原定义检查 |
| 目录尺寸重建的散端子 | 名义不相交；不是实物压接轮廓认证，也没有声明通用0.3mm端子操作裕量通过 |
| CAM板8→2mm下降 | 先前的{count}个连续区间检查保持PASS |
| 颈部穿线到初始姿态、端子入壳、扎带操作 | 尚未连成完整工序 |
| 其他七根跨关节线、排线及最终供应商裁线图 | 未完成 |

![最后一根从负侧绕行](contact_refined_forming/negative_return_branch/side6.png)
![逐步回正](contact_refined_forming/negative_return_branch/side3.png)
![负侧回到零角度](contact_refined_forming/negative_return_branch/returned.png)

三张图分别是最后一根线的参数0.8025、0.825、0.875；最后一张仍在成形途中。其后0.875→1的1032个区间也已通过。颜色和槽位仅作几何标识，不替代供应商针脚图。真实线材回弹、操作力和端子压接仍未验证。

主模型M1.47、STL和正式装配动画未修改。这里只完成独立候选的四线成形子步骤，**完整线束仍为BLOCKED**，没有制造放行。

[完整四段路径与区间覆盖](contact_refined_forming/negative_complete/screen.json) · [八个边界状态复核](contact_refined_forming/negative_complete/junctions.json) · [前三根连续记录](contact_refined_forming/first_three_continuous/screen.json) · [最后一根连续记录](contact_refined_forming/negative_tail/screen.json) · [归位阶段Blender](contact_refined_forming/negative_return_branch/review.blend)

## 下一步的外部空间已检查

空胶壳从上方8mm沿轴线接近，完整凸扫掠体对{len(housing['rigid_checks'])}个当时结构实体及12组非接合导线检查通过。未装CAM板、显示支架和头壳；四颗配套端子及各自最后2mm压接邻域不属于这项外部接近检查。

![空胶壳在上方](contact_refined_forming/housing_approach/initial.png)
![胶壳外形分配到位](contact_refined_forming/housing_approach/final.png)

头托在图中半透明以便查看内部，完整实体仍参与计算。橙色盒子只是胶壳目录外形。它到位不代表端子已经进入或锁住：针腔、锁舌、朝向、插入力和抓持均未闭合。[接近检查](contact_refined_forming/housing_approach/screen.json) · [资料及范围说明](contact_refined_forming/housing_approach/SOURCE_NOTE.md) · [独立Blender](contact_refined_forming/housing_approach/review.blend)

以下为保留的旧路线、失败记录和此前子步骤，不能用旧路线状态覆盖上方新路线，也不能用新的局部PASS覆盖未完成的完整装配。

'''
root_md='''## 根部扎带的工具空间与装入顺序

已把剪尾工具检查扩展到当前完整成形阶段：219 个结构实体、12 段导线、4 个散端子均参与。原 0° 方向的完整 60 mm 直线接近名义通过，朝外 110 mm 扎带尾操作空间也通过；工具与扎带头、带身只有约 0.25 mm 间隔，通用 0.3 mm 余量仍为 BLOCKED。真实钳口、手部和剪断动作未验证。

同时排除了“先收紧扎带，再沿四条竖直轴穿端子”的候选：四个目录端子包络均碰到打印座和带身。必须先完成导线放入，再收紧；仅松开扎带还没有证明能避开打印座。完整初次穿线与收紧过程继续设计，未据此修改结构。

[局部图、全部记录与证据范围](contact_refined_forming/root_tie_access/README.md) · [工具空间](contact_refined_forming/root_tie_access/screen.json) · [收紧后穿入失败记录](contact_refined_forming/root_tie_access/contact_feed.json)

'''
current_md=current_md.replace('以下为保留的旧路线',root_md+'以下为保留的旧路线',1)
seating_md='''## 新补齐：先放入导线，再安装根部扎带

四根绝缘导线从固定座前方 1.5 mm 处移入槽内，根部暂时抬高最多约 0.86 mm。下方端点、线径及总线长保持，21 个位置复核和 256 个连续区间均通过。上部转弯段保持对齐，只用原有末端直线段补偿长度变化；剩余直线段全程保守下界大于 5.2 mm。

![入座前](contact_refined_forming/root_seating/aligned_tails/before_seating.png)
![导线入座](contact_refined_forming/root_seating/aligned_tails/seated.png)

这一步尚未装根部扎带。初次端子穿入并到达起点、扎带穿绕收紧及端子入壳仍未完成。主模型未改，完整线束仍为 BLOCKED。[局部说明](contact_refined_forming/root_seating/aligned_tails/README.md) · [连续记录](contact_refined_forming/root_seating/aligned_tails/continuous.json) · [独立复核](contact_refined_forming/root_seating/aligned_tails/verification.json)

另从 JST 官方 LBT 目录找到同料号端子的更细图面。其下方锁止弹片不包含在 1.35 mm 的尺寸线内；已有方盒检查不能视为完整真实端子已通过。[新增原图与尺寸范围说明](../../ssh_catalogue_addendum/README.md)。

'''
current_md=current_md.replace('完整初次穿线与收紧过程继续设计，未据此修改结构。','下方已补齐绝缘导线的局部入座动作；完整初次穿线与收紧过程仍需继续设计，未据此修改结构。')
current_md=current_md.replace('以下为保留的旧路线',seating_md+'以下为保留的旧路线',1)
current_md+='\n\n[最新资料与初次穿线诊断](../../supplier_source_update/index.html)：新增 JST APSH 同料号端子细节图及 M5Stack 官方摇臂参考。同样较大端子预留尺寸下，上部穿入1228、回位256、入座256、四段弯线1735个连续区间通过；后续弯线调整了两处临时动作，见[尺寸统一复核](contact_refined_forming/root_seating/large_contact_downstream/index.html)。身体侧每根约140–162mm原有材料的暂存过程、真实端子、扎带和其他线仍未完成。\n\n'
(OUT/'README.md').write_text(current_md+latest_md+sequence_md+md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM弯线与板卡下降</title><style>
body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f4f6f5;color:#253b3d;max-width:1050px;margin:28px auto;padding:0 24px 60px}}a{{color:#096a74}}h1{{font-size:30px}}.note{{background:#fff0d9;padding:18px;border-radius:10px}}.good{{background:#e5f1e9;padding:18px;border-radius:10px}}img{{width:100%;border-radius:8px}}figure{{margin:20px 0}}figcaption{{font-size:14px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:700px){{.pair{{display:block}}}}</style>
<p><a href="../terminals/index.html">← 端子与前一版连续检查</a> · <a href="../../../index.html">当前待办</a></p>
<h1>板卡下降已通过，弯线顺序仍需修正</h1>
<p class="note">新加入上游导线后，确认原候选在弯线途中与另一根线相交。完整工序仍为BLOCKED，主模型M1.47未改。以下PASS只对应板卡从8mm下降到2mm这一子步骤。</p>
<h2>已完成：固定插头，板卡下降6mm</h2><p class="good">{count}个区间覆盖整个行程。导线、当时已装结构件和插头均参与检查；不是把25个截图当成连续证明。</p>
<div class="pair"><figure><img src="board_at8.png" alt="CAM板位于上方8毫米"><figcaption>开始：CAM板在+8mm，插头与导线在+2mm。</figcaption></figure><figure><img src="board_at2.png" alt="CAM板下降到上方2毫米"><figcaption>结束：CAM板到+2mm，插头和导线保持原位。</figcaption></figure></div>
<p>贴合面的检查使用完整凸插头直线扫掠体，没有删面或缩小插头。几乎为零的名义面间距不是制造余量；真实插座识别、端子入壳和插合深度仍待确认。</p>
<h2>确认的障碍：两根导线在途中相交</h2><figure><img src="upstream_collision.png" alt="青色弯曲导线与橙色上游导线相交"><figcaption>隔离显示相关两根线：参数0.8，中心距离上界{sep:.6f}mm，小于两线半径之和{diam:.4f}mm。并非只有安全余量不足。</figcaption></figure>
<p>提高回环、侧转整组线、先折尾段、逐根弯线的本轮具体候选仍有冲突，失败记录全部保留。已经停止对原失败路线继续计算只有结构件参与的连续检查；其全过程未覆盖，不能声称通过。</p>
<p>下一步继续处理各根线的临时摆放及完整装配顺序，不为这些失败直接给支架开孔。其余七根跨关节线和排线等仍需完成，最终裁线图尚未发布。</p>
<p><a href="README.md">完整说明与候选表</a> · <a href="board_descent_continuous.json">连续下降结果</a> · <a href="packing_collision_witness.json">相交证据</a> · <a href="one_wire_at_a_time/screen.json">逐根弯线记录</a> · <a href="review.blend">独立Blender</a> · <a href="commands.json">命令</a> · <a href="review_manifest.json">交付清单</a></p></html>'''
sequence_html='''<h1>找到逐根弯线候选，完整工序仍待核查</h1>
<p class="good">按几何槽位3→2→1→0逐根操作，最后一根先侧绕、临时抬高再归位。四段路径共644个检查位置已通过线/结构筛查及名义端子不相交检查；最终线形和M1.47主模型保持不变。</p>
<p class="note">这是有限位置证据。连续弯线、真实端子入壳、扎带安装和完整装配尚未完成。相邻目录端子的0.2mm名义间隔也没有被改写为通用0.3mm裕量通过；尚无供应商裁线图或制造放行。</p>
<figure><img src="contact_refined_forming/start.png" alt="四根导线和名义端子的初始竖直状态"><figcaption>起始假定：四根线已穿过颈部并接续；初始穿入、暂放、固定仍需补齐。</figcaption></figure>
<div class="pair"><figure><img src="contact_refined_forming/last_wire_sideways.png" alt="青色的最后一根导线绕开已放好的另外三根线"><figcaption>最后一根暂时侧绕48°并抬高，其他三根保持在位。</figcaption></figure><figure><img src="contact_refined_forming/all_four_positioned.png" alt="四根线均到达最终位置上方2毫米"><figcaption>四根线均到+2mm状态；不代表端子入壳和紧固已完成。</figcaption></figure></div>
<p>只检查导线时曾得到一条不完整的候选；加入全部散端子后发现局部问题，已调整最后一根线的临时抬高量并重查644处。各类早期失败保留，未改变线径、零件或孔位。</p>
<p><a href="contact_refined_forming/screen.json">新路径与检查记录</a> · <a href="contact_refined_forming/review.blend">独立Blender</a> · <a href="outer_first_forming/contacts.json">修正前端子问题</a> · <a href="README.md">完整证据边界</a></p><hr>
<h2>此前完成和保留的问题</h2>'''
html=html.replace('<h1>板卡下降已通过，弯线顺序仍需修正</h1>',sequence_html+'<h2>板卡下降通过；原同步弯线失败</h2>')
html=html.replace('下一步继续处理各根线的临时摆放及完整装配顺序，不为这些失败直接给支架开孔。','上方新顺序补齐了有限位置候选，接下来仍需连续过程及完整装配核查，不为早期失败直接给支架开孔。')
latest_html=f'''<h1>连续检查发现中途相交，逐根路线尚未闭合</h1>
<p class="note">之前644个位置通过的候选，在最后一根线归位途中仍会与上游另一根线相交。中心线距离约{distance['closest']['polyline_distance_mm']:.6f}mm，小于两线半径之和0.6604mm。完整工序仍为BLOCKED；主模型未改。</p>
<div class="pair"><figure><img src="contact_refined_forming/continuous/conflict_context.png" alt="保持四根导线与头部结构的中间姿态"><figcaption>遗漏位置：最后一根线归位途中，参数0.846875。</figcaption></figure><figure><img src="contact_refined_forming/continuous/conflict_closeup.png" alt="青色活动线穿过橙色上游线"><figcaption>两线局部隔离显示，线径保持0.6604mm；相交已作线段距离复核。</figcaption></figure></div>
<p>加密后的局部路线也在连接动作中遇到问题。后续改为每段动作先通过连续界限再接受；最新关键中段搜索状态{critical['status']}，只对应最后一根线的0.75→0.875，不能当成完整四线装配通过。端子入壳、初始穿线、扎带与其他线路仍需完成。</p>
<p><a href="contact_refined_forming/continuous/first_failure_segment_distance.json">相交证据</a> · <a href="contact_refined_forming/continuous/screen.json">连续失败记录</a> · <a href="contact_refined_forming/return_corridor/continuous/screen.json">加密局部路线检查</a> · <a href="contact_refined_forming/critical_return_continuous/screen.json">关键中段连续搜索</a> · <a href="README.md">完整说明</a></p><hr><h2>此前有限筛查记录</h2>'''
html=html.replace('<h1>找到逐根弯线候选，完整工序仍待核查</h1>',latest_html+'<h2>旧候选的644个有限位置</h2>')
current_html=f'''<h1>四根CAM线的规定成形动作已连续通过</h1>
<p class="good">最后一根改从负侧小角度绕开，再逐步回正。四段动作共{current['continuous_interval_count']}个自适应区间覆盖全过程，8个步骤边界与保留的线和端子一致。其余导线始终在场，线径和机器人零件未改。</p>
<p class="note">通过的是从假定初始姿态到临时落座姿态的几何子步骤。颈部初次穿线、端子入壳、扎带操作、其他七根活动线与排线仍未连成完整工序；完整线束仍为BLOCKED，尚无最终裁线图。端子是目录尺寸重建包络，实物未验证。</p>
<div class="pair"><figure><img src="contact_refined_forming/negative_return_branch/side6.png" alt="最后一根青色线从负侧绕开"><figcaption>参数0.8025：从负侧6°绕开已放好的三根线。</figcaption></figure><figure><img src="contact_refined_forming/negative_return_branch/side3.png" alt="最后一根线逐步回正"><figcaption>参数0.825：逐步回正至负侧3°。</figcaption></figure></div>
<figure><img src="contact_refined_forming/negative_return_branch/returned.png" alt="最后一根线回到零侧转角度，仍在弯曲途中"><figcaption>参数0.875：侧转角归零，仍在成形途中；后续到1.0的1032个区间也已通过。</figcaption></figure>
<p>普通线间及线对结构保留0.3mm裕量。裸端子只证明名义不相交，通用0.3mm操作裕量未闭合。板卡8→2mm下降的既有{count}个连续区间保持通过。主模型M1.47、STL与正式动画未改。</p>
<p><a href="contact_refined_forming/negative_complete/screen.json">完整四段路径与覆盖</a> · <a href="contact_refined_forming/negative_complete/junctions.json">步骤衔接检查</a> · <a href="contact_refined_forming/first_three_continuous/screen.json">前三根连续记录</a> · <a href="contact_refined_forming/negative_tail/screen.json">最后一根连续记录</a> · <a href="contact_refined_forming/negative_return_branch/review.blend">归位阶段Blender</a> · <a href="README.md">完整说明</a></p>
<h2>空胶壳的外部接近空间已检查</h2>
<p>空胶壳从上方8mm沿轴线接近，完整扫掠体对{len(housing['rigid_checks'])}个当时结构实体及12组非接合导线检查通过。图中头托半透明仅方便查看，完整实体仍参与计算。配套端子及其最后2mm压接邻域不在这项外部空间证明内；针腔、锁舌和实际装壳操作仍未验证。</p>
<div class="pair"><figure><img src="contact_refined_forming/housing_approach/initial.png" alt="橙色胶壳外形分配在导线端子上方"><figcaption>空胶壳从上方接近。图中橙色只是目录外形分配。</figcaption></figure><figure><img src="contact_refined_forming/housing_approach/final.png" alt="胶壳外形分配接近最终位置，内部配合未验证"><figcaption>外形分配到位；不代表端子已锁住或完成电气装配。</figcaption></figure></div>
<p><a href="contact_refined_forming/housing_approach/screen.json">外部接近检查</a> · <a href="contact_refined_forming/housing_approach/SOURCE_NOTE.md">资料与范围说明</a> · <a href="contact_refined_forming/housing_approach/review.blend">独立Blender</a></p>
<details><summary>查看旧路线的碰撞、搜索记录及此前子步骤</summary>'''
root_html='''<h2>根部扎带：剪尾空间已补查，初次装入仍需完成</h2>
<p>219 个结构实体、12 段导线和 4 个散端子均参与检查。工具从上方直线接近 60 mm、扎带尾朝外 110 mm 的空间分配名义通过；工具与扎带头及带身约 0.25 mm 的间隔没有达到通用 0.3 mm 余量。工具仅为目录尺寸方盒，实际钳口、抓持和剪断未验证。</p>
<div class="pair"><figure><img src="contact_refined_forming/root_tie_access/complete_tool.png" alt="完整剪尾工具与四根未成形线尾"><figcaption>绿色：工具；橙色：扎带尾操作空间。计算使用完整实体。</figcaption></figure><figure><img src="contact_refined_forming/root_tie_access/root_detail.png" alt="根部扎带与剪尾工具局部"><figcaption>剪尾工具可名义接近，不能据此宣称扎带已能安装或收紧。</figcaption></figure></div>
<p class="note">不能先收紧再沿所查竖直轴穿端子：四个目录端子包络都碰到打印座和带身。下一步需补齐扎带松开时的穿入、暂放和落座路线；松开扎带本身还没有排除打印座阻挡。未为此修改主模型。</p>
<p><a href="contact_refined_forming/root_tie_access/README.md">完整说明</a> · <a href="contact_refined_forming/root_tie_access/screen.json">工具与尾部空间检查</a> · <a href="contact_refined_forming/root_tie_access/contact_feed.json">收紧后穿端子的失败记录</a> · <a href="contact_refined_forming/root_tie_access/review.blend">独立 Blender</a></p>'''
current_html=current_html.replace('<details><summary>',root_html+'<details><summary>',1)
seating_html='''<section id="root-seating"><h2>新补齐：四根导线先放入固定槽</h2>
<p class="good">扎带尚未安装时，四根线从前方 1.5 mm 移入槽内。21 个位置和 256 个连续区间均通过；下方端点、线径、总线长保持，末端剩余直线段全程大于 5.2 mm。</p>
<div class="pair"><figure><img src="contact_refined_forming/root_seating/aligned_tails/before_seating.png" alt="四根绝缘线位于固定槽前方，根部扎带尚未安装"><figcaption>入座前：根部暂时抬高约 0.86 mm。</figcaption></figure><figure><img src="contact_refined_forming/root_seating/aligned_tails/seated.png" alt="四根绝缘线移入固定槽，扎带仍未安装"><figcaption>入座后：恢复原有根部位置。</figcaption></figure></div>
<p>这只补齐了局部入座动作。初次穿线到达起点、扎带穿绕收紧、端子入壳和其他线路仍未完成；主模型未改。</p>
<p><a href="contact_refined_forming/root_seating/aligned_tails/README.md">范围与完整线尾图</a> · <a href="contact_refined_forming/root_seating/aligned_tails/continuous.json">连续记录</a> · <a href="contact_refined_forming/root_seating/aligned_tails/verification.json">独立复核</a></p>
<p class="note">新找到的同料号 JST 端子图显示，底部锁止弹片位于 1.35 mm 尺寸线之外。已有简化方盒检查不包括完整弹片；不能视为真实端子已通过。<a href="../../ssh_catalogue_addendum/README.md">官方原图与新增尺寸说明</a>。</p></section>'''
current_html=current_html.replace('下一步需补齐扎带松开时的穿入、暂放和落座路线；松开扎带本身还没有排除打印座阻挡。','下方已补齐未装扎带时的绝缘线局部入座动作；散端子初次穿入并到达该起点的路线，以及扎带穿绕收紧，仍未完成。')
current_html=current_html.replace('<details><summary>',seating_html+'<details><summary>',1)
current_html=current_html.replace('<details><summary>','<section class="note"><h2>最新：统一端子预留尺寸的连续检查</h2><p>新增 JST APSH 同料号端子细节图及 M5Stack 官方摇臂参考。同样较大端子预留尺寸下，穿入1228、回位256、入座256、四段弯线1735个连续区间通过；身体侧材料暂存、真实端子入壳和扎带仍未完成。<a href="contact_refined_forming/root_seating/large_contact_downstream/index.html">查看后续复核</a> · <a href="../../supplier_source_update/index.html">公开资料与来源</a>。</p></section><details><summary>',1)
html=html.replace('<h1>连续检查发现中途相交，逐根路线尚未闭合</h1>',current_html+'<h2>旧路线：连续检查发现中途相交</h2>')
html=html.replace('</html>','</details></html>')
(OUT/'index.html').write_text(html)
scripts=['check_CAM_forming_lift2_continuous.py','check_CAM_lift2_board_descent.py','check_CAM_lift2_forming_packing.py',
         'check_CAM_lift2_packing_witness.py','screen_CAM_lift2_forming_apex.py','screen_CAM_lift2_forming_side_turn.py',
         'screen_CAM_lift2_sequential_bends.py','screen_CAM_lift2_one_wire_at_a_time.py','render_CAM_lift2_review.py']
scripts+=['plan_CAM_one_wire_forming_envelope.py','plan_CAM_adaptive_forming_controls.py','plan_CAM_direct_angle_forming.py',
    'plan_CAM_reverse_angle_forming.py','plan_CAM_outer_first_forming.py','check_CAM_outer_first_contacts.py',
    'refine_CAM_outer_contact_path.py','render_CAM_contact_refined_forming.py']
scripts+=['check_CAM_sequential_continuous.py','diagnose_CAM_continuous_margin.py','render_CAM_continuous_return_conflict.py',
          'refine_CAM_return_corridor.py','check_CAM_return_corridor_continuous.py','plan_CAM_last_wire_continuous.py',
          'plan_CAM_critical_return_continuous.py','audit_CAM_sequential_displacement.py']
scripts+=['check_CAM_negative_return_edges.py','plan_CAM_negative_prefix.py','check_CAM_negative_tail.py',
          'check_CAM_first_three_continuous.py','render_CAM_negative_return.py','check_CAM_forming_junctions.py',
          'screen_CAM_housing_approach.py','render_CAM_housing_approach.py']
scripts+=['check_CAM_forming_tie_access.py','render_CAM_forming_tie_access.py','check_CAM_root_contact_feed.py']
scripts+=['inspect_CAM_root_seating.py','plan_CAM_root_seating.py','refine_CAM_root_seating.py',
          'check_CAM_root_seating_continuous.py','render_CAM_root_seating.py']
commands=[f'/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/{s}' for s in scripts]
commands.append('/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/verify_CAM_complete_forming.py')
# The continuous seating script requires the analytic receipt before it runs.
math_command='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/audit_CAM_root_seating_math.py'
continuous_command=next(c for c in commands if c.endswith('/check_CAM_root_seating_continuous.py'))
commands.insert(commands.index(continuous_command),math_command)
commands.append('/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/verify_CAM_root_seating.py')
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'reproduction_commands':commands,
    'executed_witness_path':'/tmp/mori_lift2_pack_witness.py; byte-identical source preserved as check_CAM_lift2_packing_witness.py',
    'continuous_command_outcome':'Stopped with SIGTERM after wire-envelope collision was proven; exit143; incomplete, not PASS',
    'versions':{'Python':platform.python_version(),'Blender':'5.2.2 LTS d13f752e3b9c'},'main_applied':False},indent=2)+'\n')
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
(OUT/'review_manifest.json').write_text(json.dumps({'status':'PASS','scope':'Consistent delivery of partial PASS and preserved failed candidates',
    'script_sha256':sha(SCRIPT),'source_main_sha256':b['source_main_sha256'],'board_descent_status':'PASS','board_descent_intervals':count,
    'forming_wire_packing':'PASS','continuous_forming_complete':True,'witness_sha256':sha(OUT/'packing_collision_witness.json'),
    'current_forming_scope':current['scope'],'current_forming_status':'PASS',
    'current_forming_interval_count':current['continuous_interval_count'],
    'current_forming_receipt_sha256':sha(current_file),'historical_simultaneous_wire_packing':'BLOCKED',
    'housing_external_approach':'PASS','housing_contact_insertion':'NOT_TESTED',
    'housing_approach_receipt_sha256':sha(OUT/'contact_refined_forming/housing_approach/screen.json'),
    'root_tie_tool_nominal':'PASS','root_tie_general_rigid_margin':'BLOCKED','root_tie_outward_tail_space':'PASS',
    'root_tie_tight_contact_feed':'BLOCKED','root_tie_full_installation':'NOT_TESTED',
    'root_tie_tool_receipt_sha256':sha(rootdir/'screen.json'),'root_tie_feed_receipt_sha256':sha(rootdir/'contact_feed.json'),
    'root_wire_seating_finite':'PASS','root_wire_seating_continuous':'PASS','root_wire_seating_intervals':256,
    'root_wire_seating_receipt_sha256':sha(seatingdir/'verification.json'),
    'initial_terminal_bypass':'BLOCKED','tie_threading_and_tightening':'NOT_TESTED',
    'initial_terminal_bypass_scope':'Rejected finite candidate routes; complete connected procedure remains unfinished',
    'terminal_catalogue_span_is_complete_envelope':False,
    'new_sequence_finite_status':seq['status'],'new_sequence_positions':len(seq['all_contact_positions']),
    'new_sequence_contact_nonpenetration':'PASS','new_sequence_continuous':'BLOCKED','new_sequence_nominal_wire_collision':'FAIL',
    'critical_return_continuous_status':critical['status'],'critical_return_full_sequence_coverage':False,'generic_contact_margin':'BLOCKED',
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
print('CAM_LIFT2_PUBLISHED',len(files),'board_intervals',count,'current_forming',current['status'],'whole_harness BLOCKED',flush=True)
