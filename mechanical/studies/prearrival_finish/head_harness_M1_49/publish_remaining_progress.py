"""Publish the latest joint-wire study with explicit partial scope."""
from pathlib import Path
import datetime, hashlib, html, json, re, subprocess, sys
HERE = Path(__file__).resolve().parent
OUT = HERE/'remaining_routes'
STUDIES = HERE.parent
MECH = HERE.parents[2]
PROJECT = MECH.parent
variant = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('--route-set=')), 'nine_higher')
assert variant in ['nine_higher', 'nine_higher_directed', 'nine_higher_stagger', 'nine_higher_lift']
BASE = OUT/variant/'combined'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

pool = read(OUT/'nine_higher/body_prefix_screen.json')
proof = read(BASE/'lower_nine_screen.json')
high = read(OUT/'higher_entry/neck_screen.json')
five = read(OUT/'five_before_cam_reroute/lower_five_screen.json')
old_conflicts = read(OUT/'cam_body_conflicts.json')
assert pool['status'] == high['status'] == five['status'] == 'PASS'
assert old_conflicts['status'] == 'BLOCKED'
for report in [pool, proof, high, five]:
    for name, digest in {**report['sources'], **report['inputs']}.items():
        assert sha(PROJECT/name) == digest, name
source = sha(MECH/'mori_v1_2.blend')
assert source == proof['sources']['mechanical/mori_v1_2.blend']
lower_pass = proof['status'] == 'PASS'
cam_file = BASE/'cam_rejoined/cam_joined_screen.json'
cam = read(cam_file) if cam_file.exists() else None
cam_pass = lower_pass and cam is not None and cam['status'] == 'PASS'
if cam:
    for name, digest in {**cam['sources'], **cam['inputs']}.items():
        assert sha(PROJECT/name) == digest, name

render_base = BASE if lower_pass else OUT
render = read(render_base/'render_manifest.json')
assert render['status'] == 'PASS' and render['source_blend_sha256'] == source
for row in render['images']:
    assert sha(render_base/row['file']) == row['sha256']
if lower_pass:
    assert render['inputs'][str((BASE/'lower_nine_screen.json').relative_to(PROJECT))] == sha(BASE/'lower_nine_screen.json')
    assert render['continuous_CAM_included'] == cam_pass
    blend = render_base/'MORI_M1_49_nine_wire_candidate.blend'
else:
    blend = render_base/'MORI_M1_49_wire_joint_study.blend'
    assert render['source_report_sha256'] == sha(OUT/'five_before_cam_reroute/lower_five_screen.json')
assert sha(blend) == render['blend_sha256']

if cam_pass:
    summary = '九根导线的身体至颈部组合已通过有限实体和线间检查，四根CAM线已接回原头部线环并完成组合复核。入颈位置在既有开口内上移4mm，没有更改打印件、板位或针序。三根舵机线和两根CAM供电线仍只接至头部预留点；两根喇叭线仍是局部占位。线材未选定，端部、固定、FFC/FPC和带线装配仍待完成，完整线束保持BLOCKED。'
elif lower_pass:
    summary = '九根导线的身体至颈部组合已通过有限实体和线间检查，入颈位置在既有开口内上移4mm，打印件和板位保持。与原CAM头部线环的组合尚未通过或尚未完成，不能把两个独立结果直接拼成整束。上部端点、两根喇叭线、固定、FFC/FPC和带线装配仍待完成，完整线束保持BLOCKED。'
else:
    summary = '五根供电/舵机线的下部候选单独通过，但与旧CAM身体路线冲突。现有开口内上移4mm的十一线局部排布通过；加入方向细化和局部错层路线后，九根身体导线仍未找到通过组合，当前剩余冲突位于两根CAM线的出线转弯区域。有限候选失败不证明所有路线都不可行。打印件、板位及针序保持，完整线束仍BLOCKED。'
stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
style = '''<style>body{margin:0;background:#f1f5f6;color:#203a44;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:28px 24px 64px}h1{font-size:30px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:14px}.notice{background:#fff0d5;padding:18px;border-radius:10px}a{color:#17687b}td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #c3d3d8}table{width:100%;border-collapse:collapse}code{overflow-wrap:anywhere}@media(max-width:760px){main{padding:18px 12px}.grid{grid-template-columns:1fr}}</style>'''
def link(path, label):
    return f'<a href="{html.escape(str(path.relative_to(OUT)))}">{html.escape(label)}</a>'
