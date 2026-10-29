"""Archive R147 trials and adopt only verified L PCB into independent development; no publication or manufacturing."""
import csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';candidate=b/'R147L';evidence=dev/'evidence/R147L';study=dev/'evidence/R147_study';base=Path('robot/.state/c3-completion/baseline');backup=Path('robot/.state/c3-completion/baseline_R145I_before_R147L')
old='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c';new='6816b9c5783e5a699f5d3f1d0d102914269d37d6d756ef5158ed1b0b3fa129b6';board='MORI_Interface_C3.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(source/board)==old and sha(candidate/board)==new
assert not evidence.exists() and not study.exists() and not backup.exists()
result=json.loads((b/'R147L-verify/result.json').read_text());planned=json.loads((b/'R147L-planned-delta.json').read_text());reg=json.loads((b/'R147L-verify/regression.json').read_text());metrics=json.loads((b/'R147L-local-metrics.json').read_text());inspection=json.loads((b/'R147L-inspection.json').read_text());plan=json.loads((b/'R147L-plan.json').read_text())
assert (result['board_sha256'],result['unconnected_items'],result['violations'],result['schematic_parity'],result['erc_violations'])==(new,27,0,0,0)
assert planned['status']=='PASS' and len(planned['checks'])==2581 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert sum(x['status']=='FAIL' for x in reg['reference_transitions'])==6
assert metrics['same_face_body_hits']==0 and not inspection['same_face_nominal_body_intersections']
assert json.loads((b/'R147-guard-checks-v2/result.json').read_text())['status']=='PASS'
assert json.loads((b/'R147-previous-plan-review.json').read_text())['status']=='PASS'
members=sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and p.name not in [board,'MORI_Interface_C3.kicad_prl']);assert len(members)==77
for p in members:assert (base/p).read_bytes()==(source/p).read_bytes()==(candidate/p).read_bytes(),str(p)
all_source={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
old_status=json.loads((dev/'STATUS.json').read_text());assert old_status['board_sha256']==old
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();now=datetime.now(timezone.utc).isoformat()
# All seven named PNGs were actually viewed in this turn; these are native-geometry diagnostics.
images=['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','R145I-B.Cu']
for name in images:assert (b/'R147L-views'/(name+'.png')).is_file()
evidence.mkdir();study.mkdir()
for p in (b/'R147L-verify').iterdir():shutil.copy2(p,evidence/p.name)
for src,name in [('R147L-plan.json','plan.json'),('R147L-planned-delta.json','planned-delta.json'),('R147L-local-metrics.json','local-metrics.json'),('R147L-inspection.json','inspection.json'),('R147L-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/name)
shutil.copytree(b/'R147L-views',evidence/'images')
review_by_ref={
'C1601':'Inner gate branch projects below the fixed VS bypass capacitor; In4 lies between In3 and B. C1601 and its short VS/GND connection remain unchanged.',
'D1601':'D1001 K back trace projects opposite the fixed front enable diode; In4 coverage is continuous and the accepted D1601/ARMED/EN connections are retained.',
'Q1601':'Gate inner branch and back-face WHEEL/IN-/LIMIT traces project below the fixed power MOSFET. In1/In4 ground separation and unchanged source/drain copper were checked; no asserted transient or temperature qualification.',
'Q1602':'D1001 K back trace projects below the fixed power MOSFET. In4 coverage and the original source/drain connections are retained; Q1602 gate remains unconnected.',
'R1101':'Back-face gate and WHEEL sense approaches project below the front shunt. The original shunt, sense via and power copper remain; continuous In4 reference is verified. Thermal drift and transient coupling remain open.',
'R805':'Back-face gate RC trace projects below the front eFuse ILM resistor. The front ILM components and wiring are unchanged, with intervening In4 ground; noise injection/ILM behavior still needs engineering validation.',
'U1601':'Back gate-clamp and D1001 K traces project below the front controller. In4 reference coverage and existing controller-net connectivity are verified; this is not switching-waveform qualification.'}
projection_groups=sorted({(h['reference'],r['net'],r['layer']) for r in metrics['new_tracks'] for h in r['nominal_body_projections']})
assert all(ref in review_by_ref for ref,net,layer in projection_groups)
visual={'board_sha256':new,'local_status':'PASS','whole_board':'NOT_TESTED','images_actually_viewed':[{'path':'images/'+n+'.png','status':'PASS','scope':'Native-geometry local diagnostic; rendered in a separate process and actually viewed.'} for n in images],
'findings':['Q1601 gate and U1601 GATE are joined to the existing clamp/RC group. Q1602 gate remains separate.','C1602 moved 1.35 mm down; R1601 moved 2.4 mm right, retaining its original orientation. R1701 and R1707 are placed as a horizontal pair with short pin approaches.','Sampling escape follows the actual rounded pad before turning; no new same-face nominal body intersection remains.','Obsolete inner gate branch and two obsolete non-ground transfers removed; two new transfers installed. No ground via moved.','Inner gate branch stays above the CAM distribution region. All 50 power-width and 155 ground-pad checks remain valid.','Native owner BODY guards follow the explicit part transforms; R1601 retains the unchanged global via cutouts. No rules, exclusions or unrelated keepouts are relaxed.'],
'projection_review':[{'reference':ref,'net':net,'layer':layer,'review':review_by_ref[ref],'reference_screen':'PASS','coupling_and_thermal':'NOT_TESTED; scoped layout separation reviewed, final engineering qualification remains open.'} for ref,net,layer in projection_groups],
'limits':['Local six-layer review only; whole-board per-track/per-via review is unfinished.','Nominal Fab/fallback geometry is not a manufacturer maximum envelope or physical measurement.','C1602 body separation improves in plan view only; no measured temperature/capacitance qualification.','Six historical reference-transition flags remain.'], 'physical':'NOT_TESTED','manufacturing_release':False}
write(evidence/'visual_review.json',visual)
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for i,x in enumerate(json.loads((evidence/'drc.json').read_text())['unconnected_items'],1):w.writerow([i,x['description'],' | '.join(y['description'] for y in x['items'])])
# Preserve all R147 scripts, raw failures, reports, test boards and rendered evidence without copying complete trial projects repeatedly.
payloads=[]
def preserve(src,rel):
 data=src.read_bytes();compressed=src.suffix=='.kicad_pcb' or len(data)>524288
 dest=study/rel
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True)
 assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compressed})
