"""Publish partial CAM retention/installation evidence, keeping main untouched."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];FINISH=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda n:json.loads((HERE/n).read_text())
reports=['anchors.json','material_stations.json','tools_and_tail.json','neck_feed_verified.json','board_installation.json']
data={n:load(n) for n in reports}
assert all(d['status']=='PASS' and not d['main_applied'] and d['whole_harness']=='BLOCKED' for d in data.values())
main_sha=sha(PROJECT/'mechanical/mori_v1_2.blend')
assert all(d['source_main_sha256']==main_sha for d in data.values())
anchors=data['anchors.json'];stations=data['material_stations.json'];feed=data['neck_feed_verified.json'];board=data['board_installation.json']
now=datetime.now(timezone.utc).isoformat()
detail=('CAM四线完整路线的候选已有两处一体固定座和两根扎带，130姿态及材料点位置检查通过；'
        '剪尾工具、向上弯起的扎带长尾、四向局部穿颈扫掠，以及CAM板抬高6mm插线再落座的16个位置检查通过。'
        '这些仍是未采用的三个打印件候选，完整带线工序没有通过；身体端应力释放、连续柔性装配、'
        '扎带穿入/收紧、另7根跨关节线与FFC及供应商制作图未完成。完整线束仍BLOCKED。')
readme=f'''# M1.48：CAM 线固定与装入候选

**补齐了本页列出的局部数字检查；完整线束仍为 BLOCKED。结构候选尚未应用主模型。**

两处固定座分别并入 Pitch_Yoke 和 Pitch_Cradle，不增加打印件，增加两根扎带预留。
固定座按四根线的直线段定位；它们不会证明柔性导线会自然保持数学曲线。
使用前一研究的 Yaw_Base/Pitch_Yoke 通道，因此总计涉及三个未采用的打印件。

![CAM 板与头部固定座候选](anchors_front.png)

橙色为扎带估计外形，四色细线区分机械路线，不表示电气线序。
屏幕、相机、头壳及部分头部轴件尚未安装，符合本次工具检查的工序。
图中 CAM 板为当前来源模型，仍包含照片估计细节。

| 检查 | 结果及边界 |
|---|---|
| 两处固定座与扎带 | PASS：130 个组合姿态、3120 组线与局部特征检查；两座与各自主体均连通 |
| 固定点的导线长度位置 | PASS：24 个指定位置、各 130 姿态；最大数值变化 {max(r['material_position_variation_mm'] for r in stations['stations']):.8f} mm。只验证曲线，不是加工公差 |
| 剪尾工具与扎带长尾 | PASS：两处工具进出；CAM 侧找到向上弯起的 80 mm 临时长尾空间。长尾不是成品长度 |
| 四向端子穿颈及局部线形放松 | PASS：每方向 410 个包络区间；端子名义间隙下界 {feed['terminal_gap_lower_bound_mm']:.6f} mm，线体 {feed['wire_gap_lower_bound_mm']:.6f} mm |
| CAM 板后装 | PASS：抬高 6 mm 后插线、再落座的 16 个位置，64 条完整线对当前实体复核；板卡逐元件和胶壳的 6 mm 刚性平移扫掠通过 |
| 完整工序 | BLOCKED：以上局部工序还未连成完整带线装配，不能算整项完成 |

端子穿颈仍以 1.0×1.8×4.1 mm 估计包络检查，不是已确认的压接后最大尺寸。
0.31 mm 检查膨胀扣除网格和插值误差后仍超过原定 0.3 mm 间隙。
早期 neck_feed.json 使用切槽时的 0.32 mm 工具面重放，在共边处出现微小相交；保留该诊断，
没有提高相交豁免值或再次切薄结构。当前依据为 neck_feed_verified.json。

![扎带长尾向上弯起的临时工作空间](tail_workspace.png)

绿色只表示操作时的临时扎带长尾。实际弯折能力、穿入锁头、收紧手势及剪切仍未验证。
工具外形含照片估计；这不是完整的人手操作或工艺认证。

## 还需要完成

1. 身体端独立应力释放；现有 J5 插头不能代替线束固定。
2. 自由线尾穿颈、线形形成、CAM 插接、扎带收紧、其他部分装入之间的完整衔接。
3. 其余七根跨关节导线、相机 FPC、屏幕 FFC 及整套线间干涉。
4. 通道与固定座的可制造性和结构复核；三个打印件的改动需确认后应用。
5. 实际线端针腔、压接最大尺寸和线材资料；供应商制作图仍不发布。

轴颈通道的采样最薄壁仍约 1.48 mm，原件约 2.25 mm；本次没有进一步减薄。
扎带夹持力、PA12 强度、真实插拔、磨损与动态寿命仍需实物。
CAM 板的柔性运动是 16 个离散位置；本次没有宣布全线连续运动或重新批准全部线间排布。
插头自身的五毫米出线区域只对自身接口预留体作有界排除，实际端子配合仍 BLOCKED。

主模型仍为 M1.48，正式 STL、装配动画和硬件文件保持已批准状态。
距离实物前工作完成仍有五类：完整线束、反力夹初装、采购件及安装、供应商接口资料、质量与驱动预算。

[候选 Blender](review.blend) · [固定座反面](anchors_rear.png) · [前一阶段完整路线](../yaw_service_M1_48/index.html)

[固定与姿态](anchors.json) · [导线材料点](material_stations.json) · [工具及长尾](tools_and_tail.json)
· [穿颈扫掠](neck_feed_verified.json) · [CAM 后装](board_installation.json)
· [发布来源](publication.json) · [交付核对](delivery.json)

更新：{now}
'''
(HERE/'README.md').write_text(readme)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · CAM 线固定与装配候选</title>
<style>body{{background:#f3f5f4;color:#233c35;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}}main{{max-width:1080px;margin:auto;padding:28px 22px 60px}}h1{{font-size:30px;line-height:1.4}}a{{color:#176950}}.note{{padding:16px 20px;background:#fff1d4;border:1px solid #d9b46b}}figure{{margin:24px 0;background:white;border:1px solid #c7d2cc}}img{{display:block;width:100%}}figcaption{{padding:12px 16px}}td,th{{padding:12px;border-bottom:1px solid #ccd7d1;text-align:left;vertical-align:top}}table{{border-collapse:collapse;width:100%;background:#fff}}.links{{display:flex;gap:14px;flex-wrap:wrap}}</style>
<main><nav><a href="../index.html">到货前待办</a> · <a href="../yaw_service_M1_48/index.html">前一阶段：完整 CAM 路线</a></nav>
<h1>CAM 固定和局部装入已有候选，完整线束仍未完成</h1>
<p class="note"><b>未应用主模型。</b>两处固定座并入已有打印件，配两根扎带；加上前一阶段通道，共涉及三个打印件候选。仍需把局部步骤连成完整带线装配工序。</p>
<figure><img src="anchors_front.png" alt="CAM 板及线固定座候选"><figcaption>橙色为扎带估计外形，线色仅区分机械路线。屏幕、相机、头壳等尚未安装；不会作为主模型显示。</figcaption></figure>
<table><thead><tr><th>已补的检查</th><th>通过范围</th></tr></thead><tbody>
<tr><td>固定座、扎带及线路</td><td>130 个组合姿态；两个固定座与主体连通，不增加打印件。</td></tr>
<tr><td>导线在固定点的位置</td><td>24 个位置 × 130 姿态，材料点数值变化约 0.000016 mm；不是制造精度或夹持力证明。</td></tr>
<tr><td>剪尾工具与临时长尾</td><td>工具进出与一条向上弯起的 80 mm 长尾候选通过；实际穿入、收紧尚未验证。</td></tr>
<tr><td>局部穿颈</td><td>四个方向各 410 个包络区间，要求仍为 0.3 mm。端子压接后最大尺寸仍待厂家。</td></tr>
<tr><td>CAM 板后装</td><td>板卡抬高 6 mm 插线再落座：16 个位置、64 条完整线对实体检查及逐元件刚性平移扫掠通过；6 mm 是插合行程预留。</td></tr>
</tbody></table>
<figure><img src="tail_workspace.png" alt="向上弯起的绿色临时扎带长尾"><figcaption>绿色长尾只在收紧、剪尾时存在。图示空间不证明扎带实际弯折和手工收紧可行。</figcaption></figure>
<h2>仍未完成的线束工作</h2><p>身体端应力释放；穿颈、成形、插接与扎带收紧的完整衔接；另七根跨关节线和 FFC；候选通道/固定座的结构及制造复核；最终供应商制作图。</p>
<p>本次柔性装配只检查离散位置，完整线束仍 <b>BLOCKED</b>。三个打印件候选均未进入正式 STL 或装配视频；轴颈采样最薄壁仍约 1.48 mm，强度未验证。</p>
<p>距离实物前工作完成仍有五类：完整线束、反力夹初装、采购件及安装、供应商接口资料、质量与驱动预算。主模型为 M1.48。</p>
<p class="links"><a href="review.blend">独立 Blender</a><a href="anchors_rear.png">固定座反面</a><a href="README.md">完整说明和限制</a><a href="../work_status.json">项目剩余清单</a></p>
<details><summary>检查记录与来源</summary><p class="links"><a href="anchors.json">固定座</a><a href="material_stations.json">导线材料点</a><a href="tools_and_tail.json">工具与长尾</a><a href="neck_feed_verified.json">穿颈</a><a href="board_installation.json">CAM 后装</a><a href="publication.json">文件哈希</a><a href="delivery.json">交付核对</a></p><p>早期 neck_feed.json 是构造切削面的边界重放诊断，当前穿颈依据为 neck_feed_verified.json。未放宽 0.3 mm 间隙或修改打印件取得通过。</p></details>
</main></html>'''
(HERE/'index.html').write_text(html)
changed={}
status_path=FINISH/'work_status.json';before=sha(status_path);status=json.loads(status_path.read_text())
status['updated_utc']=now
entry=next(r for r in status['remaining'] if r['id']=='harness')
entry['detail']=detail;entry['latest_retention_evidence']='cam_retention_M1_48/index.html';entry['latest_retention_detail']=detail
status['cam_retention_M1_48']=dict(status='PASS',scope='Local candidate fixation and assembly checks only',evidence='cam_retention_M1_48/index.html',
    source_main_sha256=main_sha,print_candidates=['Yaw_Base','Pitch_Yoke','Pitch_Cradle'],added_printed_parts=0,added_ties=2,
    anchor_head_poses=130,material_stations=24,material_station_poses=130,neck_feed_directions=4,neck_feed_spans_each=410,
    CAM_board_positions=16,full_wire_entity_checks=64,whole_harness='BLOCKED',main_applied=False,
    body_retention='NOT_TESTED',complete_flexible_assembly='NOT_TESTED',tie_tightening='NOT_TESTED',
    other_seven_wires_and_FFC='NOT_TESTED',manufacturing_release=False)
# This already-adopted M1.48 change retained a stale proposal flag.
camera=status.get('camera_top_clearance_candidate',{})
assert camera.get('main_applied') and camera.get('adopted_revision')=='V1.2-M1.48'
camera['pending_user_adoption']=False
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');changed[str(status_path.relative_to(PROJECT))]=dict(before=before,after=sha(status_path))
for path,href in [(PROJECT/'mechanical/index.html','studies/prearrival_finish/cam_retention_M1_48/index.html'),(FINISH/'index.html','cam_retention_M1_48/index.html')]:
    before=sha(path);text=path.read_text()
    block=f'<aside id="M1-48-yaw-service" class="notice"><b>CAM线固定与局部装配检查已补，完整线束仍未完成。</b> 三个打印件候选未应用；完整工序、身体端固定、另7根线和FFC待完成。<a href="{href}">查看最新候选和剩余工作</a>。</aside>'
    assert 'id="M1-48-yaw-service"' in text
    text=re.sub(r'<aside id="M1-48-yaw-service".*?</aside>',block,text,count=1,flags=re.S)
    def replace_row(match):
        row=match.group(0)
        if '<td>完整线束</td>' not in row:return row
        cells=re.findall(r'<td>.*?</td>',row,re.S);assert len(cells) in [2,3]
        cells[-1]=f'<td>{detail} <a href="{href}">当前依据</a></td>'
        return '<tr>'+''.join(cells)+'</tr>'
    text=re.sub(r'<tr>.*?</tr>',replace_row,text,flags=re.S);path.write_text(text)
    changed[str(path.relative_to(PROJECT))]=dict(before=before,after=sha(path))
commands=[]
for script,log in [('check_anchors.py','anchors.log'),('check_material_stations.py','material_stations.log'),('check_tool_routes.py','tools_and_tail.log'),('verify_neck_feed.py','neck_feed_verified.log'),('check_board_installation.py','board_installation.log'),('render_review.py','render_review.log')]:
    contents=(HERE/log).read_text();assert 'Blender quit' in contents and 'Traceback' not in contents
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python '+str((HERE/script).relative_to(PROJECT)),cwd=str(PROJECT),script_sha256=sha(HERE/script),log=log,log_sha256=sha(HERE/log)))
publication=dict(status='PASS',scope='Partial current-main retention and assembly candidate evidence',utc=now,source_main_sha256=main_sha,
    result_files=reports,native_sources=anchors['native_context']['sources'],reproduction_commands=commands,
    tools=dict(Blender='5.2.2 LTS d13f752e3b9c',publication_python='mori-cad Python 3.12.14'),
    visual_review='Three PNGs inspected; CAM board visible, anchors and temporary tail distinguished; some structures occlude the rear anchor.',
    changed_presentation_files=changed,files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['publication.json','delivery.json']},
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(HERE/'publication.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n')
print('CAM_RETENTION_PUBLISHED',now,flush=True)
