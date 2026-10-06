# -*- coding: utf-8 -*-
"""Publish H01-H04 static study and received PHC1 audit, not a CAD release."""
from pathlib import Path
import json,hashlib,datetime,re,html,urllib.request
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
when=datetime.datetime.now(datetime.timezone.utc).isoformat()
main=PROJECT/'mechanical/mori_v1_2.blend';base=read(PARENT/'M1_47_delivery.json')
v=read(HERE/'fourteen_validation.json');preview=read(HERE/'fourteen_preview_manifest.json')
body=read(HERE/'fourteen_body_sequence.json')
assert body['source_wire_check_sha256']==sha(HERE/'fourteen_validation.json')
assembly_filter=read(HERE/'imu_assembly_pools.json')
assert assembly_filter['source_pool_sha256']==sha(HERE/'imu_wide_pools.json')
filter_count=sum(r['input'] for r in assembly_filter['search'])
filter_pass=sum(r['passed'] for r in assembly_filter['search'])
regression=read(HERE/'screen_regression.json')
endpoint_check=read(HERE/'endpoint_plug_body_sequence.json')
assert regression['status']==endpoint_check['status']=='PASS'
receipt=read(PARENT/'hardware_A4_PH_receipt.json')
a5=read(PARENT/'hardware_A5_harness_receipt.json')
assert a5['status']=='PASS' and a5['main_sha256']==sha(main)
assert sha(PROJECT/a5['handoff'])==a5['handoff_sha256']
for row in a5['sources']:assert sha(PROJECT/row['file'])==row['sha256']
assert v['status']==preview['status']==receipt['status']=='PASS'
assert sha(main)==base['source_blend_sha256']==v['source_blend_sha256']==preview['source_main_sha256']==receipt['source_main_sha256']
for p,d in v['sources'].items():assert sha(PROJECT/p)==d,p
assert sha(HERE/preview['candidate_blend'])==preview['candidate_sha256']
for r in preview['images']:assert sha(HERE/r['file'])==r['sha256']
assert sha(PROJECT/receipt['handoff'])==receipt['handoff_sha256']
for entry in receipt['manifests'].values():
    assert sha(PROJECT/entry['file'])==entry['sha256']
    for p,d in read(PROJECT/entry['file']).items():assert sha(PROJECT/p)==d,p
for b in receipt['boards']:
    assert b['received_CLI_input_hashes_match'] and b['received_CLI_returncodes']==[0,0]
    for p,d in b['reports_sha256'].items():assert sha(PROJECT/p)==d,p
