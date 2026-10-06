"""Publish the connector-direction investigation without changing the main CAD."""
from pathlib import Path
import datetime,hashlib,json,os,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';FLEX=BASE/'static_flex';OUT=FLEX/'connector_faces'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
paths=[OUT/'review.json',OUT/'orientation/review.json',OUT/'terminal_length_audit.json']
paths += [OUT/'direction_receipt.json',OUT/'pair_terminal_length_audit.json']
for p in paths:
    r=read(p);assert not r['main_changed']
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
assert read(paths[0])['status']=='PASS' and read(paths[1])['status']=='PASS'
assert read(paths[2])['status']=='FAIL'
jobs=[('inspect_flex_connector_faces.py','static_flex_connector_faces.log',paths[0],'FFC_CONNECTOR_FACES_DONE',True),
      ('review_flex_orientation.py','static_flex_orientation.log',paths[1],'FFC_ORIENTATION_HYPOTHESES_DONE',True),
      ('audit_flex_terminal_length.py','static_flex_terminal_audit.log',paths[2],'FFC_TERMINAL_LENGTH_AUDIT_DONE FAIL',False),
      ('receive_flex_direction_handoff.py','static_flex_direction_receipt.log',paths[3],'FPC_DIRECTION_RECEIPT_DONE PASS',False),
      ('audit_flex_terminal_pair.py','static_flex_pair_audit.log',paths[4],'FFC_PAIR_TERMINAL_AUDIT_DONE FAIL',False)]
commands=[]
for script,log,result,token,blender in jobs:
    s=HERE/script;l=BASE/log;r=read(result);txt=l.read_text()
    assert sha(s)==r['script_sha256'] and token in txt and 'Traceback' not in txt
    if blender:assert 'Blender quit' in txt
    argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))] if blender else ['python3',str(s.relative_to(ROOT))]
    commands.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),
        log_sha256=sha(l),script_sha256=sha(s),result=str(result.relative_to(ROOT)),
        result_sha256=sha(result),check_status=r['status']))
write(OUT/'commands.json',dict(status='PASS',utc=now,commands=commands,failed_executions=[],
    scope='Execution record; terminal budget result is FAIL, not a software error.',
    script_sha256=sha(Path(__file__))))

refs={n:ROOT/'mechanical/sources/waveshare_detail'/n for n in [
    'ESP32-S3-CAM-OVxxxx-details-5-2.jpg','esp32-s3-cam-ovxxxx-3_1.jpg',
    'esp32-s3-cam-ovxxxx-2_1.jpg']}
