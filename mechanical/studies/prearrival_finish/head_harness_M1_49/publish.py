"""Publish bounded route progress separately from the adopted mechanical model."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys,subprocess
HERE=Path(__file__).resolve().parent;S=HERE.parent;M=HERE.parents[2];P=M.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
local=read(HERE/'spaced_entry_screen.json');pack=read(HERE/'spaced_local_packing.json')
body=read(HERE/'body_layered_four_screen.json');motion=read(HERE/'current_source_verification.json');render=read(HERE/'render_manifest.json')
assert all(r['status']=='PASS' for r in [local,pack,body,motion,render])
source=sha(M/'mori_v1_2.blend')
assert source==body['source_blend_sha256']==motion['source_blend_sha256']==render['source_blend_sha256']
assert all(sha(P/p)==h for p,h in motion['sources'].items())
assert all(sha(HERE/p)==h for p,h in motion['inputs'].items())
assert render['source_report_sha256']==sha(HERE/'current_source_verification.json')
profile=local['results'][0]
pair_min=min((r for r in body['whole_local_pair_checks'] if 'point_mm' in r),key=lambda r:r['lower_bound_mm'])
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
summary=f'M1.49当前原件上，11条局部路线已把身体入口抬至Z138mm；130姿态、局部线间下界{pack["minimum"]["gap_lower_bound_mm"]:.3f}mm通过。CAM四根线已从Motion J5接到颈部Z200mm；其中一根上调1.05mm走线层，四根同时排布与七条局部容量样线共存检查通过，最小数值间隙下界{pair_min["lower_bound_mm"]:.3f}mm。所有打印件不变。头部端口、另外七根线的完整两端、FFC、固定与应力释放、带线装配及制作图仍未完成；这是独立候选，未加入主模型。'
table=''.join(f'<tr><td>Motion J5-{r["pin"]}</td><td>{r["slot"]} / {r["body_entry_angle_deg"]}°</td><td>{r["lead_mm"]:g} mm</td><td>{r["plane_z_mm"]:.2f} mm</td><td>{r["length_mm"]+profile["length_mm"]:.2f} mm</td></tr>' for r in body['selected'])
style='''<style>body{background:#f1f5f6;color:#223d46;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;margin:0}main{max-width:1150px;margin:auto;padding:28px 24px 60px}h1{font-size:30px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{width:100%;display:block}figcaption{padding:14px}.notice{background:#fff0d5;padding:17px;border-radius:10px}a{color:#17687b}td,th{text-align:left;padding:10px;border-bottom:1px solid #c3d3d8}table{width:100%;border-collapse:collapse}code{overflow-wrap:anywhere}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:20px 14px}}</style>'''
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.49 · 部分走线候选</title>{style}<main><a href="../neck_adoption/index.html">← 已应用的颈部结构</a><h1>CAM身体段与颈部11线排布</h1><p>{stamp}</p><p class="notice">独立走线候选，未应用主模型；完整线束仍未完成。没有修改打印件、接口或板卡。</p><p>{html.escape(summary)}</p><div class="grid"><figure><img src="body_to_neck.png"><figcaption>当前框架中的零位候选。四种彩色线是CAM的身体至颈部段；橙色为另外七条局部容量样线。</figcaption></figure><figure><img src="paths_exposed.png"><figcaption>隐藏桥座和转动座展示路线；检查仍包含209个原件、29个对插包络和14条已有静态线候选。</figcaption></figure></div><h2>检查范围</h2><table><tr><th>项目</th><th>结果与边界</th></tr><tr><td>11条局部路线与实体</td><td>13偏航 × 10俯仰姿态，分组共{profile['checks']}次检查通过。七条Ø1.4224仅作规划，不是已选SH/GH线材。</td></tr><tr><td>局部弯曲与长度</td><td>13个偏航采样的局部曲线等长{profile['length_mm']:.3f}mm；最小采样曲率半径{profile['minimum_sampled_bend_mm']:.3f}mm。不是实际线材动态寿命验证。</td></tr><tr><td>四根身体段</td><td>两个水平层相差1.05mm；名义最小弯曲半径7mm。身体段与13偏航/130组合姿态的当前原件检查通过。</td></tr><tr><td>所有已规划段共存</td><td>{len(body['whole_local_pair_checks'])}对/姿态线间检查通过。有限采样间距用步长及弦误差保守扣除；四条信号线的远距离自接近检查通过。</td></tr><tr><td>端口与压接数据</td><td>PCB针脚来自原生交接；插头线出口为对插壳包络投影，真实压接位置、剥线、尾部过渡及线材选型待确认。</td></tr></table><h2>路线索引</h2><p>保持Motion J5的针脚身份。这里的槽号只标机械路线；CAM头部端尚未接上，不能把它当作线序视图。下表长度只包含身体到颈部这一段，<b>不是供应商裁线尺寸</b>。</p><table><tr><th>起点</th><th>颈部槽号 / 零位相位</th><th>直线出线预留</th><th>身体段水平层Z</th><th>部分路线中心线长度</th></tr>{table}</table><h2>文件</h2><p><a href="MORI_M1_49_partial_harness_review.blend">独立可编辑预览</a> · <a href="spaced_entry_screen.json">局部实体/姿态</a> · <a href="spaced_local_packing.json">局部线间</a> · <a href="body_layered_four_screen.json">身体段组合与全部线间</a> · <a href="selected_body_motion.json">身体段姿态复核</a></p><h2>继续完成的内容</h2><ul><li>从颈部Z200mm继续连接CAM和其他头部端口，处理俯仰服务环。</li><li>另外七根线的身体段及头部端、LCD FFC和相机软排线。</li><li>固定与应力释放、端子入壳顺序、完整带线装配，以及供应商制作图。</li><li>实际线材/压接、接口和动态弯曲寿命验证。</li></ul><small>当前原件SHA256：<code>{source}</code>。所有结果为数字候选，未采购或制造放行。</small></main></html>'''
page=page.replace('href="spaced_entry_screen.json">局部实体/姿态','href="current_source_verification.json">当前实体/姿态复核').replace('href="selected_body_motion.json">身体段姿态复核','href="current_source_verification.json">身体段姿态复核')
page=page.replace('<h2>文件</h2>','<p>走线检查已修复隐藏代理模型的位置更新问题；在当前装配位置重新执行1716次局部检查和1152次身体段检查，均通过。早期实体报告保留为历史记录，当前实体结论以current_source_verification.json为准；未改变路线的线间距离证明经文件哈希核对后保留。</p><h2>文件</h2>')
(HERE/'index.html').write_text(page)
(HERE/'README.md').write_text('# M1.49 部分走线候选\n\n'+summary+'\n\n当前可用输入：\n\n- spaced_entry_candidates.npz / spaced_entry_screen.json：11条较高入口的等长局部曲线，slot0..10。\n- spaced_local_packing.json：局部线间PASS。\n- body_layered_candidates.npz：身体路线池，选中的id见body_layered_four_screen.json。\n- body_layered_four_candidates.npz：已连接的CAM四根身体至颈部曲线，pin1..4 × 13yaw；头部端尚未连接。\n- selected_body_motion.json：当前主模型的身体段运动检查PASS。\n- render_routes.py生成独立预览，主模型未变。\n\n更早的入口/同平面组合失败记录保留，不作为当前可用路线。未执行任何旧脚本前缀，始终通过harness_context读取当前原件。\n')
with (HERE/'README.md').open('a') as f:
    f.write('\n当前实体检查以current_source_verification.json为准：隐藏代理变换更新问题修复后，1716次局部/1152次身体段检查重跑PASS，所有集合显示状态切换后实体指纹一致。早期报告保留为历史，曲线本身和线间计算未变。\n')
work=read(S/'work_status.json');row=next(r for r in work['remaining'] if r['id']=='harness')
row['latest_M1_49_route_detail']=summary;row['latest_M1_49_route_evidence']='head_harness_M1_49/index.html'
row['detail']=summary;row['evidence']='head_harness_M1_49/index.html'
work['updated_utc']=stamp
work['completed']=[r for r in work['completed'] if r['id']!='M1_49_partial_harness']+[dict(id='M1_49_partial_harness',status='PASS',detail='当前原件上的11线局部排布与CAM四线身体至颈部段通过有限几何检查；完整线束仍BLOCKED。',evidence='head_harness_M1_49/index.html')]
write(S/'work_status.json',work)
status=read(M/'reports/interface_completion_status.json');status['pending']=[r for r in status['pending'] if r.get('id')!='harness']+[row];write(M/'reports/interface_completion_status.json',status)
index=M/'index.html';t=index.read_text()
needle='<section id="remaining"><h2>当前剩余项目</h2><table>'
rows=''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{html.escape(r["detail"])}'+(f' <a href="studies/prearrival_finish/{r["evidence"]}">检查记录</a>' if r.get('evidence') else '')+'</td></tr>' for r in work['remaining'])
t,n=re.subn(r'<section id="remaining">.*?</section>',needle+rows+'</table><p><a href="studies/prearrival_finish/work_status.json">完整状态记录</a></p></section>',t,flags=re.S);assert n==1
banner='<p id="M1-49-route-progress">CAM身体至颈部段的四线组合已通过检查，完整线束仍在设计。<a href="studies/prearrival_finish/head_harness_M1_49/index.html">查看部分走线候选</a>。</p>'
t=re.sub(r'<p id="M1-49-route-progress">.*?</p>','',t,flags=re.S).replace('<section id="neck-capacity">','<section id="neck-capacity">'+banner,1)
index.write_text(t)
# Main-page changes require refreshing its animation-delivery file hash, while
# the already-verified video and animation geometry remain unchanged.
subprocess.run([sys.executable,str(M/'scripts/publish_animation_update.py')],cwd=P,check=True)
files=[HERE/f for f in ['index.html','README.md','spaced_entry_screen.json','spaced_local_packing.json','body_layered_four_screen.json','current_source_verification.json','render_manifest.json','body_to_neck.png','paths_exposed.png','MORI_M1_49_partial_harness_review.blend']]
write(HERE/'publication.json',dict(status='PASS',utc=stamp,source_blend_sha256=source,main_changed=False,full_harness='BLOCKED',manufacturing_release=False,files={p.name:sha(p) for p in files}))
print('PARTIAL_ROUTE_PUBLISHED',len(body['selected']),len(body['whole_local_pair_checks']))