gap=min(r['conservative_inflated_capsule_gap_lower_bound_mm'] for r in v['wire_to_wire'])
rigidgap=min(g['conservative_capsule_gap_lower_bound_mm'] for r in v['rigid_solids'] for g in r['gap_checks'])
routes=read(HERE/'ecowire_joint.json')['routes']+read(HERE/'imu_wide_joint.json')['routes']
routes=sorted(routes,key=lambda r:r['id'])
style=re.search(r'<style>(.*?)</style>',(HERE/'index.html').read_text(),re.S).group(1)
def page(title,body):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+style+'</style><main>'+body+'</main></html>'
rows=''.join('<tr><td>%s</td><td>%s → %s</td><td>%.2f</td></tr>'%(r['id'],r['from_port'],r['to_port'],r['geometric_centerline_length_mm']) for r in routes)
(HERE/'index.html').write_text(page('MORI · 十四根身体导线候选',f'''
<a href="../index.html">返回到货前工作</a><h1>IMU 八线已并入身体走线候选</h1>
<p>M1.47 几何 · H01–H04，共十四根线 · 独立研究，未应用到主模型</p>
<p class="notice ok">保持原针序和结构。IMU 的 1–5 号线经后左侧，6–8 号线经后右侧；十四根线的实体、91 对线间距和 130 个头部姿态检查通过，没有增加打印件或走线孔。</p>
<p class="notice">这是一组静态走向候选。线材采购/压接、真实端子出线、固定绑束、拆装松量与其余线束仍未定，不能按下方几何长度裁线。</p>
<p class="notice">随后重放身体装配路径发现阻挡：上壳倾斜装入及后接口板随壳移动时，会碰到部分 IMU 线。407 个位置的带线检查为 {body['status']}；两处桥螺钉工具通道通过。当前静态候选不能直接作为装配路线，需继续调整走向。</p>
<figure><img src="fourteen_rear_upper.png" alt="保留承重桥及固定板，IMU八根候选线分两侧绕过托板后缘"><figcaption>后上方观察。橙色表示未采用的线材及插头包络；外壳、电池等在预览中隐藏，碰撞检查仍使用完整静态实体。</figcaption></figure>
<figure><img src="fourteen_rear_lower.png" alt="托板下方的IMU板和向下出线插头"><figcaption>后下方观察，显示托板背面的 IMU 与其插头；未为线路开孔，也未移动原生接线针号。</figcaption></figure>
<h2>输入与检查</h2><table><tr><th>线路</th><th>研究线材</th><th>外径上限</th><th>最小静态弯曲半径输入</th></tr>
<tr><td>H01，两根</td><td><a href="https://www.alphawire.com/products/wire/ecogen/ecowire/6712">Alpha 6712 / 24AWG</a></td><td>1.143 mm</td><td>5.715 mm</td></tr>
<tr><td>H02–H04，十二根</td><td><a href="https://www.alphawire.com/products/wire/ecogen/ecowire/6711">Alpha 6711 / 26AWG</a></td><td>1.016 mm</td><td>5.08 mm</td></tr></table>
<p>保留端后 5 mm 直段分配。原 A2 中 5853/5854 的 10D 要求保持不变；这里研究的是另外两种具名线材，尚未选定。IMU 曲线按曲率极值检查，最小曲率半径约 5.23 mm。</p>
<p>十四根封闭扫掠均为单个连通实体，未检出刚体或线间交叠。扣除几何增厚和数值余量后，线间最小间隙下界 {gap:.3f} mm，刚体间隙下界 {rigidgap:.3f} mm；超过本研究分配的 0.3 mm。130 个离散姿态覆盖 Yaw ±60°、Pitch −20°～25°，未检出头部碰撞；不等于连续运动或实物资格验证。</p>
<h2>仍需完成</h2><ul><li>端子实际出线、线材采购与压接、绑束固定、应力释放及带线拆装。</li><li>H05 与 J10 侧出候选的完整路径；其他分支、头部服务环和 FFC。</li><li>板卡候选正式整合、厂家接口资料，以及实际配合、温升与动态验证。</li></ul>
<p><a href="../hardware_A4_PH_review.html">18 个 PH 接口修孔候选的独立接收核对</a>已完成；其正式 PCB 尚未替换。</p>
<h2>A5 新增厂家资料</h2><p>已核对候选6711/6712的全外径公差及AWG均在SPH-002T-P0.5S目录范围内，实际mPPE压接、小量供货与加工报价仍未确认。J10插合后的导线中心高度仍未知。</p>
<p>保存场景内LCD、CAM和相机均属pitch组：FFC两端和全部固定点若随同一刚体运动，应先按静态弯曲与拆装设计。跨关节的供电、串口和舵机线另需运动检查。原配FFC的18P/0.5mm/200mm同向规格已收到，宽度、厚度和静态弯曲半径仍缺；SCS0009资料的编号/视图差异仍待厂家澄清。</p>
<p><a href="../hardware_A5_harness_receipt.json">A5机械接收记录</a> · <a href="../../../../hardware/v1_2/harness_evidence_20261002/README.md">硬件原始证据与询问稿</a></p>
<details><summary>几何中心线长度，仅用于比较</summary><p>未计入端子、剥线、固定和拆装余量，不是裁线尺寸。</p><table><tr><th>导线</th><th>端口</th><th>mm</th></tr>{rows}</table></details>
<p><a href="MORI_H01_H04_CANDIDATE_NOT_ADOPTED.blend">十四线独立 Blender</a> · <a href="fourteen_validation.json">联合检查</a> · <a href="imu_wide_joint.json">八线针序与曲线</a> · <a href="REVIEW.md">方法及范围</a></p>
<p><a href="fourteen_body_sequence.json">407位置的身体带线装配检查</a>与静态通过记录分别保存，未删除失败项。</p>
<p>筛选算法修正：最近三角面的法向符号不能可靠判断点是否在实体内。原先“{filter_count}条全部被拒绝”的结论撤回；改用完整曲线的表面间隙及封闭实体包含探针后，有{filter_pass}条通过单线装配筛查。<a href="screen_regression.json">四个实际场景回归检查</a>通过，<a href="imu_assembly_pools.json">新筛查结果</a>保留。单线通过仍不等于八线可同时装配。</p>
<p><a href="endpoint_plug_body_sequence.json">八个端点插头本体</a>独立通过407个装配位置和两处桥螺钉/工具路径。旧十四线实体装配相交是真实几何结果，仍保留FAIL；筛选误判不能抵消它。</p>
<p><a href="MORI_H01_H03_CANDIDATE_NOT_ADOPTED.blend">原六线 Blender</a>及<a href="ecowire_validation.json">原六线记录</a>保留。主模型/视频仍为 M1.47 / M1.47-A1，打印件保持。</p>'''))
lengths='\n'.join('|%s|%.2f|'%(r['id'],r['geometric_centerline_length_mm']) for r in routes)
(HERE/'REVIEW.md').write_text(f'''# H01–H04 十四根身体导线：静态候选

{when}。主模型 M1.47 保持，硬件正式板及几何配置未改。候选未选型、未采用，不是完整线束完成声明。

## 已完成

H01–H03 原六根线保持。IMU 八根线从 motion_J4 到 imu_J1，原针号 1–5 走后左侧，6–8 走后右侧；维持原端口朝向、5 mm 端后直段，不开走线孔。

十四根封闭扫掠各为单个连通实体，与刚体及相互之间未检出交叠。91 对线间保守间隙下界最小 {gap:.6f} mm，刚体下界最小 {rigidgap:.6f} mm，目标分配为0.3 mm。Yaw ±60°/10°步长、Pitch −20°～25°/5°步长共130姿态未检出交叠。有限姿态不证明连续运动安全。

## 带线身体装配检查：{body['status']}

按原上壳倾斜15°/升14mm、承重桥水平升18mm及后移14mm的分阶段路径重放407个位置，固定十四根候选线不动，并让后接口板及其两只插头包络随上壳运动。上壳碰到H04_1/2；后接口板/插头路径还碰到H04_1–5。两处桥螺钉抽出及L形工具包络通过。失败仅说明这组固定候选线不适用原路径，未证明必须改壳，也未假定拉扯导线就可通过。下一步调整候选走向；不改主模型。

后续查出筛选误判：最近三角面的法向符号在边界附近不能作为内外测试，实际空腔点距实体14.88mm却被判入实体。原“{filter_count}条全部被拒绝”结论已撤回，原始文件保留在filter_false_rejection_history。修正后有{filter_pass}条通过单线装配筛查；表面采样间隙下界保持，并仅在完整曲线都位于包围盒内时用封闭实体探针排除整体包含。四项实际场景回归检查通过。

八个端点插头本体独立通过407个装配位置及两处桥螺钉/工具路径。原十四线实体装配检查的FAIL没有撤销；它使用实体相交，独立于候选筛选的误判。当前正在完成八线联合排布。

## 数据与方法

- H01：Alpha6712/24AWG，外径上限1.143mm，厂家5D对应R5.715mm。
- H02–H04：Alpha6711/26AWG，外径上限1.016mm，厂家5D对应R5.08mm。IMU候选曲率最小约5.23mm。
- [厂家资料及哈希](ecowire_sources.json)。这些是独立研究用线材，并未降低原5853/5854的10D要求或替换硬件合同。
- IMU采用两段切向连续三次Bézier，通过曲率平方导数的多项式根求极值；保留5mm终端直段。单侧有限候选未完成八线联合布局，双侧有限候选搜索成功。这不是所有可能路线的穷举。
- 闭合扫掠半径比最大线径增加0.02mm；核对曲线弦差、32段球面内切误差和连通性。刚体碰撞仍检查完整闭合实体。
- 刚体表面距离使用不大于0.04mm弧长采样，扣除半采样区间、增厚后线半径与0.0001mm数值余量。只有与本端插头接触的5mm直段免除该插头间隙要求，完整实体碰撞仍检查。
- 全部91对线间距离为线段到线段最小值，扣除两根增厚后半径及0.0001mm数值余量，并另查实体交叠。不是仅采样端点或外包盒距离。
- 原网格MinGap程序因实测性能瓶颈停止，保留在validation_attempts/01_mesh_min_gap；没有把中止结果视为通过。

## 未完成范围

插头针序和节距取自原生板；端子横向出线位置仍按壳体中线估计。未验证线材价格/供货、压接工艺、固定/绑束、应力释放、带线取板或装配松量。H05、头部FFC和有限服务环、其他分支仍待完成。原几何长度不得用于裁线。静态弯曲半径不是反复摆头寿命。

## A5新增证据

已接收12项交接文件与12份成功获取的厂家/供应商源文件，249份正式源文件未改。候选6711/6712的完整OD公差和AWG在SPH002目录范围内，但实际压接仍NOT_TESTED，小量材料/加工报价未取得。

直接读取M1.47场景确认LCD、CAM和相机都在pitch组。如果FFC两端及所有固定点同属该刚体，按静态布线处理；跨关节线才需相应动态服务环。随屏18P/0.5mm/200mm同向FFC有厂家依据，宽度/厚度/最小半径没有确认。SCS0009第4页与第8页的编号/视图区别、J10的真实出线Z继续BLOCKED，未更改引脚或选型。见[A5接收记录](../hardware_A5_harness_receipt.json)。

## 几何长度（未计端子和松量）

|导线|中心线 mm|
|---|---:|
{lengths}

## 证据

- [十四线检查](fourteen_validation.json) · [八线联合选择](imu_wide_joint.json) · [独立Blender](MORI_H01_H04_CANDIDATE_NOT_ADOPTED.blend)
- [身体带线装配失败记录](fourteen_body_sequence.json)
- [原六线记录](ecowire_validation.json) · [原A2参数筛查](static_screen.json)
- [PH修孔候选接收](../hardware_A4_PH_review.html) · [J10 A3独立复核](../J10_A3_review/index.html)

PROTOTYPE / UNVALIDATED。PASS仅限声明的名义几何；完整线束与制造仍未放行。
''')
boardrows=''.join('<tr><td>%s</td><td>%d</td><td>%d</td><td>0 / 0</td></tr>'%(b['board'],b['components_checked'],len(b['PH_pads_checked'])) for b in receipt['boards'])
(PARENT/'hardware_A4_PH_review.html').write_text(page('MORI · PH修孔候选机械接收',f'''
<a href="index.html">返回到货前工作</a><h1>18 个 PH 接口：修孔候选已核对</h1>
<p class="notice ok">硬件完成 PHC1 独立候选。机械直接读取正式/候选原生板，确认 69 个编号孔中心、185 个器件的位置朝向和3D引用、板框、安装孔及非PH焊盘保持。</p>
<p class="notice">正式PCB和主模型尚未替换。板厂成品孔公差未确认；此候选不是 J10 侧出 C2，后者仍需单独完成布线与线束。</p>
<table><tr><th>板</th><th>器件数</th><th>PH孔数</th><th>收到的 ERC / DRC 违规数</th></tr>{boardrows}</table>
<p>2P 名义孔/铜盘为0.85/1.45mm，3–16P为0.90/1.50mm，绘制环宽0.30mm。硬件提出成品孔+0/−0.05mm，尚未获得板厂承诺，不能当作已验证工艺。</p>
<p>核对249份正式源文件与264份候选文件哈希；四板8条原生检查命令返回0，输入哈希与当前候选匹配。ERC/DRC是收到的硬件检查，机械未重复运行电气检查，也未把它当成孔加工或电气性能资格。</p>
<p><a href="hardware_A4_PH_receipt.json">逐项接收结果</a> · <a href="../../../hardware/v1_2/handoff/mechanical_P5R7_prearrival_A4_PH.json">A4原始交接</a> · <a href="../../../hardware/v1_2/ph_hole_candidates_20261002/README.md">硬件候选说明</a> · <a href="SUPPLIER_DATA_REQUEST.md">仍缺的厂家资料</a></p>'''))

