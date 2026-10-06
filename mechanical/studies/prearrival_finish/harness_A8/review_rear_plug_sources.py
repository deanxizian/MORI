"""Record PHR-5 source evidence without substituting a smaller envelope."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'rear_plug_source_review';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
family=OUT/'JST_DE_PH_family.html';product=OUT/'JST_DE_PHR5.html'
assert family.stat().st_size==314791 and product.stat().st_size==29767
assert 'PHR-5' in product.read_text() and '/produkt/3526/680902-00' in family.read_text()
pdf=A8.parent/'supplier_made_harness/recheck_20261004/JST_PH.pdf'
assert pdf.read_bytes().startswith(b'%PDF-')
assert sha(pdf)=='447624f4f2f7d37c58c1eaa7ee314ad757fe7aff48f6186491ef6f69fbc00b96'
source_script=ROOT/'mechanical/studies/prearrival_preparation/check_mated_connectors.py'
source=source_script.read_text()
assert 'Conservatively enclose full4.8mm native header height; PHR actual4.5mm.' in source
assert 'size=np.array([(n-1)*2+3.8,4.8,6.85])' in source
text='''# 后接口板 J2 / PHR-5 来源复核

官方PH目录列出PHR-5，节距2mm、5位、两端孔跨度8mm，胶壳外宽11.8mm；侧视标注4.5mm与6.85mm。
这些是目录名义尺寸，没有到货测量。来源为已归档的原厂PH目录，本轮没有取得更完整的逐型号插合剖面或STEP。

当前模型是11.8×6.85×4.8mm的保守长方体分配：厚度方向4.8mm来自原生直角板座完整高度；生成脚本已明确写明实际PHR胶壳名义4.5mm。
胶壳相对板座的准确插合位置与凸筋细节仍未定。不能仅把4.8改成4.5就判定通过，也没有修改接口位置或忽略重叠。

本次通过系统curl实际读取了[JST德国PH系列页](https://jst.de/product-family/show/119/ph)和
[PHR-5产品页](https://jst.de/produkt/3526/680902-00)，两页HTTP200；产品页无逐型号图纸、STEP或PDF下载链接。
公共[原厂PH目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)继续作为名义尺寸来源。
未提交表单、未发送供应商消息、未做采购或制造放行。

后续装配检查保留原保守包络；先比较外壳动作与拔插时机。若取得准确插合CAD，再以有来源的刚体替换，不通过缩放硬件消除干涉。
'''
(OUT/'README.md').write_text(text)
report=dict(status='PASS',scope='PHR-5 nominal source and existing conservative-envelope audit only',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    source_files={str(p.relative_to(ROOT)):sha(p) for p in [family,product,pdf,source_script]},
    retrieved_pages=[dict(url='https://jst.de/product-family/show/119/ph',http_status=200,file=family.name,transport='macOS curl with normal certificate verification'),
                     dict(url='https://jst.de/produkt/3526/680902-00',http_status=200,file=product.name,transport='macOS curl with normal certificate verification')],
    nominal_housing_dimensions_mm=[11.8,4.5,6.85],current_conservative_dimensions_mm=[11.8,4.8,6.85],
    dimension_evidence='VENDOR_DOCUMENTED nominal catalogue; no physical measurement',
    exact_mated_envelope='BLOCKED',complete_CAD_retrieved=False,
    source_package_unchanged=True,main_applied=False,contact_submitted=False,manufacturing_release=False,
    outputs={'README.md':sha(OUT/'README.md')})
(OUT/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('REAR_PHR5_SOURCE_AUDIT PASS; exact mating shape BLOCKED; original envelope retained')
