"""Publish only the new A6 receipt; preserve historical A3 and robot geometry."""
from pathlib import Path
import json,hashlib,datetime,html,re,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
d=read(HERE/'hardware_A6_J10_C3_receipt.json');assert d['status']=='PASS'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==d['main_sha256']
resolved=sum(m['status']=='PASS' for m in d['model_file_checks'])
unresolved=[m['reference'] for m in d['model_file_checks'] if m['status']=='BLOCKED']
page=HERE/'hardware_A6_J10_C3_review.html'
page.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI J10 C3 机械接收</title><style>body{background:#f3f5f4;color:#253b3c;font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:960px;margin:auto;padding:30px 22px 60px}h1{font-size:30px}h2{margin-top:30px}a{color:#166b70}aside{padding:16px 20px;background:#e0eee8;border-left:4px solid #4f8972}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #cdd8d4;text-align:left}code{overflow-wrap:anywhere}.pending{background:#fff0d5;border-color:#b58a33}</style><main>
<p><a href="index.html">返回打样前工作</a> · M1.47 独立候选接收</p><h1>J10 侧出线 C3：连通与原生规则检查通过</h1>
<aside>机械已从原生文件复核：112 个封装、280 个焊盘，以及板框、厚度、元件位置、面别、孔位和模型变换均与已检查的 C2/A3 相同。仍是独立候选，没有替换正式电源板或主模型。</aside>
<h2>这次完成了什么</h2><table><tr><th>项目</th><th>结果与范围</th></tr>
<tr><td>电气布线</td><td>收到 KiCad 10.0.6 原始 ERC / DRC 报告：0 / 0；未连接、原理图差异、忽略项均为 0。机械核对了报告输入的源文件哈希，没有重复宣称电气或温升认证。</td></tr>
<tr><td>走线视觉复核</td><td>硬件对话最新澄清：整板逐线、逐器件放大复核尚未全部完成，39 项形态提示尚未全部形成具体结论。提示数量不等于错误数量；DRC 清零不能代替用户要求的向外出线、无抖动和器件本体避让复核。</td></tr>
<tr><td>机械接口</td><td>原生逐项比对通过；80×55×1.6 mm 板框、孔位和 J10 1–8 针保持。D30/F70/R50 背面以及 JP70/TP71 位置保持 A3。</td></tr>
<tr><td>之前的空间检查</td><td>A3 背面包络、裸插头退出和局部工具占位检查的几何依据保持。带线取件、实际抓握和完整安装顺序尚未通过。</td></tr>
<tr><td>版本边界</td><td>正式电源板仍为 P5R6。PHC1 其他 PH 孔修正仍是独立候选，C3 未合并它。</td></tr></table>
<h2>还不能应用为已完成线束</h2><aside class="pending">需要实际插合后的出线高度、端子后直段、带线拔出与夹持空间。JP70/TP71 的装后直进维护通道仍受阻；装桥前可操作不等于装后可维护。背面器件的热与装配公差仍未实测。</aside>
<p>旧 A3/C2 的 26 处未连接和 14 条 DRC 警告属于历史源，保留记录；当前 C3 的原生布线报告已清零。旧 A3 的局部导线法线筛查也不被沿用为“路线不存在”的证明。</p>
<details><summary>模型来源检查的限制</summary><p>100 个模型引用及变换保持；''' + str(resolved) + ''' 个引用在本机可解析为相同数据。''' + str(len(unresolved)) + ''' 个原库引用两版均未解析（''' + ', '.join(unresolved) + '''），已逐项记录，不能据此声称全部器件获得精确厂家模型。此前主模型的已记录替代包络保持原有精度标签。</p></details>
<p><a href="hardware_A6_J10_C3_receipt.json">机械独立接收记录</a> · <a href="hardware_A6_followup.json">硬件后续澄清与回报记录</a> · <a href="../../../hardware/v1_2/j10_routing_C3_20261002/README.md">硬件 C3 原始交接</a> · <a href="J10_A3_review/index.html">保留的 A3 空间检查</a></p>
<p><small>PROTOTYPE / UNVALIDATED；采购和制造未放行。ERC/DRC 及名义几何通过不等于实际载流、温升、连接或整机安全验证。</small></p></main></html>''')

s=read(HERE/'work_status.json');row=next(r for r in s['remaining'] if r['id']=='hardware_selection');old=row['detail']
new='现成软轮胎未定型。已核对A6/C3的112封装、280焊盘及机械接口与A3相同，ERC/DRC/未连接为0；硬件整板逐线视觉复核仍未完成。背面包络及裸插头退出几何保持，真实出线、带线取件及装后JP70/TP71维护仍未定。C3与PHC1均未应用正式板或主模型。'
row['detail']=new;row['evidence']='hardware_A6_J10_C3_review.html';s['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
if not any(r['id']=='A6_J10_C3_receipt' for r in s['completed']):
    s['completed'].append(dict(id='A6_J10_C3_receipt',status='PASS',detail='C3原生112封装/280焊盘、板框厚度与模型引用/变换同A3；收到的ERC/DRC零项与实际输入哈希匹配，候选未应用。'))
s['prearrival_wire_addendum'].update(A6_C3_native_receipt='PASS',A6_C3_review='hardware_A6_J10_C3_review.html',A6_C3_applied=False,A6_C3_received_DRC='PASS')
write(HERE/'work_status.json',s)
p=HERE/'index.html';text=p.read_text().replace(old,new).replace(html.escape(old),html.escape(new))
text=text.replace('J10 A3最新复核','J10 A3历史复核').replace('带线拔插和J10候选布线仍未完成','带线拔插仍未完成；新 C3 候选连通与原生规则检查已通过').replace('新 C3 候选布线已收尾','新 C3 候选连通与原生规则检查已通过')
text=re.sub(r'<section id="J10-A6-update">.*?</section>','',text,flags=re.S)
text=text.replace('<main>','<main><section id="J10-A6-update"><h2>J10 最新交接</h2><p><a href="hardware_A6_J10_C3_review.html">C3 原生检查与机械接收</a>完成：电气规则检查清零，112 个封装与 280 个焊盘接口保持。整板逐线视觉复核及带线维护仍待完成，正式板和主模型保持。</p></section>',1)
p.write_text(text)

for target in [page,p]:
    for link in re.findall(r'(?:href|src)=["\']([^"\']+)',target.read_text()):
        if link.startswith(('http:','https:','#','data:','mailto:')):continue
        assert (target.parent/link.split('#')[0].split('?')[0]).resolve().exists(),(target,link)
    url='http://127.0.0.1:58201/'+str(target.relative_to(ROOT))
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as response: assert response.status==200
for mf in ['M1_47_delivery.json','harness_A2/delivery.json']:
    doc=read(HERE/mf)
    for target in [HERE/'work_status.json',p]:
        key=str(target.relative_to(ROOT))
        if key in doc['files']:doc['files'][key]=sha(target)
    write(HERE/mf,doc)
files=[page,HERE/'hardware_A6_J10_C3_receipt.json',HERE/'hardware_A6_followup.json',HERE/'receive_A6_J10_C3.py',HERE/'receive_A6_J10_C3.log',Path(__file__).resolve()]
write(HERE/'hardware_A6_delivery.json',dict(status='PASS',scope='A6 receipt artifacts and links only',
    source_main_sha256=d['main_sha256'],files={str(p.relative_to(ROOT)):sha(p) for p in files},
    command='KICAD10_3DMODEL_DIR=/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 mechanical/studies/prearrival_finish/receive_A6_J10_C3.py',
    main_geometry_changed=False,manufacturing_release=False))
print('A6_RECEIPT_PUBLISHED',page)