status=read(PARENT/'work_status.json');old={r['id']:r.copy() for r in status['remaining']}
for r in status['remaining']:
    if r['id']=='harness':
        r['detail']='H01–H04十四根静态候选的实体、91对线间及130头部姿态通过；身体装配407位置复核发现上壳及后板/插头路径碰到IMU线，需继续改走向，未改壳。线材/端子、固定、松量、H05、头部FFC/服务环和其他分支仍未完成。'
    if r['id']=='supplier_interfaces':
        r['detail']='SCS0009舵盘/短轴锁紧及线序视图、S288输出自攻螺钉、WeAct E孔针与插接长度、PHR8真实出线仍缺资料。A4的18个PH接口/69孔候选检查通过但未正式替换；A5确认线材目录范围和FFC部分规格，压接、板厂孔公差及FFC宽厚/半径仍待确认。'
        r['evidence']='hardware_A4_PH_review.html'
for entry in [dict(id='H01_H04_static_candidate',status='PASS',detail='十四根独立静态线候选实体、91对间隙及130头部姿态通过；完整线束、固定及采购尚未完成。'),
              dict(id='PHC1_mechanical_receipt',status='PASS',detail='18个PH接口/69孔、185器件及板框安装接口的原生对比通过；收到ERC/DRC报告和命令输入哈希一致，未应用正式板。')]:
    status['completed']=[r for r in status['completed'] if r['id']!=entry['id']]+[entry]
