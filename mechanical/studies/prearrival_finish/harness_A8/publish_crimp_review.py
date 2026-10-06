"""Attach newly retrieved guidance while preserving unresolved process status."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
data=json.loads((HERE/'crimp_guide_sources.json').read_text())
for name in ['JST_SPH004_crimp.pdf','JST_SSH003_crimp.pdf']:
    assert data['sources'][name]['content_review']=='PASS'
    assert hashlib.sha256((HERE/'sources'/name).read_bytes()).hexdigest()==data['sources'][name]['sha256']
block='''<section id="crimp-guides"><h2>新取得：JST压接工艺参考表</h2>
<p>已下载并查看PH、SH/SHL两份原厂指导表，补齐30 AWG对应的剥线长度、导体压接尺寸和拉力参考。原表日期为2001年，按端子系列列值；不是当前实际线材和完整端子型号的已批准工艺。</p>
<p><a href="CRIMP_REFERENCE.md">数值、来源、适用边界及供应商回签要求</a> · <a href="sources/JST_SPH004_crimp.pdf">PH原始PDF</a> · <a href="sources/JST_SSH003_crimp.pdf">SH/SHL原始PDF</a> · <a href="crimp_guide_sources.json">下载记录</a></p>
<p><strong>后续补查：</strong>已取得按完整料号查询的PH/SH工艺数据及JST官方的-H后缀说明。查询实际来自厂商公开的test-jst主机，生产站接口本次返回403；新旧数值差异和版本限制均已记录。<a href="TOOLING_DETAILS.md">完整料号、逐线规数据与仍缺事项</a> · <a href="tooling_lookup_sources.json">原始查询记录</a></p></section>'''
path=HERE/'index.html';text=path.read_text()
if 'id="crimp-guides"' in text:
    text=re.sub(r'<section id="crimp-guides">.*?</section>',block,text,flags=re.S)
else:
    text=text.replace('<h2>中间段通过，端部直行受阻</h2>',block+'\n<h2>中间段通过，端部直行受阻</h2>')
path.write_text(text)
path=HERE/'README.md';text=path.read_text()
marker='## 补充：压接工艺参考已找到'
if marker not in text:
    text+='\n'+marker+'\n\n已下载并逐页检查JST两份原厂压接指导表，参见[数值和供应商回签要求](CRIMP_REFERENCE.md)。这补齐系列工艺参考；对实际线材、完整端子后缀和模具的过程认可仍未完成，不能作为制造放行。\n'
path.write_text(text)
if 'TOOLING_DETAILS.md' not in text:
    text+='\n后续取得了完整料号的公开查询数据及-H后缀说明，见[逐线规工艺数据与来源限制](TOOLING_DETAILS.md)。\n'
    path.write_text(text)
path=PARENT/'work_status.json';work=json.loads(path.read_text())
work['A8_harness_research'].update(crimp_series_guidance='PASS',
    crimp_guidance_review='harness_A8/CRIMP_REFERENCE.md',specific_wire_terminal_process='BLOCKED')
work['A8_harness_research'].update(exact_terminal_tooling_reference='PASS',
    exact_terminal_tooling_review='harness_A8/TOOLING_DETAILS.md',
    tooling_reference_host='test-jst.jst.com; production query 403; per-record revision unavailable',
    SH_H_same_application_tooling_official_FAQ='PASS')
work['prearrival_wire_addendum'].update(JST_crimp_series_guidance_received='PASS',
    final_crimp_process_qualification='NOT_TESTED')
work['updated_utc']=datetime.now(timezone.utc).isoformat()
path.write_text(json.dumps(work,ensure_ascii=False,indent=2)+'\n')
print('A8_CRIMP_GUIDANCE_PUBLISHED')
