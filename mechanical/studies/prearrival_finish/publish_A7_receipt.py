"""Publish the new receipt without replacing historical receipts or hardware."""
from pathlib import Path
import json, hashlib, datetime, html, re, urllib.request
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
d=read(HERE/'hardware_A7_J10_C4_receipt.json')
assert d['status']=='PASS' and sha(ROOT/'mechanical/mori_v1_2.blend')==d['main_sha256']
page=HERE/'hardware_A7_J10_C4_review.html'
style='body{background:#f3f5f4;color:#253b3c;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:960px;margin:auto;padding:30px 22px 60px}h1{font-size:30px}h2{margin-top:30px}a{color:#166b70}aside{padding:16px 20px;background:#fff0d5;border-left:4px solid #b58a33}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #cdd8d4;text-align:left}small{color:#5f6e70}'
page.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI C4 与头部接线资料接收</title><style>'''+style+'''</style><main>
<p><a href="index.html">返回打样前工作</a> · M1.47 独立资料接收</p>
<h1>C4 走线复核已交付，机械接口保持</h1>
<p>从 C3、C4 原生文件独立比对了 <b>112 个封装、280 个焊盘、147 个过孔</b>，位置、孔径、面别、针序、模型变换、80×55×1.6 mm 板框均保持。正式电源板仍为 P5R6；C4 和 PHC1 都是独立候选，未应用主模型。</p>
<table><tr><th>检查</th><th>本次结果</th></tr>
<tr><td>电源板走线视觉复核</td><td>收到硬件方的39条逐项记录：5条已修正、24条有具体保留理由、10条误报；另有70条本体引出说明和104器件覆盖表。6处局部修改有前后图。范围仅电源板C3/C4，不能扩展为其他三板重新通过。</td></tr>
<tr><td>原生规则报告</td><td>收到ERC / DRC / 未连接 / 原理图一致性 / 忽略项均为0，输入文件哈希匹配；27条负载路径报告通过。机械没有代替硬件重新做电气资格认定。</td></tr>
<tr><td>源文件完整性</td><td>249个正式文件、C3源和两份交付文件清单逐项哈希检查通过。100个模型引用中90个解析一致；原来8个XT30和2个保险丝库模型仍缺失，未伪称全部精确建模。</td></tr>
<tr><td>已有机械检查</td><td>A3的背面包络与裸插头退出几何依据保持。实际出线、带线抓握/拔插和装后JP70/TP71维护仍未解决。</td></tr></table>
<h2>头部线材不能直接沿用研究样本</h2>
<aside>SH候选端子 SSH-003T-P0.2-H 的目录绝缘外径范围为 <b>0.4–0.8 mm</b>；此前 Alpha5853 样本为 <b>0.889–1.0922 mm</b>，不能直接压接。现有H06研究依赖尚未选定的厂配细尾线及接续。实际接头系列、料号和配套线仍未确认。</aside>
<p>收到37行相机、UART、喇叭和舵机电气针脚对应资料；物理插合方向均仍标为待确认。CAM相机座是24P、0.5 mm节距、2.0 mm连接器高度，这个高度不是FPC厚度。完整OV3660排线长度、接触面及厂家支持的延长方式仍缺。</p>
<p>SCS0009原厂资料的p4尾线表与p8示例针号顺序存在视图疑问；不能自行镜像猜接。USB供电尾线和源端CC接法、LCD排线宽厚与弯曲参数也仍待定。资料检索无结果不代表相应产品不存在。</p>
<p><a href="../../../hardware/v1_2/reviews/J10_C3_visual_20261003/review.html">硬件C4对比图与记录</a> · <a href="hardware_A7_J10_C4_receipt.json">机械独立接收记录</a> · <a href="../../../hardware/v1_2/head_harness_evidence_20261003/README.md">头部接线证据</a> · <a href="head_harness/index.html">机械走线研究</a></p>
<p><a href="hardware_A6_J10_C3_review.html">历史A6/C3接收</a> · <a href="J10_A3_review/index.html">历史A3空间检查</a></p>
<p><small>PROTOTYPE / UNVALIDATED。采购、制造和完整线束未放行；主模型与装配动画保持。</small></p></main></html>''')
s=read(HERE/'work_status.json'); old_new=[]
row=next(r for r in s['remaining'] if r['id']=='hardware_selection')
new='现成软轮胎未定型。A7/C4已核对112封装、280焊盘、147过孔及机械接口同C3/A3；收到电源板39项视觉处置、70条引出说明和ERC/DRC零项报告。真实出线、带线取件及装后JP70/TP71维护仍未定。C4与PHC1均未应用正式板或主模型。'
old_new.append((row['detail'],new));row.update(detail=new,evidence='hardware_A7_J10_C4_review.html')
row=next(r for r in s['remaining'] if r['id']=='supplier_interfaces')
new='SCS0009舵盘/短轴锁紧及线序视图、S288输出自攻螺钉、WeAct E孔针与插接长度、PHR8真实出线仍缺。A7补齐37行头部电气针脚及SH/GH目录候选；实际插合视图、相机完整FPC、USB尾线和压接过渡未确定，不能按目录候选冒充实物配套。'
old_new.append((row['detail'],new));row.update(detail=new,evidence='hardware_A7_J10_C4_review.html')
s['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
entry=dict(id='A7_J10_C4_receipt',status='PASS',detail='C4原生112封装/280焊盘/147过孔接口保持；249正式文件和交付清单核对通过，电源板视觉复核及头部37行针脚证据已收到。实际线束仍未定型，候选未应用。')
s['completed']=[r for r in s['completed'] if r['id']!=entry['id']]+[entry]
s['prearrival_wire_addendum'].update(A7_C4_native_receipt='PASS',A7_C4_review='hardware_A7_J10_C4_review.html',
    A7_C4_applied=False,A7_received_power_visual_review='PASS',A7_head_pinmap_rows=37,
    actual_SH_GH_parts_and_cavity_views='BLOCKED',Alpha5853_direct_SH_crimp='FAIL')
write(HERE/'work_status.json',s)
p=HERE/'index.html';text=p.read_text()
for old,new in old_new:text=text.replace(old,new).replace(html.escape(old),html.escape(new))
for section in ['J10-A6-update','J10-A7-update']:
    text=re.sub('<section id="'+section+'">.*?</section>','',text,flags=re.S)
text=text.replace('<main>','<main><section id="J10-A7-update"><h2>电源板和头部接线最新交接</h2><p><a href="hardware_A7_J10_C4_review.html">C4机械接收完成</a>：112封装、280焊盘、147过孔接口保持；收到电源板逐项视觉复核。实际头部尾线及带线维护仍待定，候选未应用。</p></section>',1)
p.write_text(text)
checks=[]
for target in [page,p]:
    for link in re.findall(r'(?:href|src)=["\']([^"\']+)',target.read_text()):
        if link.startswith(('http:','https:','#','data:','mailto:')):continue
        assert (target.parent/link.split('#')[0].split('?')[0]).resolve().exists(),(target,link)
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:58201/'+str(target.relative_to(ROOT)),method='HEAD'),timeout=10) as r:
        assert r.status==200
    checks.append(str(target.relative_to(ROOT)))
for name in ['M1_47_delivery.json','harness_A2/delivery.json']:
    doc=read(HERE/name)
    for target in [HERE/'work_status.json',p]:
        key=str(target.relative_to(ROOT))
        if key in doc['files']:doc['files'][key]=sha(target)
    write(HERE/name,doc)
files=[page,HERE/'hardware_A7_J10_C4_receipt.json',HERE/'receive_A7_J10_C4.py',
       HERE/'receive_A7_J10_C4.log',HERE/'receive_A7_J10_C4_API_retry.log',
       HERE/'receive_A7_J10_C4_record_retry.log',Path(__file__).resolve()]
write(HERE/'hardware_A7_delivery.json',dict(status='PASS',scope='A7 receipt artifacts and links only',
    source_main_sha256=d['main_sha256'],files={str(p.relative_to(ROOT)):sha(p) for p in files},
    command='KICAD10_3DMODEL_DIR=/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 mechanical/studies/prearrival_finish/receive_A7_J10_C4.py',
    local_links_checked=checks,main_geometry_changed=False,manufacturing_release=False))
print('A7_RECEIPT_PUBLISHED')