status['updated_utc']=when
status['prearrival_wire_addendum'].update(static_H01_H04_geometry='PASS',IMU_static_candidate='PASS',
    PHC1_native_mechanical_receipt='PASS',PHC1_applied=False,PHC1_review='hardware_A4_PH_review.html',
    wire_pair_count=91,wire_gap_lower_bound_mm=gap,head_pose_count=130,body_sequence_with_static_wires=body['status'],
    A5_harness_evidence_receipt='PASS',A5_receipt='hardware_A5_harness_receipt.json',
    FFC_motion_basis='Static if both ends and all anchors are on pitch; routing/bend data still pending')
write(PARENT/'work_status.json',status)
top=(PARENT/'index.html').read_text()
for r in status['remaining']:
    top=top.replace(html.escape(old[r['id']]['detail']),html.escape(r['detail'])).replace(old[r['id']]['detail'],r['detail'])
top=top.replace('H01–H03六根线','H01–H04十四根静态线')
top=top.replace('带线拔插、候选布线及18个PH接口孔径修正仍未完成。','带线拔插和J10候选布线仍未完成；18个PH接口已有独立修孔候选，尚未正式替换。')
section='<section id="fourteen-wire-update"><h2>新增检查</h2><p><a href="harness_A2/index.html">十四根身体导线</a>的静态/头部姿态检查通过；身体带线装配发现上壳/后板路径碰IMU线，正在调整。<a href="hardware_A4_PH_review.html">18个PH接口修孔候选</a>已完成独立机械接收。两项仍属候选，完整线束及制造未放行。</p></section>'
top=re.sub(r'<section id="fourteen-wire-update">.*?</section>','',top,flags=re.S)
top=top.replace('</main>',section+'</main>')
(PARENT/'index.html').write_text(top)
# Mark A3 report as historical with a link to the newer hole-only result.
a3=PARENT/'J10_A3_review/index.html';txt=a3.read_text()
if 'id="PHC1-update"' not in txt:
    txt=txt.replace('<h2>打样前新增：18个PH接口孔径</h2>', '<p id="PHC1-update" class="notice">后续进展：<a href="../hardware_A4_PH_review.html">PHC1独立修孔候选及接收核对</a>已完成，正式板未替换。以下保留A3当时记录。</p><h2>打样前新增：18个PH接口孔径</h2>')
    a3.write_text(txt)
