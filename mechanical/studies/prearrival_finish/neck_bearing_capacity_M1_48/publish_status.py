"""Publish the current unresolved outcome; preserve all historical evidence."""
from pathlib import Path
import json,hashlib,datetime,re
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
review=json.loads((HERE/'review.json').read_text())
detail=('完整线束仍未完成。较大内孔轴承C2候选能保留反力固定座孔壁并容纳11根局部导线，'
    '但整机运动复核发现支撑颈部与后壳、抬高的防脱压板与前后壳相交，限位接触角也需调整。'
    '因此尚未采用。原轴承四线/十一线切槽仍存在孔壁问题；两轮外绕局部筛查也未通过。'
    '各接口端部连接、真实线材和FFC、固定与应力释放、完整带线装配及供应商制作图仍未完成。')
p=BASE/'work_status.json';before={str(p):sha(p)};status=json.loads(p.read_text())
status['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
status['neck_bearing_capacity_M1_48']={
    'status':'BLOCKED','evidence':'neck_bearing_capacity_M1_48/index.html',
    'source_main_sha256':review['source_main_sha256'],'local_eleven_curves':'PASS',
    'socket_support_material_preserved':'PASS','complete_candidate_motion':'BLOCKED',
    'rigid_unwired_local_installation':'PASS','stop_contact_angle':'BLOCKED',
    'full_endpoints':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
    'manufacturing_release':False,'scope':'6806 boundary reference and three complete print candidates; not an adopted bearing change'}
for r in status['remaining']:
    if r['id']=='harness':
        r['detail']=detail;r['evidence']='neck_bearing_capacity_M1_48/index.html'
        r['latest_capacity_evidence']=r['evidence'];r['latest_capacity_detail']=detail
status['whole_head_harness_M1_48']['followup']='neck_bearing_capacity_M1_48/index.html'
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=BASE/'index.html';before[str(p)]=sha(p);text=p.read_text()
notice=('<aside id="larger-neck-capacity-update" class="notice"><b>当前仍剩5类到货前工作，完整线束是主要未完成项。</b> '
    '较大内孔轴承候选的局部通道通过，但整机运动会碰头壳，尚不能采用。'
    '<a href="neck_bearing_capacity_M1_48/index.html">查看本轮实体截面和结果</a>。'
    '其余为反力夹初装、未定采购件及安装、厂家传动与插接资料、质量与驱动预算。'
    '当前交付仍为M1.48 / M1.48-A1，下方保留历史研究。</aside>')
text=re.sub(r'<aside id="larger-neck-capacity-update".*?</aside>','',text,flags=re.S)
text=text.replace('<main>','<main>'+notice,1)
text=text.replace('<b>最新：跨颈通道需要重做，完整线束仍是主要未完成项。</b>',
    '<b>之前的原轴承通道：反力孔壁检查未通过。</b>')
text,count=re.subn(r'<tr><td>完整线束</td>.*?</tr>',
    '<tr><td>完整线束</td><td>BLOCKED<br>机械＋硬件线材输入</td><td>'+detail+
    ' <a href="neck_bearing_capacity_M1_48/index.html">当前依据</a></td></tr>',text,count=1,flags=re.S)
assert count==1;p.write_text(text)
p=BASE/'whole_head_harness_M1_48/index.html';before[str(p)]=sha(p);text=p.read_text()
notice=('<aside id="larger-bearing-followup" class="note"><b>后续整体复核：</b> '
    '较大内孔轴承候选保留了固定座孔壁，局部11线通过；但支撑与压板碰到头壳，仍未采用。'
    '<a href="../neck_bearing_capacity_M1_48/index.html">查看最新结果</a>。下方为原轴承切槽研究。</aside>')
text=re.sub(r'<aside id="larger-bearing-followup".*?</aside>','',text,flags=re.S)
text=text.replace('<main>','<main>'+notice,1);p.write_text(text)
(HERE/'status_amendment.json').write_text(json.dumps(dict(
    utc=status['updated_utc'],original_hashes=before,
    updated_hashes={p:sha(p) for p in before},main_applied=False,
    numerical_historical_reports_modified=False),ensure_ascii=False,indent=2)+'\n')
print('STATUS_UPDATED',len(before),'status/presentation files; five categories remain')
