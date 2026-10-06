"""Attach the new support finding to current status and historical study pages.

Earlier numerical reports remain intact; explicit follow-up notices narrow the
scope of their PASS results. This never changes native source geometry.
"""
from pathlib import Path
import json,datetime,re,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
review=json.loads((HERE/'review.json').read_text())
p=BASE/'work_status.json';status=json.loads(p.read_text());before={str(p):sha(p)}
detail=('完整线束仍未完成。新11线局部路线在130姿态下通过共存检查，但通道会切穿反力固定座孔壁，不能采用。'
        '补查此前CAM四线通道，固定座顶部也有同类孔壁问题，需先修改通道。R19.5/R20.5外绕的首轮288条局部候选碰防脱压板或电源板。'
        '完整端部连接、身体端应力释放、固定/收紧、完整带线装配、另7根线及FFC、供应商制作图仍未完成；所有通道和固定座候选均未应用。')
status['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
status['whole_head_harness_M1_48']={
    'status':'BLOCKED','scope':'Local routing plus newly added support review; not an assembled harness',
    'evidence':'whole_head_harness_M1_48/index.html','source_main_sha256':review['source_main_sha256'],
    'eleven_local_paths':'PASS','channel_host_support':'BLOCKED','prior_four_line_socket_support':'BLOCKED',
    'outside_bearing_screen':'BLOCKED','outside_bearing_local_candidates':288,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
for r in status['remaining']:
    if r['id']=='harness':
        r['detail']=detail;r['evidence']='whole_head_harness_M1_48/index.html'
        r['latest_support_review_evidence']=r['evidence']
        r['latest_support_review_detail']=detail
for key in ['yaw_service_M1_48','cam_retention_M1_48']:
    status[key]['socket_support_followup']='BLOCKED'
    status[key]['socket_support_evidence']='whole_head_harness_M1_48/index.html'
    status[key]['prior_PASS_scope_note']='Historical route/fixation/limited assembly checks remain scoped; they did not qualify reaction socket support.'
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')

updates=[]
for folder in ['yaw_service_M1_48','cam_retention_M1_48']:
    p=BASE/folder/'index.html';before[str(p)]=sha(p);text=p.read_text()
    notice=('<aside id="socket-support-followup" class="note"><b>后续支座复核：此候选暂不能采用。</b> '
        '反力固定座顶部被通道局部切开，需先修正。下方 PASS 仅适用于所列线路、固定或局部装配检查，未覆盖固定座承载。'
        '<a href="../whole_head_harness_M1_48/index.html">查看新增截面对比</a>。</aside>')
    text=re.sub(r'<aside id="socket-support-followup".*?</aside>','',text,flags=re.S)
    assert '<main>' in text;text=text.replace('<main>','<main>'+notice,1);p.write_text(text);updates.append(str(p))

p=BASE/'index.html';before[str(p)]=sha(p);text=p.read_text()
notice=('<aside id="whole-neck-support-update" class="notice"><b>最新：跨颈通道需要重做，完整线束仍是主要未完成项。</b> '
        '新11线及之前4线候选都发现反力固定座局部孔壁问题；尚未应用主模型。'
        '<a href="whole_head_harness_M1_48/index.html">查看原件与候选截面对比</a>。</aside>')
text=re.sub(r'<aside id="whole-neck-support-update".*?</aside>','',text,flags=re.S)
text=text.replace('<main>','<main>'+notice,1)
pattern=r'<tr><td>完整线束</td>.*?</tr>'
replacement='<tr><td>完整线束</td><td>BLOCKED<br>机械＋硬件线材输入</td><td>'+detail+' <a href="whole_head_harness_M1_48/index.html">当前依据</a></td></tr>'
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S);assert n==1
pattern=r'<tr id="head-front-contact">.*?</tr>'
replacement=('<tr id="head-front-contact"><td>相机支架上沿及 CAM 螺钉</td><td>PASS<br>已应用 M1.48</td>'
    '<td>按用户确认完成上沿降低0.6mm和四枚M2×5内六角螺钉替换，局部、运动与工具检查已完成。'
    '<a href="camera_cam_adoption/index.html">当前交付</a>；本项不再属于待办，实物配合仍待验证。</td></tr>')
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S);assert n==1
text=text.replace('限位、装入和前壳/支架连续合拢路径通过，其他208件保持。待确认后应用，主模型尚未修改。',
    '原独立候选的限位、装入和连续合拢检查通过；用户已确认，本项现已应用 M1.48，见页面上方当前交付。')
p.write_text(text);updates.append(str(p))
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reason='New support check narrows prior local PASS claims and corrects a stale completed-camera status row.',
    original_hashes=before,updated_hashes={str(p):sha(p) for p in [BASE/'work_status.json']+[Path(x) for x in updates]},
    numerical_historical_reports_modified=False,main_applied=False)
(HERE/'status_amendment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('STATUS_UPDATED',len(before),'presentation/status files; geometry unchanged')