received=read(OUT/'direction_receipt.json')
assert received['package_files_checked']==31
for f,h in received['files'].items():assert sha(ROOT/f)==h,f
handroot=ROOT/received['source_package']
refs['use_msg_01.webp']=handroot/'sources/use_msg_01.webp'
refs['handoff.json']=handroot/'handoff.json'
refs['missing_fields.csv']=handroot/'missing_fields.csv'
refs['hardware_README.md']=handroot/'README.md'
relative={k:os.path.relpath(v,OUT) for k,v in refs.items()}
note='''# CAM 与 LCD 排线座方向复核

主模型 M1.49 C5＋K1 未变。本研究提取原模型，并制作三个独立可编辑视图：当前模型、只转相机座、相机与屏幕座都转。后两者只是视觉假设，均未应用；金色指片不表示已核实的物理针号。

## 已有证据

- **CAM 相机座**：官方已插线照片的橙色 FPC 从上缘向 SD 卡方向伸出，即 SD 面局部 +V／整机 +Z。当前重建槽朝 -V／-Z，两者相反。相机座转 180° 的独立候选可让黑盖与槽的位置接近照片；这不补齐其型号、真实接触面、插入深度、补强和公差。
- **CAM 屏幕座**：硬件 CAM-FPC-EXIT-R1 已找到两张官方接屏实拍，直接支持向板外 -U／零位 -X 出线。当前重建白色主体在局部 -U（IC 面照片右侧、板边），黑盖在 +U（照片左侧、板内），其黑白布局与官方照片一致，但模拟入口画在了相反侧。需要单独修正入口表达，不能整体转180°。两个都转的图保留作反例，未推荐采用。官方实拍使用其他尺寸屏幕，只用于 CAM 端方向，不能证明本项目 LCD35079 的整链路兼容。
- **LCD L1 / Connector_108**：原厂 STEP 的 -X 侧可见入口指片，+X 侧为 SMT 焊脚，支持排线从整机 -X 侧接近。此项是原厂模型观察，不是实物测量；完整接触面、针1视图及实际采购批次仍未知。

CAM 的板坐标 U 是 SD 面向右，V 是 SD 面向上。IC 面观察时左右反转；整机中 U→+X、V→+Z。原理图提供逻辑网络，不提供装配时的视角或可交换的实际针号。

## 对上轮 170 mm 收纳候选的影响

中央段最后切向为 -X，而由 LCD 的 -X 入口进入时切向为 +X；需转向 180°。在此前 R7.5 mm 的容量假设下，仅改变切向就至少需要 πR ≈23.56 mm，已超过分给屏幕端的15 mm。R5 假设也至少15.71 mm。计算不含插入长度、端点距离和宽度姿态约束。

CAM 实拍也支持向 -X 出线，而原中央段初始切向为 +X，因此 CAM 端也需要反向。R7.5 假设下两端合计至少47.12 mm，中央段最多152.88 mm；这个上限尚未扣除插入、补强或位置偏差，不是一条已通过的路径。

因此旧的“中央170＋两端各15”分配不能直接补成完整排线，必须重新分配长度。**这不等于200 mm原配线太短，也不否定原中央段自身的空间检查。**R5/R7.5是容量假设，不是厂家的允许弯曲半径。不能缩小曲率或伸长排线来凑已有图。

## 尚未结束

硬件 CAM-FPC-EXIT-R1 资料交接已收到，31份包内文件及572份受保护文件哈希复核一致；逻辑针表未改变。来源和遗漏字段见 direction_receipt.json 及硬件原包。此研究未修改电气文件、BOM、针表、主模型、打印件、STL或装配视频。

仍需实际连接器/排线型号与版本、触点面和针1视角、线宽厚/补强区/插入深度/允许弯曲数据，再完成整根屏幕FFC、相机原配FPC的过渡、固定和装入路径。完整屏幕排线及完整线束均为 BLOCKED。
'''
(OUT/'README.md').write_text(note)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M1.49 排线座方向复核</title><style>body{font:16px/1.7 system-ui;background:#f4f6f7;color:#22313b;margin:0}main{max-width:1120px;margin:auto;padding:30px 22px}h1{font-size:30px}h2{margin-top:36px}a{color:#17648d}.note{background:#fff5df;border-left:5px solid #d39324;padding:14px 18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}figure{margin:0;background:white;padding:12px;border-radius:12px}img{width:100%;height:auto}figcaption{font-size:14px;margin-top:10px}table{width:100%;border-collapse:collapse;background:white}th,td{padding:12px;text-align:left;border-bottom:1px solid #dce2e7}.small{font-size:14px}</style><main>
<p><a href="../index.html">返回屏幕排线容量研究</a> · <a href="../../index.html#flex-connectors">线束总进展</a></p>
<h1>先核对入口方向，再连接整根排线</h1>
<p class="note">主模型仍为 M1.49 C5＋K1。以下转向图只用于比较，未应用到主模型。相机座有明确照片方向差异；CAM 屏幕座不能据此一起翻转。</p>
<h2>1. 相机：官方已接线照片显示向上出线</h2>
<div class="grid"><figure><a href="PHOTO_CAMERA"><img src="PHOTO_CAMERA" alt="官方OV3660已插线照片"></a><figcaption>官方照片：橙色排线由座上缘向 SD 卡方向伸出，即 +V／整机 +Z。</figcaption></figure>
<figure><a href="orientation/current_SD.png"><img src="orientation/current_SD.png" alt="当前CAM相机座槽向下"></a><figcaption>当前重建：槽和黑色示意盖朝下，方向与照片相反。</figcaption></figure>
<figure><a href="orientation/camera_180_SD.png"><img src="orientation/camera_180_SD.png" alt="只将相机座重建几何转向上方的比较"></a><figcaption>独立候选：只转相机座的重建几何，板卡和其他元件不动。仍是照片估算，未应用。</figcaption></figure></div>
<h2>2. CAM 屏幕座：向板外出线，保留正确的黑白布局</h2>
<figure><a href="PHOTO_CONNECTED"><img src="PHOTO_CONNECTED" alt="微雪官方CAM接屏实拍，排线从板边向外伸出"></a><figcaption>官方已接线实拍：USB朝右，把板转回USB朝下后，排线向照片右／主板−U／零位−X出线。示例使用其他尺寸屏幕，仅支持CAM端方向，不证明本项目整链路兼容。<a href="https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Instructions-For-Use">微雪原始使用说明</a>。</figcaption></figure>
<div class="grid"><figure><a href="PHOTO_IC"><img src="PHOTO_IC" alt="官方CAM IC面照片"></a><figcaption>官方 IC 面照片。与 SD 面相比左右翻转：白色主体在板边，黑盖在板内。</figcaption></figure>
<figure><a href="orientation/current_IC.png"><img src="orientation/current_IC.png" alt="当前CAM屏幕座重建"></a><figcaption>当前模型黑白布局正确，但模拟入口在内侧，应单独改为板外方向。准确槽高、插深和触点仍未知。</figcaption></figure>
<figure><a href="orientation/both_180_IC.png"><img src="orientation/both_180_IC.png" alt="屏幕座也翻转的假设对照"></a><figcaption>若屏幕座也转，黑白布局反而与照片相反。此图仅作排除误改的对照，未推荐采用。</figcaption></figure></div>
<h2>3. LCD 原厂 CAD：从 −X 侧接近入口</h2>
<div class="grid"><figure><a href="Connector_108_minus_x.png"><img src="Connector_108_minus_x.png" alt="LCD原厂Connector108负X侧"></a><figcaption>原厂 CAD 的 −X 侧可见入口指片。原三角面原尺寸提取。</figcaption></figure>
<figure><a href="Connector_108_plus_x.png"><img src="Connector_108_plus_x.png" alt="LCD原厂Connector108正X侧"></a><figcaption>+X 侧是 SMT 焊脚。不是另一处排线入口。</figcaption></figure></div>
<h2>此前两端各 15 mm 的长度预算需要调整</h2>
<p>中央段末端朝 −X，进入 LCD 时需朝 +X。沿用 R7.5 mm 的容量假设，仅转向180°就至少需要23.56 mm，已超过15 mm。R5假设也至少15.71 mm。这里还没有计入插深和两端的位置偏差。</p>
<p>CAM端也要从−X反向接到原中央段的+X切向。R7.5假设下，两端合计至少47.12 mm，中央段最多152.88 mm；这个上限还没扣除插入、补强和位置偏差，不代表新路径已通过。</p>
<p class="note">旧中央段的空间检查仍有效，但不能把它直接当成完整排线。需要重新分配中央段与端部长度；这不是“200 mm 原配线不够长”的结论。R5／R7.5 也不是厂家给定的弯曲限制。</p>
<table><tr><th>已经确定</th><th>仍未确定</th></tr><tr><td>同一俯仰组；官方已插线照片中的相机+Z及CAM屏幕−X方向；LCD原CAD入口侧；旧15 mm预算不足</td><td>所购批次、接触面／针1、完整型号、线宽厚、补强、插深及允许弯曲数据</td></tr></table>
<p>硬件 CAM-FPC-EXIT-R1 已正式接收并核对31份文件哈希。完整屏幕排线、相机FPC、固定及带线装配仍为 BLOCKED。没有修改打印件、孔位、BOM或视频。</p>
<p><a href="direction_receipt.json">硬件证据接收记录</a> · <a href="HARDWARE_HANDOFF">原始交接</a> · <a href="HARDWARE_MISSING">明确缺失的字段</a></p>
<p><a href="orientation/MORI_M1_49_CAM_FPC_orientation_hypotheses.blend">可编辑三组方向对照</a> · <a href="README.md">详细判断与限制</a> · <a href="pair_terminal_length_audit.json">双端长度必要条件</a> · <a href="terminal_length_audit.json">先前LCD单端计算</a></p>
<p class="small"><a href="review.json">原始模型提取</a> · <a href="orientation/review.json">几何变更范围</a> · <a href="commands.json">实际命令与日志</a> · <a href="main_integrity.json">主文件保留检查</a></p>
</main></html>'''
page=page.replace('PHOTO_CAMERA',relative['ESP32-S3-CAM-OVxxxx-details-5-2.jpg']).replace('PHOTO_IC',relative['esp32-s3-cam-ovxxxx-3_1.jpg'])
page=page.replace('PHOTO_CONNECTED',relative['use_msg_01.webp']).replace('HARDWARE_HANDOFF',relative['handoff.json']).replace('HARDWARE_MISSING',relative['missing_fields.csv'])
(OUT/'index.html').write_text(page)

main_delivery=read(HERE.parent/'neck_adoption/delivery.json')
protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for f,h in {**main_delivery['files'],**protected}.items():assert sha(ROOT/f)==h,f
ex=read(ROOT/'mechanical/reports/export_manifest.json')
for row in ex['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
animation=read(ROOT/'mechanical/animation/delivery.json')
for f,h in animation['files'].items():assert sha(ROOT/'mechanical'/f)==h,f
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),main_changed=False,
    config_sha256=sha(ROOT/'config/geometry.json'),main_files_checked=len(main_delivery['files']),
    protected_hardware_files_checked=len(protected),STL_files_checked=len(ex['parts']),
    animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))

flexpage=FLEX/'index.html';txt=flexpage.read_text()
txt=re.sub(r'<!-- CONNECTOR_DIRECTION_UPDATE -->.*?<!-- /CONNECTOR_DIRECTION_UPDATE -->','',txt,flags=re.S)
update='''<!-- CONNECTOR_DIRECTION_UPDATE --><section><h2>后续复核：入口方向与旧长度预算</h2><p>相机座重建朝向与已接线照片相反；CAM屏幕座不能一起翻转。LCD原CAD支持从−X接近，原先分配给屏幕端的15 mm不足以完成转向，需要重做完整路径。</p><p><a href="connector_faces/index.html">查看官方照片、当前模型与方向对照</a></p></section><!-- /CONNECTOR_DIRECTION_UPDATE -->'''
flexpage.write_text(txt.replace('</main>',update+'</main>'))
mainpage=BASE/'index.html';txt=mainpage.read_text()
txt=re.sub(r'<!-- FLEX_CONNECTOR_REVIEW -->.*?<!-- /FLEX_CONNECTOR_REVIEW -->','',txt,flags=re.S)
section='''<!-- FLEX_CONNECTOR_REVIEW --><section id="flex-connectors"><h2>新增：排线两端方向复核</h2><p>官方已插线照片支持相机+Z、CAM屏幕−X出线；相机重建应转向，CAM屏幕座则应单独修正入口，不可一起整只翻转。LCD原厂CAD也支持−X入口，旧中央170 mm＋两端各15 mm的分配需要重做。</p><p><a href="static_flex/connector_faces/index.html">看方向证据和独立模型对照</a> · <a href="static_flex/connector_faces/pair_terminal_length_audit.json">双端长度必要条件</a></p><p>硬件CAM-FPC-EXIT-R1已接收；主模型、打印件、STL和视频保持，完整线束仍未完成。</p></section><!-- /FLEX_CONNECTOR_REVIEW -->'''
mainpage.write_text(txt.replace('</main>',section+'</main>'))
state=read(BASE/'continuation_status.json')
state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT)))
state['flex_connector_review']=dict(status='PASS',scope='Evidence comparison; not actual interface qualification',
    camera_outlet='Photo shows +V/+Z; current reconstruction is opposite',
    CAM_display_outlet='Official connected photographs support -U/-X; preserve black/white layout while correcting entry independently',
    LCD_outlet='Vendor CAD appears to enter from world -X',
    prior_15mm_terminal_budget='FAIL under prior R5/R7.5 capacity assumptions',
    main_applied=False,report='static_flex/connector_faces/index.html')
state['flex_hardware_followup']=dict(thread_id='01a0c24f-ddc2-7f03-a9d4-d09dff26d30f',host_id='local',
    status='COMPLETED_RECEIVED',topic='CAM camera/display FPC entrance direction and remaining actual interface fields',
    source_files_modified=False,formal_pinmap_changes_authorized=False,no_supplier_contact=True,
    receipt='static_flex/connector_faces/direction_receipt.json',revision='CAM-FPC-EXIT-R1',files_checked=31,
    after_cursor='3e16a964-2dc3-4a56-9c50-9f67d321864e:18')
state['last_completed_independent_work']='Original connector extraction, unchanged-base CAM orientation comparisons, and conditional rejection of the old 15 mm LCD-end budget.'
state['next_work']=[x for x in state['next_work'] if not x.startswith(('Static LCD central-span','Receive hardware FPC-direction evidence.'))]
state['next_work'].append('CAM-FPC-EXIT-R1 received: camera +Z and display -X at zero pose. Reconstruct CAMERA orientation and DISPLAY outward entry separately in independent candidates; do not flip both full packages. Reallocate the old 170+15+15 screen cable model; actual contacts, insertion, width/thickness and material limits remain unknown.')
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json');assert not pub['C6_approved']
assets=[p for p in OUT.rglob('*') if p.is_file()]
assets += [HERE/s for s in ['inspect_flex_connector_faces.py','review_flex_orientation.py','audit_flex_terminal_length.py','receive_flex_direction_handoff.py','audit_flex_terminal_pair.py',Path(__file__).name]]
assets += [flexpage,mainpage,*refs.values()]
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in assets})
pub.update(utc=now,flex_connector_review='PASS for comparison only',full_LCD_FFC='BLOCKED',full_harness='BLOCKED',
    flex_connector_publisher_sha256=sha(Path(__file__)),flex_connector_publish_command=[sys.executable,*sys.argv])
write(BASE/'publication.json',pub)
print('FFC_CONNECTOR_REVIEW_PUBLISHED',len(commands),'commands',len(assets),'files')
