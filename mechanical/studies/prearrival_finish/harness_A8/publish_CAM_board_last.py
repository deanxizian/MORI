"""Publish source boundaries and a still-incomplete board-last assembly study."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,re,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_board_last'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=read(OUT/'screen.json');verify=read(OUT/'verification.json');render=read(OUT/'render_manifest.json')
source_hash=sha(ROOT/'mechanical/mori_v1_2.blend')
assert screen['status']=='PASS' and verify['status']=='BLOCKED' and render['status']=='PASS'
assert len(screen['rows'])==16 and all(r['status']=='PASS' for r in verify['rigid_sweeps'])
assert [r['screw'] for r in verify['driver_access'] if r['status']=='BLOCKED']==['CAM_Mount_Screw_0']
assert render['physical_parts_preserved_unchanged']==209
gap=min(r['wire_gap_bound_mm'] for r in screen['rows']);radius=min(r['curve']['minimum_radius_bound_mm'] for r in screen['rows'])
detail='CAM板后装候选：16个位置的四线等长、弯曲和间隙检查通过，板卡与插头的6mm连续刚性路径通过；但下方一枚CAM螺钉被俯仰舵机挡住，现有直柄工具无法锁紧。完整工序与裁线图仍未完成，主模型未改。'
md=f'''# 已有公开资料与CAM板后装研究

供应商按图制作已经确定，不再等待用户选择制作方式。完整线束图仍未完成；本页把公开资料、机械设计和实物验证分开列明。

## 能查到的资料

| 项目 | 已取得的厂家资料 | 还不能据此声称什么 |
|---|---|---|
| JST SH | [官方目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)：SHR-04V-S、SSH-003T-P0.2-H、尺寸、线规及绝缘外径 | 不能据此认定微雪板端就是JST原厂插座 |
| JST PH | [官方目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)：PHR-4、SPH-004T-P0.5S及适用范围 | 不能把不同端子型号的压接要求混用 |
| 压接工艺 | [PH系列指导表](https://www.jst-india.com/downloads/series/SPH-004-P0.5S.pdf)、[SH系列指导表](https://www.jst-india.com/downloads/series/SSH-003-02_SSHL-003-02_2.pdf)及[完整料号查询记录](../TOOLING_DETAILS.md) | 指导值不等于所选线材、工具组合已通过工艺验证 |
| 微雪CAM | [V1.1原理图](https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf)标有SH1.0四针UART接口 | 未给出完整插座厂牌料号及真实线端针腔视图 |
| SCS0009 | [厂家规格书](https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf)及项目留存的[参考STEP说明](../../supplier_made_harness/SOURCE_REVIEW.md) | 参考STEP不含原配舵盘；厂家网页25T与20T标法仍不一致，未冻结采购版次的传动接口 |

线长、分支、固定点和整机带线装配顺序由MORI项目设计，供应商目录不会提供这些尺寸。此前取得的文件和失败检索都保留在[公开资料复查](../../supplier_made_harness/recheck_20261004/README.md)。此次未获得能直接关闭实际CAM插座或舵盘缺项的新图纸。

## 更换装配顺序的独立尝试

原工序将CAM板固定在头托后，把整组下放42mm，受导线折回限制。本候选先让头托到位，再将CAM板暂时抬高6mm，插头从下方向上插合，最后板卡落座。四枚CAM安装螺钉暂不安装，四个嵌件留在头托。

![CAM板临时抬高6mm](board_raised6.png)

图中只展示四根头部候选线段；颜色用于区分几何槽位，不是电气针序或最终线色。实际CAM插座、照片估算元件和两处未批准的扎带座仍保持原有证据限制。

| 检查 | 结果 |
|---|---|
| 7个板卡落座位置、9个插头进入位置 | 16个均PASS；完整曲线按离散位置检查，不是连续柔性运动证明 |
| 每根线的总长度 | 解析保持不变，不向身体侧凭空借42mm余线 |
| 最小曲率半径保守下界 | {radius:.4f}mm，超过本次筛查值6.9342mm |
| 已检查位置的导线表面间距下界 | {gap:.4f}mm，达到0.3mm要求 |
| CAM板与插头6mm连续刚性平移 | 各原始元件起止外凸包覆盖整段平移，未发现外部碰撞 |
| 板卡落座后的四枚螺钉工具 | 3处PASS；CAM_Mount_Screw_0的直柄PH1刀杆穿过Pitch_Servo，BLOCKED |

为保全真实空腔，连续板卡检查按原始132个组件索引逐件处理（排除自身UART互配件后为131件），没有把整板与背面元件之间的空隙当成实心。互配插座内的名义插合接触不作为外部障碍物；这不验证实际插入力或插合深度。

![剩下的直柄工具阻挡](screw_tool_obstruction.png)

红色仅表示直径4mm、长60mm的直柄刀杆检查体。不是新零件，也不是打印件的切孔建议。另一个80mm长刀杆同样受阻。该失败只针对这两种直柄工具，不证明所有弯头工具或装配次序都不可能。

因此本候选没有批准为最终装配工序。下一步需要先解决这枚螺钉的工具/先后顺序，再闭合裸端穿线、线形形成、两处扎带收紧以及其余头部线、USB和相机FPC。最终裁线长度仍不发布。

## 保留的42mm滑动候选

另一个[独立检查](../cam_sliding_departure/screen.json)允许CAM端直线段随42mm下放缩短，15个姿态及[连续上部导线检查](../cam_sliding_departure/continuous_upper_wires.json)通过；但需要身体侧每根提供42mm余线。共同PH插头的暂存及全长守恒尚未闭合，不能据此声称完整装配可行。

主模型M1.47、config、STL、动画和正式硬件均未更改。没有新增永久零件，也没有订货、联系供应商或发布制造图。实体装配、PA12配合、压接和动态寿命仍需实物验证。

[独立Blender](review.blend) · [16个位置](screen.json) · [连续刚性路径及工具](verification.json) · [命令记录](commands.json) · [交付清单](review_manifest.json)
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 公开资料与CAM后装</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f4f6f5;color:#253b3d;max-width:1040px;margin:28px auto;padding:0 24px 60px}}a{{color:#096a74}}h1{{font-size:30px}}.note{{background:#fff0d9;padding:18px;border-radius:10px}}img{{width:100%;border-radius:8px}}figure{{margin:24px 0}}figcaption{{font-size:14px}}td,th{{padding:12px;border-bottom:1px solid #cad7d2;text-align:left}}table{{border-collapse:collapse;width:100%}}</style>
<p><a href="../../index.html">← 当前未完成项</a> · <a href="../index.html">A8研究</a> · <a href="../cam_tail_ribbon/index.html">上轮：临时扎带尾端</a></p>
<h1>资料可以查到；完整线束设计还要继续完成</h1>
<p class="note">供应商按图制作已确定。标准连接器与压接参考已取得；本轮CAM后装候选的16个导线位置检查通过，但一枚固定螺钉的直柄工具仍受阻。主模型M1.47未改，最终线束图未放行。</p>
<h2>已取得的公开资料</h2>
<p><a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH</a>、<a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST PH</a>的胶壳、端子、线规和尺寸已找到；<a href="../CRIMP_REFERENCE.md">压接指导</a>及<a href="../TOOLING_DETAILS.md">完整料号查询记录</a>也已保留。微雪<a href="https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf">CAM V1.1原理图</a>写明SH1.0四针UART，但未提供完整插座厂牌料号及线端针腔视图。</p>
<p>SCS0009有规格书和参考STEP；原配舵盘图、采购版次及部分互配细节仍未取得。详见<a href="../../supplier_made_harness/recheck_20261004/README.md">资料复查</a>。线长、固定点和完整装配工序由MORI项目设计，不能一并归为等厂家资料。</p>
<h2>先装头托，再装CAM板</h2><p>板卡暂抬6mm，插头从下方进入，再让板卡落座。头部线环变窄以补偿插头直线段增长，每根线总长度保持不变。四枚CAM螺钉留到最后锁紧，原有嵌件不动。</p>
<figure><img src="board_raised6.png" alt="CAM板抬高6毫米的独立装配候选"><figcaption>只展示头部四线候选段；颜色不代表电气针序。头托、舵机及支座位置不变。</figcaption></figure>
<table><tr><th>检查</th><th>结果与范围</th></tr><tr><td>导线</td><td>16个位置通过；逐根等长，曲率半径下界{radius:.3f}mm，表面间距下界{gap:.3f}mm</td></tr><tr><td>板卡/插头落座</td><td>6mm连续刚性路径通过；不代表连续柔性运动或实际插合认证</td></tr><tr><td>固定工具</td><td>3处通过；下方CAM_Mount_Screw_0被俯仰舵机挡住</td></tr></table>
<figure><img src="screw_tool_obstruction.png" alt="CAM固定螺钉的直柄刀杆与俯仰舵机相交"><figcaption>红色为直柄刀杆检查体。两种已检查直柄工具受阻；没有删除舵机或为它新增避让孔。</figcaption></figure>
<h2>尚未完成的设计</h2><p>先解决这枚螺钉的工具或工序，再接通裸端穿线、线形形成与两处扎带收紧。其余头部导线、USB、相机FPC和最终裁线图也仍未完成。本候选尚未采用。</p>
<p>另一个42mm滑动路线的上部导线检查通过，但身体侧共同PH插头和余线暂存未闭合，因此也不能作为完整工序。所有实物压接、动态寿命与打印配合保持待验证。</p>
<p><a href="README.md">完整说明与来源</a> · <a href="screen.json">16个位置</a> · <a href="verification.json">刚性路径和工具检查</a> · <a href="review.blend">独立Blender</a> · <a href="commands.json">实际命令</a> · <a href="review_manifest.json">交付清单</a></p></html>'''
(OUT/'index.html').write_text(html)
for suffix,dest in [('', 'screen.log'),('_verify','verification.log'),('_render','render.log')]:shutil.copyfile('/tmp/mori_CAM_board_last'+suffix+'.log',OUT/dest)
commands=[f'/Applications/Blender.app/Contents/MacOS/Blender --background {blend} -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/{script}' for blend,script in [
    ('mechanical/mori_v1_2.blend','check_CAM_board_last.py'),('mechanical/mori_v1_2.blend','verify_CAM_board_last.py'),('mechanical/studies/prearrival_finish/harness_A8/cam_wired_cradle/review.blend','render_CAM_board_last.py')]]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},indent=2)+'\n')
p=PARENT/'work_status.json';state=read(p);row=next(r for r in state['remaining'] if r['id']=='harness');old=row['detail']
if not (OUT/'previous_work_status.json').exists():shutil.copyfile(p,OUT/'previous_work_status.json')
row.update(detail=detail,evidence='harness_A8/cam_board_last/index.html');state['updated_utc']=datetime.now(timezone.utc).isoformat()
state['A8_harness_research'].update(latest_review='harness_A8/cam_board_last/index.html',CAM_board_last_wire_positions='PASS',CAM_board_last_position_count=16,
    CAM_board_last_constant_lengths='PASS',CAM_board_last_rigid_continuous_paths='PASS',CAM_board_last_straight_driver='BLOCKED',
    CAM_board_last_blocked_screw='CAM_Mount_Screw_0',CAM_board_last_review='harness_A8/cam_board_last/index.html',
    CAM_sliding_departure_upper_continuous='PASS',CAM_sliding_departure_body_reserve='NOT_TESTED',CAM_whole_connected_installation='BLOCKED')
p.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old in s;s=s.replace(old,detail).replace('harness_A8/cam_tail_ribbon/index.html','harness_A8/cam_board_last/index.html').replace('最新：CAM临时扎带尾端','最新：CAM板后装与剩余工具阻挡');p.write_text(s)
for p,link in [(A8/'index.html','cam_board_last/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_board_last/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_board_last/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM板后装与工具阻挡</h2><p>{detail}</p><p><a href="{link}">查看资料与装配检查</a></p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM板后装候选</h2><p>{detail}</p><p><a href="{link}">查看资料与装配检查</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM板后装候选](cam_board_last/index.html)：16个等长导线位置和6mm刚性连续路径通过，但下方一枚CAM螺钉的直柄工具受阻；完整工序未完成，主模型未改。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
(OUT/'review_manifest.json').write_text(json.dumps({'status':'PASS','scope':'Publication and evidence consistency only; complete installation BLOCKED','script_sha256':sha(SCRIPT),
    'source_main_sha256':source_hash,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==source_hash
print('CAM_BOARD_LAST_PUBLISHED',len(files),flush=True)