trials=[]
for p in sorted(b.glob('R147*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif p.name in ['R147'+x for x in 'ABCDEFGHIJKL']:
  if (p/board).exists():
   preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
   row={'revision':p.name,'board_sha256':sha(p/board),'adopted':p.name=='R147L'}
   d=b/(p.name+'-drc.json')
   if d.exists():row.update({k:len(v) for k,v in json.loads(d.read_text()).items() if k in ['unconnected_items','violations','schematic_parity']})
   trials.append(row)
 else:
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
preserve(Path(__file__),Path('archive_and_adopt_R147.py'))
write(study/'summary.json',{'source_revision':'R145I','source_sha256':old,'adopted_revision':'R147L','adopted_sha256':new,'candidates':trials,'R147H':'Preparation assertion rejected an unlisted placement; no candidate PCB was built. Both error logs retained.','remaining_unconnected_items':27,'remaining_connectivity_fraction':.675,'not_engineering_progress':True,'manufacturing_release':False})
(study/'README.md').write_text('''# R147：栅极、RC 与电流采样联合布局

仅 L 经完整核对后采用到独立开发入口：28 → **27 项未连接**，相对最初 40 项剩 **67.5%**。发布仍 R108P；此比例不是工程或时间完成率。

- A/B 的电容、RC 和换层位置碰到原生铜/孔或供电；失败资料保留。
- C/D/E 逐步恢复 D1001 K 和参考地。E 虽为 27 opens / 0 other DRC，但 RC 两项邻接距离超标，且正面出线擦过本体，未采用。
- F 的新孔碰正面分流电阻，R1707 位移碰 U1701；内层路径割裂 CAM。G 把内层路径放到 CAM 区域上方并恢复供电，但 R1701 太远、庭院相碰且有旧支线悬空，未采用。
- 单移 R1701 的有限搜索没有位置；成组移动 R1701/R1707 得到几何候选。H 的准备断言拒绝了未在结果中的位置，没有生成板。I 消除其他 DRC，但采样线参考地有两处缺口。
- J/K 的电气与邻接回归通过，实际圆角焊盘之外仍有微小同面本体投影，未采用。L 调整采样出线及门极孔，消除投影并保留原参考地。
- L 删除 32 段旧铜、新增 42 段；删两只失去换层作用的旧门极孔、新增两孔，总 1278 段 / 322 孔 / 215 器件。Q1602 栅极仍未连接。

[接收证据](../R147L/README.md)包含原生 DRC/ERC、2581 项精确计划核对及实际查看的六层局部图。原始失败、命令、计划、脚本和原生板在本目录归档；大文件/板使用 gzip，manifest 同时记录压缩文件与原始字节哈希。完整试验工程仍留在本机 `.state`。

构建工具新增双重显式选择的“旋转器件且保持原过孔窗口固定”支持；7 项原生保存/重读与拒绝对照通过，R145I 的 2535 项旧计划重放通过。该旋转功能仅用于未采用候选；L 的 R1601 采用原朝向平移，不把工具能力当作规则豁免。

布置依据为 [TI LM74502 数据手册](https://www.ti.com/lit/ds/symlink/lm74502.pdf) SNOSDE5A Rev A §11.1：栅极靠近 MOSFET、合适供电铜、VCAP 电容避开 MOSFET 热影响。项目 5/3 mm 邻接筛查不是手册规定值。C1602 平面距离改善不构成热验证。

全板逐线逐孔、六项历史回流提示、电源/热/耦合、机械/线束与实物资格继续保持未完成；没有制造导出、设备操作或发布合并。
''')
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads})
for r in payloads:
 p=study/r['path'];assert sha(p)==r['sha256'];data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==r['source_sha256']
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'all_stored_and_original_byte_hashes_match':True})
# Preserve every native member and UI extra before changing only the PCB.
shutil.copytree(source,backup,copy_function=shutil.copy2);assert {p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}==all_source
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for rel,digest in all_source.items():
 if rel!=board:assert sha(source/rel)==digest
