"""Publish a scoped, unapplied CAM entry correction and preserve execution evidence."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
FACES=BASE/'static_flex/connector_faces';OUT=FACES/'correction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
review=read(OUT/'review.json');views=read(OUT/'closeup_review.json')
assert review['status']=='PASS' and views['status']=='PASS'
assert not review['main_changed'] and not review['adopted']
assert len(review['sibling_checks'])==262 and not review['sibling_failures']
assert not review['new_interferences'] and review['poses']==130
commands=[]
for script,log,result,token,blend in [
 ('review_cam_fpc_correction.py','cam_fpc_correction.log','review.json','CAM_FPC_CORRECTION_DONE PASS',ROOT/'mechanical/mori_v1_2.blend'),
 ('render_cam_fpc_entries.py','cam_fpc_entry_views.log','closeup_review.json','CAM_FPC_ENTRY_VIEWS_DONE',OUT/'MORI_M1_49_CAM_corrected_entries.blend')]:
    s=HERE/script;l=BASE/log;r=read(OUT/result);txt=l.read_text()
    assert token in txt and 'Blender quit' in txt and 'Traceback' not in txt
    assert sha(s)==r['script_sha256']
    for name,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/name)==h,name
    for image in r['images']:assert sha(OUT/image['file'])==image['sha256']
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background',str(blend.relative_to(ROOT)),'-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),
        result=str((OUT/result).relative_to(ROOT)),result_sha256=sha(OUT/result),check_status=r['status']))
failures=[]
for file in sorted((OUT/'failures').glob('*.json')):
    row=read(file)
    if 'script_snapshot' not in row:row['script_snapshot']=str((file.parent/row.pop('script')).relative_to(ROOT))
    if not row['log'].startswith('mechanical/'):row['log']=str((file.parent/row['log']).relative_to(ROOT))
    assert row['exit_code']!=0 and sha(ROOT/row['log'])==row['log_sha256']
    assert sha(ROOT/row['script_snapshot'])==row['script_sha256']
    failures.append(row)
write(OUT/'commands.json',dict(status='PASS',utc=now,commands=commands,failed_executions=failures,
    scope='Two successful executions; four failed intermediate script executions retained, not geometric failures',script_sha256=sha(Path(__file__))))
write(OUT/'visual_review.json',dict(status='PASS',utc=now,reviewed_images=[r['file'] for r in review['images']+views['images']],
    findings=['Camera opening faces toward SD; the reconstructed body was rotated without changing bounds.',
        'Display opening is visible at the board edge; white outboard housing and black inboard actuator remain.',
        'Gold fingers and slot interiors remain illustrative and unnumbered.'],
    exact_contact_geometry='BLOCKED',main_applied=False,photos_edited=False))
resources=read(OUT/'research/current_vendor_files.json');assert resources['status']=='PASS'
write(OUT/'research/search_notes.json',dict(status='BLOCKED',utc=now,scope='Bounded exact-product documentation search; not proof that no further data exists',
    sources=[
      dict(url='https://docs.waveshare.com/1.85inch_Touch_LCD_Module/Resources-And-Documents',result='Official resources link to schematic and module STEP/DXF/PDF; no separate FFC manufacturing drawing listed on this page.'),
      dict(url='https://github.com/waveshareteam/1.85inch-Touch-LCD-Module/tree/main/dimensions',result='Current official STEP and dimension PDF LFS hashes match retained local files; see current_vendor_files.json.'),
      dict(url='https://www.waveshare.com/catalog/product/view/id/8439/s/1.85inch-touch-lcd-module/category/346/',result='Official search-indexed packing list: 18PIN,0.5mm pitch,200mm,same-direction FFC. Exact product page direct fetch returned403 in this review; no live stock or price claim.')],
    stock_listing_fields=dict(pins=18,pitch_mm=.5,length_mm=200,contact_faces='same direction',source_basis='Official indexed product listing'),
    unresolved=['cable thickness and width tolerance','stiffener lengths and endpoint no-bend zones','actual connector mouth height and insertion depth',
        'allowed radius and torsion for this cable','factory OV3660 full FPC length, profile and reinforcement'],
    not_borrowed='Different 20PIN HDMI cable dimensions and other display cables are not applied.',
    manufacturing_release=False))
readme='''# CAM 排线入口修正模型

这是独立检查模型；主装配、源参数、打印件、STL 和装配视频仍保持 M1.49 C5＋K1。修正可在后续统一交付中并入主模型，不需要为照片明确的入口方向另行更改结构。

- 相机 CAMERA_FPC_24：原模型朝下，修正为朝 SD 卡方向（机械零位 +Z）。以现有中心将原重建包体转 180°，不改变其外包络。
- 屏幕 DISPLAY_FPC_18：保留白色壳体在板外、黑色拨片在板内的照片关系，仅将示意入口改到板外（−X）。不能将整只插座转 180°。
- 其余 130 个板内元件组的顶点和面保持；板卡、安装孔、打印结构位置保持。

两处新增加材料与同板其他元件进行 262 组检查；另检查 130 个头部姿态下新增材料与其余刚性件的相交，未检出新增相交。比较体积前合并重叠的示意子实体，避免重复计体积。检查不包含真实插接、接触面、插深或拉力。

槽口高度、宽度及触点是明确标注的 ASSUMED 示意，不能用来决定真实排线中心、厚度或端部。完整排线和带线装配仍为 BLOCKED。主模型 C5＋K1 的采用不包含 C6 或导线约束候选。

当前官方屏幕 STEP、尺寸 PDF 与项目留存文件内容哈希一致。官方商品索引列出 18P／0.5 mm／200 mm 同面 FFC，但本次未取得其补强片、厚度和弯曲规范。上一轮路径约在假定插座包络外 2.6 mm 开始弯曲；这一条件必须与实际补强区核对。检索记录只说明本次范围，不能宣称厂家不存在更多资料。
'''
(OUT/'README.md').write_text(readme)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CAM 排线入口修正</title>
<style>body{font:16px/1.7 system-ui;background:#f3f6f7;color:#253844;margin:0}main{max-width:1160px;margin:auto;padding:26px 24px}h1{font-size:30px}h2{margin-top:34px}.note{padding:14px 18px;background:#fff0d2;border-left:5px solid #b88228}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}figure{margin:0;background:white;padding:12px;border-radius:9px}img{width:100%;height:auto}a{color:#146887}figcaption{font-size:14px}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:10px;border-bottom:1px solid #d4dee4}</style><main>
<p><a href="../index.html">入口证据</a> · <a href="../../full_route/index.html">完整排线空间候选</a> · <a href="../../../index.html">线束总进展</a></p>
<h1>两处入口方向已修正，包体位置和尺寸保持</h1><p class="note">独立检查模型，尚未并入主装配。主模型、STL 和视频仍为 M1.49 C5＋K1。内部触点及槽口尺寸属于估算；这不是完整的真实插接模型。</p>
<h2>相机口：朝 SD 卡方向出线</h2><div class="grid"><figure><a href="before_camera_entry.png"><img src="before_camera_entry.png" alt="修正前相机插座"></a><figcaption>修正前：示意入口朝下。</figcaption></figure><figure><a href="corrected_camera_entry.png"><img src="corrected_camera_entry.png" alt="修正后相机插座"></a><figcaption>修正后：以原中心旋转 180°，入口朝 SD 卡；外包络不变。</figcaption></figure></div>
<h2>屏幕口：朝板外出线</h2><div class="grid"><figure><a href="before_display_entry.png"><img src="before_display_entry.png" alt="修正前屏幕插座"></a><figcaption>修正前：内部示意开口错误地朝向板内。</figcaption></figure><figure><a href="corrected_display_entry.png"><img src="corrected_display_entry.png" alt="修正后屏幕插座外侧入口"></a><figcaption>修正后：外侧入口可见，白壳和黑拨片的位置保持。槽口和金色触点为未编号示意。</figcaption></figure></div>
<h2>核对范围</h2><table><tr><th>项目</th><th>结果</th></tr><tr><td>其余板内元件</td><td>130 个元件组的顶点、面保持。</td></tr><tr><td>同板元件新增相交</td><td>262 组比较未检出新增相交。</td></tr><tr><td>头部运动</td><td>130 个离散姿态，新增材料未与其他刚性件相交。</td></tr><tr><td>真实排线配合</td><td>BLOCKED：型号、接触面、补强区、插深和弯曲规范仍缺。</td></tr></table>
<p>当前官方发布的屏幕 STEP 和尺寸 PDF 与项目文件一致。<a href="https://docs.waveshare.com/1.85inch_Touch_LCD_Module/Resources-And-Documents">官方资源页</a>及其链接目录没有列出单独的 FFC 制造图；<a href="https://www.waveshare.com/catalog/product/view/id/8439/s/1.85inch-touch-lcd-module/category/346/">官方商品索引</a>提供 18P、0.5 mm、200 mm 同面线信息，未取得补强区和允许弯曲尺寸。这里只描述本次检索范围。</p>
<p class="note">上一轮排线路径仅在假定包络外约 2.6 mm 处开始弯曲。新的示意槽口不能替代真实接口尺寸，不能据此放行该路径。</p>
<p><a href="MORI_M1_49_CAM_corrected_entries.blend">下载可编辑修正模型</a> · <a href="README.md">详细说明</a> · <a href="review.json">几何检查</a> · <a href="commands.json">执行与保留失败记录</a> · <a href="research/search_notes.json">资料检索边界</a> · <a href="research/current_vendor_files.json">官方文件比对</a> · <a href="main_integrity.json">主模型保留核验</a></p></main></html>'''
(OUT/'index.html').write_text(page)
main_delivery=read(HERE.parent/'neck_adoption/delivery.json');protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for file,h in {**main_delivery['files'],**protected}.items():assert sha(ROOT/file)==h,file
exports=read(ROOT/'mechanical/reports/export_manifest.json');animation=read(ROOT/'mechanical/animation/delivery.json')
for row in exports['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
for file,h in animation['files'].items():assert sha(ROOT/'mechanical'/file)==h,file
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,main_changed=False,main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),
    config_sha256=sha(ROOT/'config/geometry.json'),main_files_checked=len(main_delivery['files']),protected_hardware_files_checked=len(protected),
    STL_files_checked=len(exports['parts']),animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))
for page,url in [(BASE/'index.html','static_flex/connector_faces/correction/index.html'),(FACES/'index.html','correction/index.html')]:
    text=page.read_text();text=re.sub(r'<!-- CAM_FPC_CORRECTION -->.*?<!-- /CAM_FPC_CORRECTION -->','',text,flags=re.S)
    section=f'<!-- CAM_FPC_CORRECTION --><section><h2>后续：CAM 入口修正模型</h2><p>相机入口朝 SD 卡、屏幕入口朝板外；保留包体外包络和其余元件。262 组同板比较、130 个姿态未检出新增相交，真实插接仍未完成。主模型未替换。</p><p><a href="{url}">查看入口侧前后对比</a></p></section><!-- /CAM_FPC_CORRECTION -->'
    assert '</main>' in text;page.write_text(text.replace('</main>',section+'</main>'))
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT)))
state['last_completed_independent_work']='CAM camera and display entry correction reviewed: unchanged package bounds,262 sibling checks,130 poses,editable candidate and closeups. Official current LCD CAD hashes match retained files.'
state['CAM_entry_correction']=dict(status='PASS',main_applied=False,source='static_flex/connector_faces/correction/review.json',actual_mating='BLOCKED')
state['next_work']=[x for x in state['next_work'] if not x.startswith('Correct the independently evidenced CAM camera')]
state['next_work']+=['Known CAM entry correction is ready in an independent model. Integrate it with a versioned delivery after keeping the current harness baseline reproducible; no printed structure approval is implied.',
    'Exact-product resource refresh found unchanged LCD CAD/dimension drawing. Do not repeat the same search without new evidence; stiffener/insertion/bend data are still absent from inspected sources.']
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json');assert not pub['C6_approved']
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix not in ['.blend1','.pyc']]
files += [HERE/n for n in ['cam_fpc_entry_geometry.py','review_cam_fpc_correction.py','render_cam_fpc_entries.py',Path(__file__).name,'verify_remaining_publication.py']]
files += [BASE/'index.html',FACES/'index.html',BASE/'cam_fpc_correction.log',BASE/'cam_fpc_entry_views.log']
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in files})
pub.update(utc=now,CAM_entry_correction='PASS independent candidate only',CAM_entry_main_applied=False,
    CAM_correction_publish_command=[sys.executable,*sys.argv],CAM_correction_publisher_sha256=sha(Path(__file__)))
write(BASE/'publication.json',pub)
print('CAM_FPC_CORRECTION_PUBLISHED',len(commands),'commands',len(failures),'preserved failures',len(files),'files')