if lower_pass:
    names = ['nine_overview','nine_exposed','body_routes']
    captions = ['九条下部路径的同一组合；三条蓝绿色为舵机、两条紫色为CAM供电、四条暖色为CAM信号。颜色只区分机械路径。',
                '隐藏部分框架观察路线，检查时仍保留实体。两条黄色短线只预留喇叭经过颈部的空间。',
                '身体内的出线段。数学曲线尚无实际固定，不能认为实物线束可以自行保持这些形状。']
    gallery = ''.join(f'<figure><img src="{variant}/combined/{n}.png"><figcaption>{c}</figcaption></figure>' for n,c in zip(names,captions))
else:
    gallery = '<figure><img src="five_lower_exposed.png"><figcaption>五线单独候选；未接入旧CAM四线。</figcaption></figure><figure><img src="old_CAM_conflict_overlay.png"><figcaption>故意叠加旧CAM路线显示冲突，此图不是通过的整束方案。</figcaption></figure>'
lane = next(r for r in high['results'] if r['z0_mm'] == 142.)
counts = proof['candidate_counts']
check_rows = [
    ('十一线局部入口', f'PASS。入口Z142mm；{len(lane["pairs"])}组线间记录。只代表该局部段。' if 'pairs' in lane else 'PASS。入口Z142mm，在既有开口内上移4mm；仅此局部段。'),
    ('九根身体线的独立选项', f'{sum(counts.values())}条选项；单线筛查不代表能同时安装。'),
    ('九根下部路径同时存在', 'PASS；715组全路径线间检查、所选路径的实体和自身接近检查通过。' if lower_pass else 'BLOCKED；当前有限选项的组合尚未通过。'),
    ('四根CAM接回头部线环', 'PASS；新增5200组上下段互检和520条完整CAM自身接近检查；13个偏航×10个俯仰姿态。' if cam_pass else 'BLOCKED / 尚未通过组合；原CAM独立结果保留，不能直接合并。'),
    ('主模型、打印件及硬件文件', '本研究未更改；正式结构保持已批准的M1.49。'),
    ('完整线束与制造', 'BLOCKED。其余端部、固定、FFC/FPC、带线装配及供货图未完成；实物动态行为NOT_TESTED。')]
checks = ''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a,b in check_rows)
length_rows = ''
if lower_pass:
    length_rows = '<h2>下部中心线长度，仅供布局</h2><p>下表只列进入颈部之前的身体段；不是成品长度，端子、剥线、固定和装配余量未冻结。</p><table><tr><th>导线</th><th>身体段长度</th><th>范围</th></tr>'
    for row in sorted(proof['selected'],key=lambda r:r['endpoint']):
        value = f'{row["analytic_length_mm"]:.1f} mm' if 'analytic_length_mm' in row else f'{row["length_lower_bound_mm"]:.2f}–{row["length_upper_bound_mm"]:.2f} mm（数学界限）'
        length_rows += f'<tr><td>{row["endpoint"]}</td><td>{value}</td><td>不含颈部及头部，不可下单</td></tr>'
    length_rows += '</table>'
evidence = [link(BASE/'lower_nine_screen.json','九线组合记录'),
            link(OUT/'higher_entry/neck_screen.json','局部入口复核'),
            link(OUT/'nine_higher/body_prefix_screen.json','独立选项筛查'),
            link(blend,'独立Blender候选'),
            link(OUT/'ENDPOINT_REQUIREMENTS.md','端部输入与剩余工作'),
            link(OUT/'INTERFACE_NOTES.md','功能及线材证据'),
            link(OUT/'commands.json','实际命令')]