write(evidence/'adoption.json',{'adopted_at_utc':now,'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,'member_checks':[{'member':str(p),'sha256':sha(source/p)} for p in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status=dict(result);status.update({k:v for k,v in old_status.items() if k.startswith('remaining_')})
status.update({'revision':'C3 R147L','status':'INDEPENDENT_DEVELOPMENT_CANDIDATE','published_revision':'C3 R108P','adopted_in_main_model':False,'previous_candidate':'C3 R145I','previous_candidate_sha256':old,'strict_regression_explanation':'Raw audit retains FAIL for four explicit part transforms and owner guards, 32 replaced tracks and two removed obsolete vias. Exact planned-delta review passes 2581 checks; old connections, power, adjacency and reference regression pass. This is local development evidence, not whole-board or physical qualification.','step_regression_status':'FAIL','planned_delta_review_status':'PASS','planned_delta_check_count':2581,'electrical_regression_status':'PASS','local_visual_review':'PASS','local_visual_review_explanation':'Six local native layers and source back-face comparison actually viewed; zero new same-face nominal body hits. Thermal/coupling and whole-board qualification remain open.','whole_board_route_style':'NOT_TESTED','new_same_face_nominal_body_projection_groups':0,'segment_count':1278,'via_count':322,'footprint_count':215,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.675,'connectivity_fraction_is_not_engineering_progress':True,'remaining_ACT_GATE_groups':2,'goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
(evidence/'README.md').write_text('''# C3 R147L 独立开发接收

2026-10-27：已采用到 `development/native`，**27 项未连接、0 其他 DRC、0 图板差异、0 启用项 ERC**。相对原 40 项消除 13 项，剩余连通数量比例 67.5%；工程仍 FAIL / PROTOTYPE / UNVALIDATED。发布仍 R108P，机械与软件未采用，不可制造。

PCB SHA256：`6816b9c5783e5a699f5d3f1d0d102914269d37d6d756ef5158ed1b0b3fa129b6`。

Q1601/U1601 GATE 与 D1602/R1601 组接通，Q1602.4 仍独立。C1602 下移 1.35 mm；R1601 右移 2.4 mm、朝向不变；R1701 改为 `(42.5,10.6)` / 0°，R1707 为 `(42.5,12.15)` / 0°。D1001 K 旧支路恢复。删除 32 段旧铜、新增 42 段；两只旧门极孔退出、两只新孔进入，总 1278 段 / 322 孔 / 215 器件。源过孔、全部地孔、固定连接器、板框及非关联规则保留；器件自有 BODY 区随明确变换更新，R1601 原全局过孔窗口保持。

- [原生结果](result.json)、[实际验证命令](commands.json)、[构建命令](build_commands.json)。
- [2581 项精确计划核对](planned-delta.json)、[原始回归](regression.json)：旧焊盘连接、50 项供电铜宽、155 地焊盘、63 邻接、新旧参考地通过；6 项历史换参考面提示未关闭。原始冻结几何审计因显式改动仍保留 FAIL。
- [局部六层审查](visual_review.json)、[逐段投影](local-metrics.json)、[剩余连接](remaining_connections.csv)、[77 非 PCB 原字节核对](adoption.json)。
- C1602 对两只 MOSFET 的名义平面本体距离约 1.20 / 1.43 mm，仅作布局代理。实际温升、容值偏置、耦合、瞬态、全板审查与机械/实物资格未完成。

[前序失败与工具测试](../R147_study/README.md)保留全部失败证据。下一步继续 Q1602 栅极、FAULT/ARMED、采样输入等剩余网络；不能把本次局部接通写成整个保护或接口板已验证。
''')
print(json.dumps({'adopted':'R147L','unconnected':27,'remaining_fraction':.675,'exact_plan_checks':2581,'archive_payloads':len(payloads),'non_pcb_source_members_unchanged':77,'goal_complete':False}))
