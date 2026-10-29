"""Archive rejected R146 studies without changing the accepted PCB or project."""
import gzip,hashlib,json,shutil
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
dest=Path('robot/hardware/driver/development/evidence/R146_study');dest.mkdir(exist_ok=False)
canonical=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
assert sha(canonical)==source_hash
for p in sorted(b.glob('R146*')):
 if p.is_file():shutil.copyfile(p,dest/p.name)
 elif p.name=='R146-views':shutil.copytree(p,dest/p.name)
shutil.copyfile(__file__,dest/'archive_R146.py')
(dest/'boards').mkdir()
summary={'canonical_revision':'R145I','canonical_sha256':source_hash,'adopted':False,'remaining_unconnected_items':28,'connectivity_fraction_remaining':.7,'connectivity_is_not_engineering_progress':True,'manufacturing_release':False,'candidates':[]}
for rev in ['R146A','R146B','R146C','R146D']:
 p=b/rev/'MORI_Interface_C3.kicad_pcb';data=p.read_bytes()
 with (dest/'boards'/(rev+'.kicad_pcb.gz')).open('wb') as f:
  with gzip.GzipFile(filename=rev+'.kicad_pcb',fileobj=f,mode='wb',mtime=0) as z:z.write(data)
 row={'revision':rev,'sha256':sha(p),'archive':'boards/'+rev+'.kicad_pcb.gz','adopted':False}
 commands=json.loads((b/(rev+'-commands.json')).read_text());row['commands']=[{'step':x['step'],'returncode':x['returncode']} for x in commands]
 drc=b/(rev+'-drc.json');audit=b/(rev+'-audit.json')
 if drc.exists():
  d=json.loads(drc.read_text());row.update({k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']})
 else:row['native_drc_status']='NOT_TESTED: build readback rejected the moved via net; saved intermediate board retained only as failed evidence.'
 if audit.exists():
  a=json.loads(audit.read_text());row['audit_status']=a['regression_status'];row['failed_power_widths']=[{'net':x['net'],'width_mm':x['width_mm'],'lost_pairs':len(x['lost_pairs'])} for x in a['power_width'] if x['status']!='PASS'];row['retained_reference_losses']=a['retained_trace_reference_loss']
 summary['candidates'].append(row)
(dest/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
readme='''# R146：栅极与相邻供电联合布局研究

本轮 A/B/C/D 均未采用。当前可信入口仍是 **R145I / 28 项未连接**，相对原 40 项剩余 70%；这不是整项工程完成率。发布版本仍 R108P，制造放行 false。

- A 将 Q1601 右移 0.65 mm，C1602 和 R1601 配套调整，并尝试栅极换层。实际碰到原 MOTION_5V 孔、WHEEL 采样线及 C1003 电源焊盘，In3 路径损失供电连接；拒绝。初步庭院空位不能代替各层铜、孔与本体检查。
- B 为避开这些冲突移动 5 V 孔并绕采样线，原生保存重读发现该孔被错误路径短接到采样网，构建保护正确拒绝。保存的中间板仅作失败证据，没有完成 DRC。
- C 修正这个短接，但新增 In2 MOTION_5V 线不在原 R13 白名单；新增地孔还撞到既有地孔。没有放宽规则。
- D 撤去违规 In2 线和新增地孔，删除已失去换层作用的旧 5 V 孔，修正栅极与 C1602 间距，并留下待恢复的供电支路。其 D301 左移又碰原 GND 孔、R1403 庭院和 CLR 尾段；仍有普通违规、供电损失及一项保留线参考地退化，不能采用。D 的栅极路径没有新增参考缺口，也不代表整板通过。

各板实际计数、哈希与失败供电项见 [summary.json](summary.json)，具体命令、原生 DRC 和完整审计原样保留。四块压缩板可逐字节恢复，完整试验工程仍在本机 `.state/c3-completion/trials/`；这些都不是制造包。诊断图只覆盖局部，不构成全板视觉审查。

## 已确定的下一步约束

1. Q1601 原来的细 UPS_BAT 支路不是冗余连接；删除它会断开原有两组电源。主漏极供电与 U1601/C1601 的供电必须同时恢复。
2. 5 V 下方铜区已有 `(43.55,17.4)` 原生孔，上方孔为 `(44.5,6.4)`。D 的 0.40 mm、37..49 × 4.5..20 mm 局部搜索未找到可通过的 B/In3/F 路径；这是有界搜索失败，不是全板不可布通。不能重复采用 C 的禁用 In2 走线。
3. 同一次搜索给出两个原 UPS_BAT 孔间约 7.24 mm 的 In3 提案，尚未构建和验证，不能视为已经恢复。使用前需精确落在真实孔中心，并检查 CAM、3.3 V 和全部原供电连接。
4. 不继续照 D 左移 D301。D1001 K 尾段邻近 CLR 换层孔的参考缺口需要联合调整；可比较该孔及其 F/B 尾段，但必须先核对所有层的真实铜与参考面，再按源哈希和完整快照试验。没有授权移动地孔或缩小本体禁布区。
5. 目前所有正式规则、源模型、厂家资料、其他活动工作区和 R145I 入口均保持不变；Q1602 栅极及全部其余待办仍继续处理。

栅极布局依据是 [TI LM74502 数据手册](https://www.ti.com/lit/ds/symlink/lm74502.pdf) SNOSDE5A Rev A 第 19 页 11.1：靠近 MOSFET、短栅极连接、合适电源铜和电荷泵电容热位置。此处仅记录设计依据，热、耦合和实物资格仍未完成。
'''
(dest/'README.md').write_text(readme)
manifest={'scope':__doc__,'canonical_sha256':source_hash,'payloads':[{'path':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file()]}
(dest/'archive_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
checks=[{'path':r['path'],'hash_match':sha(dest/r['path'])==r['sha256']} for r in manifest['payloads']]
boards=[{'revision':r['revision'],'hash_match':hashlib.sha256(gzip.decompress((dest/r['archive']).read_bytes())).hexdigest()==r['sha256']} for r in summary['candidates']]
assert all(x['hash_match'] for x in checks+boards) and sha(canonical)==source_hash
(dest/'archive_verification.json').write_text(json.dumps({'status':'PASS','payload_count':len(checks),'payload_checks':checks,'board_checks':boards,'canonical_unchanged':True},indent=2)+'\n')
print(json.dumps({'archive':str(dest),'payloads':len(checks),'candidates':summary['candidates']},ensure_ascii=False))