if cam is not None: evidence.append(link(cam_file,'CAM重新组合检查'))
if (OUT/'CAM_pair_diagnosis.json').exists(): evidence.append(link(OUT/'CAM_pair_diagnosis.json','两条CAM路径的全局距离诊断'))
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.49 · 头部线束组合复核</title>{style}<main><a href="../../neck_adoption/index.html">← 已应用的颈部结构</a><h1>头部线束的组合复核</h1><p>{stamp}</p><p class="notice">完整线束仍未完成。这里是独立研究，主模型、STL和M1.49-A1装配视频没有加入这些候选线。没有采购或制造放行。</p><p>{html.escape(summary)}</p><div class="grid">{gallery}</div><h2>检查范围</h2><table><tr><th>项目</th><th>实际结论</th></tr>{checks}</table><p>实体检查使用当前209个原件、29个对插包络及14条已有静态导线候选。导线间要求的0.3mm是当前几何规划值，不是已确认的生产公差。有限姿态通过不代表连续运动、回弹、疲劳和装配已验证。</p><h2>线材仍为候选</h2><p>本轮用最大外径1.1684mm的Alpha 2622目录参考筛查五条供电/舵机路径；CAM信号线继续使用0.6604mm参考。未替换正式BOM，压接兼容、并发供电、动态寿命、库存与成本尚未核定。不能通过缩小真实硬件来宣称通过。</p>{length_rows}<h2>下一步的具体缺项</h2><ol><li>舵机尾线/分线接口及CAM供电插头的完整端部，补齐上部路线。</li><li>CAM至SP3040的两根完整喇叭线，以及屏幕FFC和相机FPC。</li><li>固定和应力释放、端子穿入与带线装配，随后才能形成供应商制作图。</li></ol><p>厂家能够提供的端部图可在实物到货前继续取得；缺失字段保持未知。需要结构调整时先展示具体候选确认。</p><p>{' · '.join(evidence)}</p><details><summary>保留的早期失败证据</summary><p>旧CAM下部路线与五根新供电/舵机线存在冲突，因此本轮重排全部九条身体路径；没有把单独通过的方案直接拼接。</p><p>{link(OUT/'cam_body_conflicts.json','旧路线冲突定位')} · {link(OUT/'five_before_cam_reroute/lower_five_screen.json','此前五线独立结果')}</p></details><small>当前主模型SHA256：<code>{source}</code>。PROTOTYPE / UNVALIDATED。</small></main></html>'''
(OUT/'index.html').write_text(page)
(OUT/'README.md').write_text('# M1.49 头部线束组合复核\n\n'+summary+'\n\n入口为 index.html；来源与实际命令见各 JSON。当前曲线均不是供应商裁线尺寸。\n')

work = read(STUDIES/'work_status.json')
row = next(r for r in work['remaining'] if r['id']=='harness')
relative = 'head_harness_M1_49/remaining_routes/index.html'
row.update(detail=summary, evidence=relative, latest_M1_49_joint_route_detail=summary,
           latest_M1_49_joint_route_evidence=relative)
work['updated_utc'] = stamp
work['completed'] = [r for r in work['completed'] if r['id'] not in ['M1_49_lower_nine','M1_49_CAM_nine_coexistence']]
if lower_pass:
    work['completed'].append(dict(id='M1_49_lower_nine',status='PASS',
        detail='九根身体至颈部导线组合通过有限名义检查；两根喇叭线仍仅局部预留，上部端部与固定未完成。',evidence=relative))
if cam_pass:
    work['completed'].append(dict(id='M1_49_CAM_nine_coexistence',status='PASS',
        detail='四条完整CAM曲线与五条下部供电/舵机曲线及两条喇叭局部预留完成组合复核；完整线束仍BLOCKED。',evidence=relative))
write(STUDIES/'work_status.json',work)
status = read(MECH/'reports/interface_completion_status.json')
status['pending'] = [r for r in status['pending'] if r.get('id')!='harness']+[row]
write(MECH/'reports/interface_completion_status.json',status)
index = MECH/'index.html'; text = index.read_text()
rows = ''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}'+(f' <a href="studies/prearrival_finish/{r["evidence"]}">检查记录</a>' if r.get('evidence') else '')+'</td></tr>' for r in work['remaining'])
block = '<section id="remaining"><h2>当前剩余项目</h2><table>'+rows+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>'
text,count = re.subn(r'<section id="remaining">.*?</section>',lambda _:block,text,flags=re.S)
assert count==1
banner = '<p id="M1-49-route-progress">'+('九条下部路径已通过组合复核；完整线束仍未完成。' if lower_pass else '九线组合继续复核；独立路径通过不代表整束完成。')+f'<a href="studies/prearrival_finish/{relative}">查看当前候选与剩余项</a>。</p>'
text,count = re.subn(r'<p id="M1-49-route-progress">.*?</p>',lambda _:banner,text,flags=re.S)
assert count==1; index.write_text(text)
subprocess.run([sys.executable,str(MECH/'scripts/publish_animation_update.py')],cwd=PROJECT,check=True)
files = [OUT/'index.html',OUT/'README.md',OUT/'ENDPOINT_REQUIREMENTS.md',
         OUT/'INTERFACE_NOTES.md',OUT/'commands.json',BASE/'lower_nine_screen.json',
         render_base/'render_manifest.json',blend,*[render_base/r['file'] for r in render['images']]]
if cam: files.append(cam_file)
write(OUT/'publication.json',dict(status='PASS',utc=stamp,source_blend_sha256=source,
      files={str(p.relative_to(PROJECT)):sha(p) for p in files},lower_nine=proof['status'],
      CAM_rejoined=cam['status'] if cam else 'NOT_TESTED',main_geometry_changed=False,
      full_harness='BLOCKED',manufacturing_release=False,script_sha256=sha(Path(__file__))))
print('REMAINING_PUBLISHED',proof['status'],'CAM',cam['status'] if cam else 'NOT_TESTED')
