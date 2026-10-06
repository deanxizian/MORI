# -*- coding: utf-8 -*-
"""Publish the isolated A2/C2 work while preserving the M1.47 model delivery."""
from pathlib import Path
import json,hashlib,datetime,html,shutil
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
val=read(HERE/'ecowire_validation.json');joint=read(HERE/'ecowire_joint.json')
preview=read(HERE/'preview_manifest.json');c2=read(PARENT/'J10_C2_review/review.json')
main=PROJECT/'mechanical/mori_v1_2.blend'
assert val['status']==joint['status']==preview['status']=='PASS'
assert sha(main)==val['source_blend_sha256']==c2['source_blend_sha256']==preview['source_main_sha256']
for row in preview['images']:assert sha(HERE/row['file'])==row['sha256']
assert sha(HERE/preview['candidate_blend'])==preview['candidate_sha256']
style='''*{box-sizing:border-box}body{margin:0;background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1080px;margin:auto;padding:30px 22px 60px}h1{font-size:30px}a{color:#146c53}h2{margin-top:34px}img{width:100%;border-radius:10px;background:#dbe0de}figure{margin:24px 0}figcaption{font-size:14px;color:#4c615a}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #c6d2cd;text-align:left}.notice{background:#fff1d7;padding:16px;border:1px solid #ddc494;border-radius:8px}.ok{background:#daeae1;border-color:#a3c5b4}code{overflow-wrap:anywhere}summary{cursor:pointer;font-weight:600}details{background:white;padding:14px;margin:16px 0;border-radius:8px}@media(max-width:700px){h1{font-size:24px}td,th{padding:7px;font-size:13px}}'''
lengths=''.join('<tr><td>%s</td><td>%.2f</td></tr>'%(x['id'],x['geometric_centerline_length_mm']) for x in joint['routes'])
gap=min(x['nominal_tessellated_solid_gap_mm'] for x in val['wire_to_wire'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 身体线束候选</title><style>{style}</style><main><a href="../index.html">返回到货前工作</a><h1>六根身体导线：已有可行试排</h1><p>M1.47 几何 · H01–H03 · 候选未应用到主模型</p><p class="notice ok">保留支架、孔位和接线针序，六根线联合间隙及130个头部姿态检查通过。没有增加打印件或走线孔。</p><p class="notice">完整线束仍未完成：插头内实际出线位置、线材选型/压接、应力释放、绑束与拆装松量仍待落实。这六根线只连接身体内两块固定板，不代表摆头线束已验证。</p><figure><img src="bridge_visible.png" alt="固定Yaw桥保持，六根候选导线从现有空间经过"><figcaption>固定Yaw桥保持；橙色为未选定线材及简化插头包络。</figcaption></figure><details open><summary>隐藏承重桥，查看针号与线路</summary><img src="bridge_hidden.png" alt="仅隐藏Yaw桥展示H01到H03六根导线，几何位置没有变化"><p>仅为显示隐藏承重桥，检查时使用了完整桥体。没有将桥移开来获得通过。</p></details><h2>这次用了哪些输入</h2><table><tr><th>线路</th><th>研究候选</th><th>最大外径</th><th>厂家5D对应半径</th></tr><tr><td>H01 5V连接</td><td><a href="https://www.alphawire.com/products/wire/ecogen/ecowire/6712">Alpha6712 / 24AWG</a></td><td>1.143mm</td><td>5.715mm</td></tr><tr><td>H02 / H03</td><td><a href="https://www.alphawire.com/products/wire/ecogen/ecowire/6711">Alpha6711 / 26AWG</a></td><td>1.016mm</td><td>5.08mm</td></tr></table><p>这两种线只是有厂家参数的候选，未采购或写入硬件正式选型。仍保留5mm端后直段分配。原A2中5853/5854的10D要求没有被缩小；按原要求做的有限路径搜索未通过，见<a href="static_screen.json">原参数结果</a>。</p><h2>检查覆盖与剩余事项</h2><p>六根封闭导线包络各自连续，与当前实体没有检出交叠；15对线间检查的最小表面间隙约{gap:.2f}mm。Yaw ±60°、Pitch −20°～25°共130个离散姿态无新增相交。有限姿态不是连续运动证明，未建模的线束仍会占空间。</p><ul><li>IMU八线的120组圆弧试排仍受后壳和弯段长度限制，需继续安排线路；未切壳开孔。</li><li>H05等待J10侧出C2的接触/出线资料；其他分支、头部FFC和有限服务环仍待处理。</li><li>固定点、接头拔插余量、板卡拆出和最终裁线长度尚未放行。</li></ul><details><summary>六根线的几何长度，不能按此裁线</summary><p>没有计入端子、剥线、应力释放和拆装松量。</p><table><tr><th>导线</th><th>几何中心线 mm</th></tr>{lengths}</table></details><p><a href="MORI_H01_H03_CANDIDATE_NOT_ADOPTED.blend">独立候选Blender</a> · <a href="ecowire_validation.json">实体/姿态检查</a> · <a href="ecowire_sources.json">来源与哈希</a> · <a href="REVIEW.md">完整说明</a></p><p>PROTOTYPE / UNVALIDATED · 主模型及装配视频仍为 M1.47 / M1.47-A1，未将候选线材混入正式装配。</p></main></html>'''
(HERE/'index.html').write_text(page)
c2rows=''.join('<tr><td>%s</td><td>%.2fmm</td><td>%.2fmm</td></tr>'%(r['reference'],r['supplied_back_depth_mm'],r['minimum_remaining_gap_lower_bound_mm']) for r in c2['backside'])
(PARENT/'J10_C2_review/index.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · J10 C2局部空间</title><style>{style}</style><main><a href="../index.html">返回到货前工作</a><h1>J10 C2：局部空间可以继续，带线拆装未完成</h1><p class="notice">独立候选 · 正式电源板P5R6与主模型未修改，C2未作为制造文件交付。</p><h2>两颗器件移到背面后的局部空间</h2><table><tr><th>器件</th><th>背面包络，含0.15mm分配</th><th>额外向下余量下界</th></tr>{c2rows}</table><p>包络每0.02mm向下移动检查，最先遇到Load_Frame。F70虽超出原3mm分配0.09mm，在这处仍有几何余量继续研究；这不扩大整板背面上限，不代表热或公差通过。</p><h2>拔插与导线</h2><p>PHR-8先沿−X退5.35mm，再向上12mm，两段连续盒体扫掠无交叠。该行程由包络分离关系加0.5mm分配得出，不是JST额定退出量。</p><p>导线按原A2的外径1.0922mm、半径10.922mm和端后5mm直段检查。实际出线高度未知：假定板顶上方2.4mm时，第2、3线被C66阻挡；假定3.6mm时局部转弯可以通过。因此仍要核实真实端子，不能把高度随意改成能通过的值。</p><p>8/10mm圆柱形直进夹持工具分配均被板面/器件阻挡，不能宣称已方便拔出。上方夹持、电子预装顺序和带线取出余量仍需检查。</p><p><a href="review.json">原始检查数据</a> · <a href="REVIEW.md">范围与限制</a></p><p>反馈已发送到既有硬件对话；未编辑其原生PCB。</p></main></html>''')

# Preserve the previous publication before updating the live work checklist.
archive=PARENT/'history_M1_47_before_wire_A2';archive.mkdir(exist_ok=True)
for name in ['index.html','work_status.json','M1_47_delivery.json']:
    if not (archive/name).exists():shutil.copy2(PARENT/name,archive/name)
status=read(PARENT/'work_status.json');old={r['id']:r.copy() for r in status['remaining']}
newtext='H01–H03六根线已有独立EcoWire6711/6712候选：实体、15对线间及130个头部姿态通过，未改支架；线材选型、端子出线、应力释放和拆装松量未定。IMU八线、J10 C2带线退出、头部FFC/服务环和其他分支尚未完成。'
for row in status['remaining']:
    if row['id']=='harness':row.update(detail=newtext,evidence='harness_A2/index.html')
    if row['id']=='hardware_selection':row['detail']='现成软轮胎尚未定型；A2增补已收到。J10 C2改为插头单独退出并把D30/F70作为背面候选，局部背面空间及裸插头扫掠通过；线材/夹持/电气设计仍待完成，正式电源板与机械模型未替换。'
status['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
status['prearrival_wire_addendum']=dict(status='BLOCKED',static_H01_H03_geometry='PASS',adopted=False,
    review='harness_A2/index.html',J10_C2_review='J10_C2_review/index.html',main_geometry_changed=False)
(PARENT/'work_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
top=(PARENT/'index.html').read_text()
for row in status['remaining']:
    prev=old[row['id']]
    top=top.replace(html.escape(prev['detail']),html.escape(row['detail'])).replace(prev['detail'],row['detail'])
    if row['id']=='harness':top=top.replace('href="J10_A2_REVIEW.md">依据','href="harness_A2/index.html">依据')
marker='<h2>到货前线束检查进展</h2>'
if marker not in top:
    top=top.replace('<h2>仍需完成</h2>',marker+'<p>H01–H03六根身体导线已有保持支架的名义试排，<a href="harness_A2/index.html">查看候选与检查范围</a>。<a href="J10_C2_review/index.html">J10 C2局部复核</a>已反馈硬件；带线拔插仍未完成。两个研究都没有替换主模型。</p><h2>仍需完成</h2>')
(PARENT/'index.html').write_text(top)

# Refresh only current generated-document hashes. Preserve all geometry and
#animation hashes; they must still match the previous delivery record.
delivery=read(PARENT/'M1_47_delivery.json')
changed={'mechanical/studies/prearrival_finish/work_status.json'}
for path,digest in delivery['files'].items():
    actual=sha(PROJECT/path)
    assert path in changed or actual==digest, 'Unexpected delivery drift: '+path
    if path in changed:delivery['files'][path]=actual
delivery['documentation_addendum']='harness_A2/delivery.json'
(PARENT/'M1_47_delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
print('WIRE_REVIEW_PUBLISHED',sha(main),flush=True)
