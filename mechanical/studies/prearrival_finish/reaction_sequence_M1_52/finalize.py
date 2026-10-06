"""Record the unresolved current assembly dependency without changing CAD."""
from pathlib import Path
import datetime,hashlib,json,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=sha(M/'mori_v1_2.blend');base=read(OUT.parent/'reaction_access_M1_51/delivery.json')
assert source==base['source_blend_sha256']
# All the delivered model, documentation, exports and video remain untouched.
assert all(sha(ROOT/p)==h for p,h in base['files'].items())
prep=read(OUT.parent/'reaction_access_M1_51/preparation.json')
assert all(sha(ROOT/p)==h for p,h in prep['protected_hardware'].items())
initial=read(OUT/'initial.json');translation=read(OUT/'translation_search.json');tilt=read(OUT/'tilt_search.json')
plot=read(OUT/'plot_receipt.json');witness=read(OUT/'witness_sections.json')
assert all(d['source_blend_sha256']==source for d in [initial,translation,tilt,plot,witness])
assert len(initial['vertical_paths'])==6 and all(r['status']=='BLOCKED' for r in initial['vertical_paths'])
assert len(translation['rows'])==9 and translation['status']=='BLOCKED'
assert len(tilt['rows'])==96 and tilt['status']=='BLOCKED'
assert sha(OUT/'blocked_paths.png')==plot['image_sha256']
assert sha(OUT/'witness_sections.json')==plot['sections_sha256']
for script,data in [('check_initial.py',initial),('search_translation.py',translation),('search_tilt.py',tilt),('capture_witnesses.py',witness),('plot_witnesses.py',plot)]:
    assert sha(OUT/script)==data['script_sha256']
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
report_text=f'''# M1.52 上部夹口初装复核

**仍为 BLOCKED，没有可直接应用的结构或装配方案。** 主模型及已发布装配视频保持 M1.52 / M1.52-A1，未混入 C6、导线约束候选或其他结构修改。

本次只使用当前主模型原件，在离机、舵机/轴承/身体尚未安装的条件下，先检查夹口连杆与头部转动座的必要装入条件。实际配套舵盘、中心锁紧件和夹紧载荷仍未定型；通过这些局部条件也不能等同于真实整机可装配。

| 已检查的路径 | 当前结果 |
|---|---|
| 裸连杆、带夹口螺钉螺母、再带舵盘，分别上下直进 | 6种情况均受阻；向上约1.75mm、向下约16mm首次检出连杆与转动座相交 |
| 小幅前后偏移后上提 | 9条有限路径均受阻 |
| 前后偏移与X轴倾斜组合后上提 | 96条有限路径、1478个实际位置均未找到可用路径 |
| 下部横向锁紧 | 前一轮已通过名义螺母、螺钉及工具进入检查，本次未撤回，也未扩大为上部初装通过 |

![实际局部剖面](/Users/dean/Documents/MORI/mechanical/studies/prearrival_finish/reaction_sequence_M1_52/blocked_paths.png)

这些是明确范围内的失败证据，**不是所有复杂操作路径都不可能的证明**。目前不把继续扩大路径搜索或直接切薄支架当作已定型方案。先取得SCS0009配套舵盘及锁紧叠层尺寸，再一次性确定夹口外形、穿入方向和拧紧入口，可以避免围绕占位件反复修改。

单独连杆的螺母进入检查通过。试配螺钉在初始座位检测到约0.00000325mm³网格相交，低于这类模型实际尺寸不确定性，但本检查没有通过调整孔径来抹掉它，也没有据此宣称真实螺纹配合通过；原始值保留在initial.json。

继续所需输入仍是：C6现有开口加宽0.8mm的结构确认，以及配套舵盘/线端/排线等厂家接口资料。C6只影响线束，不能单独解决本页夹口初装。供应商问题单已有本地稿，尚未发送；当前没有新增联系厂家、采购或制造授权。

主模型SHA256：`{source}`。硬件{len(prep['protected_hardware'])}个文件和M1.52交付记录中的文件逐项保持。整机目标尚未完成。

生成时间：{stamp}。全部尺寸单位mm，+Y向前、+Z向上。原始记录：initial.json、translation_search.json、tilt_search.json、witness_sections.json。
'''
(OUT/'README.md').write_text(report_text)
commands=[]
for script,log in [('check_initial.py','initial.log'),('search_translation.py','translation_search.log'),('search_tilt.py','tilt_search.log'),('capture_witnesses.py','witness_sections.log')]:
    commands.append(dict(command=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','4','--python-exit-code','1','--python',str((OUT/script).relative_to(ROOT))],
        cwd=str(ROOT),returncode=0,log=str((OUT/log).relative_to(ROOT)),log_sha256=sha(OUT/log),script_sha256=sha(OUT/script)))
commands.append(dict(command=[sys.executable,str(OUT/'plot_witnesses.py')],cwd=str(ROOT),returncode=0,script_sha256=sha(OUT/'plot_witnesses.py')))
evidence=list(OUT.glob('*.py'))+list(OUT.glob('*.json'))+[OUT/'README.md',OUT/'blocked_paths.png']
evidence=[p for p in evidence if p.name!='closure_review.json']
out=dict(status='BLOCKED',scope='No accepted solution for the unresolved upper reaction initial assembly; finite diagnostics are complete',
         revision='V1.2-M1.52',source_blend_sha256=source,recorded_utc=stamp,commands=commands,
         previous_delivery_files_unchanged=True,protected_hardware_unchanged=True,
         protected_hardware_files=len(prep['protected_hardware']),current_native_geometry_changed=False,
         main_applied=False,C6_applied=False,full_harness='BLOCKED',actual_horn_and_locking_stack='BLOCKED',
         physical_fit='NOT_TESTED',manufacturing_release=False,files={str(p.relative_to(ROOT)):sha(p) for p in evidence})
(OUT/'closure_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
audit=read(OUT.parent/'goal_block_audit.json')
previous=audit['current_goal_turn_classification'];prior_count=audit['consecutive_impasse_turns']
audit.update(previous_goal_turn_classification=previous,current_goal_turn_classification='no progress',
             current_goal_turn_note='Current-source bench diagnostics did not close a required blocker or change the next dependency. Reported as no progress toward overall completion, not a successful assembly.',
             consecutive_impasse_turns=(prior_count+1 if previous=='no progress' else 1),goal_status='active',
             completion_proven=False,geometry_changed=False,hardware_changed=False,manufacturing_release=False,
             last_revalidated_utc=stamp,current_diagnostic='reaction_sequence_M1_52/closure_review.json')
audit['live_state_checks'].update(hardware_snapshot_cursor='7bd539b2-4981-4852-b2c7-b1b5beace384:1',
    hardware_thread_state='notLoaded',hardware_latest_turn_state='completed',hardware_result='Unchanged terminal snapshot; no new handed-off result.',
    supplier_messages_sent=False,C6_approval='PENDING')
audit['remaining_requirements'][0]['evidence']='reaction_sequence_M1_52/closure_review.json'
(OUT.parent/'goal_block_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_DIAGNOSIS_RECORDED; main unchanged; required blocker remains; no-progress count',audit['consecutive_impasse_turns'],flush=True)