for p,d in base['files'].items():
    if p.endswith('/work_status.json'):base['files'][p]=sha(PROJECT/p)
    else:assert sha(PROJECT/p)==d,'Main artifact drift: '+p
base['documentation_addendum']='harness_A2/delivery.json';write(PARENT/'M1_47_delivery.json',base)
pages=[HERE/'index.html',PARENT/'index.html',PARENT/'hardware_A4_PH_review.html',a3]
links=[]
for p in pages:
    checked=[];missing=[]
    for ref in re.findall(r'(?:href|src)=["\']([^"\']+)',p.read_text()):
        if ref.startswith(('http:','https:','#','data:','mailto:')):continue
        target=(p.parent/ref.split('#')[0].split('?')[0]).resolve();checked.append(str(target.relative_to(PROJECT)))
        if not target.exists():missing.append(ref)
    links.append(dict(page=str(p.relative_to(PROJECT)),checked=checked,missing=missing))
assert not any(r['missing'] for r in links),links
http=[]
for p in [HERE/'index.html',HERE/'fourteen_rear_upper.png',HERE/'fourteen_rear_lower.png',PARENT/'hardware_A4_PH_review.html']:
    url='http://127.0.0.1:58201/'+str(p.relative_to(PROJECT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as resp:
        http.append(dict(url=url,status=resp.status,content_type=resp.headers.get('Content-Type')))
assert all(r['status']==200 for r in http)
artifacts=[p for p in HERE.iterdir() if p.is_file() and p.suffix in ['.json','.py','.log','.png','.html','.md','.blend'] and p.name!='delivery.json']
artifacts += [PARENT/n for n in ['hardware_A4_PH_receipt.json','receive_A4_PH.py','receive_A4_PH.log','hardware_A4_PH_review.html','SUPPLIER_DATA_REQUEST.md','index.html','work_status.json','engineering_A2_mass_addendum.json']]
artifacts += [PARENT/n for n in ['hardware_A5_harness_receipt.json','receive_A5_harness.py','receive_A5_harness.log']]
artifacts += list((PARENT/'J10_A3_review').glob('*'))
previous=read(HERE/'history_six_wire_A3/harness_A2__delivery.json')
commands=previous['commands']+[
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/inspect_imu.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/imu_individual_routes.py -- --ecowire --wide',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A2/select_imu_joint.py --wide',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/validate_fourteen.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/render_fourteen.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/check_fourteen_body_sequence.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/harness_A2/filter_imu_body_paths.py',
 '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 mechanical/studies/prearrival_finish/receive_A4_PH.py',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python mechanical/studies/prearrival_finish/receive_A5_harness.py',
 'python3 mechanical/studies/prearrival_finish/harness_A2/publish_fourteen.py']
delivery=dict(verified_utc=when,status='PASS',scope='Research artifact/source/link consistency, not full harness or manufacturing release',
 main_source_sha256=sha(main),main_geometry_changed=False,animation_changed=False,STL_changed=False,
 H01_H04_static_geometry='PASS',IMU_static_route='PASS',body_sequence_with_static_wires=body['status'],body_path_single_candidate_filter=assembly_filter['status'],complete_harness='BLOCKED',J10_A3_complete_harness='BLOCKED',
 PHC1_mechanical_receipt='PASS',formal_board_PH_hole_correction='BLOCKED',adopted=False,
 files={str(p.relative_to(PROJECT)):sha(p) for p in artifacts if p.is_file()},
 received_A3_sources=previous['received_A3_sources'],received_A4_PH_handoff_sha256=receipt['handoff_sha256'],received_A5_harness_handoff_sha256=a5['handoff_sha256'],
 local_link_checks=links,HTTP_checks=http,commands=commands,
 versions=dict(previous['versions'],KiCad='10.0.6'),manufacturing_release=False)
write(HERE/'delivery.json',delivery)
print('FOURTEEN_ADDENDUM_VERIFIED',len(delivery['files']),'files',len(links),'pages',len(http),'HTTP objects',sha(main))
