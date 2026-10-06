"""Publish the current four-CAM-wire candidate with explicit remaining scope."""
from pathlib import Path
import datetime,hashlib,html,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;S=HERE.parent;M=HERE.parents[2];P=M.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
proof=read(HERE/'cam_joined_verification.json');render=read(HERE/'cam_render_manifest.json')
lower=read(HERE/'front_lower_verification.json');cross=read(HERE/'upper_lower_pairs.json')
assert all(r['status']=='PASS' for r in [proof,render,lower,cross])
source=sha(M/'mori_v1_2.blend')
assert source==proof['source_blend_sha256']==render['source_blend_sha256']
assert render['source_report_sha256']==sha(HERE/'cam_joined_verification.json')
assert sha(HERE/'MORI_M1_49_CAM_route_candidate.blend')==render['blend_sha256']
for p,h in proof['sources'].items():assert sha(P/p)==h,p
for p,h in proof['inputs'].items():assert sha(HERE/p)==h,p
for row in render['images']:assert sha(HERE/row['file'])==row['sha256']
assert len(proof['selected'])==4 and len(proof['joins'])==520
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
summary='M1.49当前原件上，CAM四根线已从Motion J5贯通到CAM J11的估计出线点，保持逻辑1→1至4→4；130个组合姿态的实体、线间及自身接近检查通过。为避开俯仰舵机，调整了三条局部路线的相位和一根身体段，并错开头部最后转弯的位置。所有打印件及硬件位置保持。该线束仍是独立候选，未加入主模型。固定与应力释放、另外七根导线的完整两端、FFC/FPC、带线装配和供应商制作图尚未完成。'
table=''.join(f'<tr><td>J5-{r["pin"]} → J11-{r["pin"]}</td><td>约 {r["maximum_polygon_length_mm"]:.1f} mm</td><td>不是裁线尺寸</td></tr>' for r in proof['lengths'])
style='''<style>body{margin:0;background:#f1f5f6;color:#233d47;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:28px 24px 64px}h1{font-size:30px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:14px}.notice{background:#fff0d5;padding:18px;border-radius:10px}a{color:#17687b}td,th{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #c3d3d8}table{width:100%;border-collapse:collapse}code{overflow-wrap:anywhere}@media(max-width:760px){main{padding:18px 12px}.grid{grid-template-columns:1fr}}</style>'''
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.49 · CAM四线贯通候选</title>{style}<main><a href="../neck_adoption/index.html">← 已应用的颈部结构</a><h1>CAM四根线的连续走线候选</h1><p>{stamp}</p><p class="notice">有限姿态的数字检查通过，完整线束仍未完成。这里是独立候选预览；正式主模型、STL及装配视频保持已批准的M1.49结构。线束尚未采购或制造放行。</p><p>{html.escape(summary)}</p><div class="grid"><figure><img src="cam_route_overview.png"><figcaption>当前框架内的零位候选。四种颜色用于区分机械路径，不代表真实电气线色。橙色七根仍是颈部局部容量样线。</figcaption></figure><figure><img src="cam_route_exposed.png"><figcaption>隐藏部分框架、外壳与光学件展示路线；数字检查仍包含这些零件。CAM端的实际胶壳、压接位置及公差尚未确认。</figcaption></figure></div><h2>头部俯仰余线</h2><figure><img src="cam_upper_close.png"><figcaption>四根线连续绕过舵机，进入CAM板估计出线点。图中空中的余线是待固定的曲线候选；不表示实物导线能自行保持形状，也不表示固定座已完成。</figcaption></figure><h2>已完成的数字检查</h2><table><tr><th>范围</th><th>结果</th></tr><tr><td>当前实体与接口基准</td><td>按当前209个原件、29个对插包络及14条已有静态线候选检查；未替换打印实体。隐藏检查模型的变换已在读取前更新。</td></tr><tr><td>身体段与颈部</td><td>已更新的11条路线通过当前实体与姿态复核、715组线间检查；四根CAM线下段连续。</td></tr><tr><td>俯仰段与下段</td><td>5720组上下段线间检查、60组上段互检通过，40组上段自身接近检查通过。</td></tr><tr><td>四根新连接段组合</td><td>选中的每段通过实体、自身接近、其他上下段及连接段之间的检查；13个偏航×10个俯仰姿态共520条连续CAM曲线，接缝误差小于0.00001mm。该数值是计算误差，不是制造公差。</td></tr><tr><td>弯曲与运动</td><td>新增身体/头部圆弧名义半径不小于7mm；颈部沿已检查的等长曲线族。实体检查为有限姿态采样，未验证实际动态弯折、回弹、摩擦或寿命。</td></tr><tr><td>线材与端口证据</td><td>CAM路线使用Ø0.6604mm候选；另外七根Ø1.4224mm仅作容量规划。身体针位来自原生PCB，CAM出线点含照片估计，端子和成品线仍需确认。</td></tr></table><h2>中心线路径长度</h2><p>只记录当前数学路径。端子、压接、剥线、应力释放及装配余量尚未冻结，<b>不能用下表向供应商下单</b>。</p><table><tr><th>逻辑连接</th><th>当前中心线</th><th>用途限制</th></tr>{table}</table><h2>仍需完成</h2><ul><li>身体、偏航及俯仰两侧的线束固定和应力释放；任何结构变化先提供候选确认。</li><li>其他七根线的两端连接，以及屏幕FFC、相机FPC。</li><li>端子穿入、插接和整机带线装配顺序。</li><li>实际线材、胶壳/压接尺寸及供货图纸，随后再做实物装配和运动验证。</li></ul><p><a href="MORI_M1_49_CAM_route_candidate.blend">独立Blender候选</a> · <a href="cam_joined_verification.json">完整CAM组合检查</a> · <a href="front_lower_verification.json">新的身体/颈部排布</a> · <a href="upper_lower_pairs.json">上下段线间检查</a> · <a href="commands.json">运行记录</a> · <a href="index.html">此前身体至颈部阶段</a></p><small>主模型SHA256：<code>{source}</code>。CAD / PROTOTYPE / UNVALIDATED。</small></main></html>'''
(HERE/'cam_index.html').write_text(page)
(HERE/'CAM_README.md').write_text('# M1.49 CAM四线贯通候选\n\n'+summary+'\n\n- 主入口：cam_index.html。\n- 当前520条曲线：cam_joined_candidates.npz，key为pinN_yY_pP。\n- cam_joined_verification.json记录组合证明、全部依赖哈希与早期失败诊断的有限复用。\n- 当前下段：front_lower_curves.npz；七根局部样线：front_neck_candidates.npz。\n- 固定、另外七根完整导线、FFC/FPC、带线装配和供应商下料图未完成。\n- 本目录index.html保留此前局部阶段，不能替代cam_index.html的更新状态。\n- head_harness_M1_49的独立Blender含未应用的候选线；主模型与动画没有新增线束。\n')
work=read(S/'work_status.json');row=next(r for r in work['remaining'] if r['id']=='harness')
row.update(detail=summary,evidence='head_harness_M1_49/cam_index.html',latest_M1_49_route_detail=summary,latest_M1_49_route_evidence='head_harness_M1_49/cam_index.html')
work['updated_utc']=stamp
work['completed']=[r for r in work['completed'] if r['id']!='M1_49_CAM_four_route']+[dict(id='M1_49_CAM_four_route',status='PASS',detail='CAM四根从身体到头部估计出线点的贯通候选通过有限实体/线间/自身接近检查；固定、完整线束及带线装配仍未完成。',evidence='head_harness_M1_49/cam_index.html')]
write(S/'work_status.json',work)
status=read(M/'reports/interface_completion_status.json');status['pending']=[r for r in status['pending'] if r.get('id')!='harness']+[row];write(M/'reports/interface_completion_status.json',status)
index=M/'index.html';t=index.read_text()
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}'+(f' <a href="studies/prearrival_finish/{r["evidence"]}">检查记录</a>' if r.get('evidence') else '')+'</td></tr>' for r in work['remaining'])
block='<section id="remaining"><h2>当前剩余项目</h2><table>'+rows+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>'
t,n=re.subn(r'<section id="remaining">.*?</section>',block,t,flags=re.S);assert n==1
banner='<p id="M1-49-route-progress">CAM四线贯通候选通过有限几何组合检查，固定与完整线束仍未完成。<a href="studies/prearrival_finish/head_harness_M1_49/cam_index.html">查看最新走线候选</a>。</p>'
t=re.sub(r'<p id="M1-49-route-progress">.*?</p>',banner,t,flags=re.S);index.write_text(t)
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=P,check=True)
files=[HERE/n for n in ['cam_index.html','CAM_README.md','cam_joined_verification.json','front_lower_verification.json','upper_lower_pairs.json','cam_render_manifest.json','cam_route_overview.png','cam_route_exposed.png','cam_upper_close.png','MORI_M1_49_CAM_route_candidate.blend','commands.json']]
write(HERE/'cam_publication.json',dict(status='PASS',utc=stamp,source_blend_sha256=source,files={p.name:sha(p) for p in files},main_changed=False,full_harness='BLOCKED',manufacturing_release=False))
print('CAM_CANDIDATE_PUBLISHED',len(proof['joins']))
