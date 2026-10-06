"""Publish native-bridge assembly-order failures without changing production CAD."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,os,platform
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Rectangle

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'bridge_tail_order_review';OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={}
specs=[('original','bridge_then_shell_over_wires/screen.json','screen_bridge_then_shell_over_wires.py','bridge_then_shell_over_wires.log'),
       ('left','bridge_left_tail_staging/screen.json','screen_bridge_left_tail_staging.py','bridge_left_tail_staging.log'),
       ('bare','bridge_before_bearing/screen.json','screen_bridge_before_bearing.py','bridge_before_bearing.log'),
       ('diagnosis','bridge_then_shell_over_wires/diagnosis.json','diagnose_bridge_shell_tail_clearance.py','bridge_shell_tail_diagnosis.log')]
records={};commands=[]
for key,relative,script,log in specs:
    p=STOCK/relative;d=read(p);records[key]=d
    assert d['script_sha256']==sha(A8/script),script
    assert not d['main_applied']
    for q in [p,A8/script,A8.parent/'verification_logs'/log]:inputs[str(q.relative_to(ROOT))]=sha(q)
    logtext=(A8.parent/'verification_logs'/log).read_text()
    assert 'Traceback (most recent call last)' not in logtext and 'Blender quit' in logtext
    for name,h in d.get('source_files',{}).items():assert sha(ROOT/name)==h,name;inputs[name]=h
    for name,h in d.get('protected_sources',{}).items():assert sha(ROOT/name)==h,name
    commands.append(dict(command='/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 2 --python mechanical/studies/prearrival_finish/harness_A8/'+script,
        log=str((A8.parent/'verification_logs'/log).relative_to(ROOT)),exit_code=0))
original,left,bare,diag=[records[k] for k in ['original','left','bare','diagnosis']]
assert all(d['status']=='BLOCKED' for d in [original,left,bare])
assert original['baseline_wire_status']=='PASS'
assert original['original_M1_47_source_solids_used'] and original['substituted_prints']==[]
assert diag['source_screen_sha256']==sha(STOCK/'bridge_then_shell_over_wires/screen.json')
assert diag['terminal_hits'][0]['pin']==4
assert diag['bare_bridge_candidate_centre_probe']['centre_inside']
assert original['fourteen_core_wires_present']
for folder,name in [('bridge_then_shell_over_wires','temporary_wires.npz'),('bridge_left_tail_staging','curves.npz'),('bridge_before_bearing','curves.npz')]:
    p=STOCK/folder/name;inputs[str(p.relative_to(ROOT))]=sha(p)
    source=original if folder=='bridge_then_shell_over_wires' else left if 'left' in folder else bare
    assert source['wire_sha256']==sha(p)


def draw_section(axis,name,angle,face,edge,alpha=1.):
    paths=[]
    for contour in diag['radial_sections'][str(angle)][name]:
        p=np.array(contour);vertices=np.vstack([p,p[0]])
        codes=[MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY]
        paths.append(MPath(vertices,codes))
    if paths:axis.add_patch(PathPatch(MPath.make_compound_path(*paths),facecolor=face,edgecolor=edge,lw=1.,alpha=alpha))


plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,axes=plt.subplots(1,2,figsize=(12,7))
for ax,angle in zip(axes,[45,225]):
    draw_section(ax,'Yaw_Base',angle,'#d6e3e7','#456772')
    ax.set_xlim(-1,26);ax.set_ylim(132,160);ax.set_aspect('equal');ax.grid(alpha=.18)
    ax.set_xlabel('Radial coordinate (mm)');ax.set_ylabel('Ground height in bridge frame (mm)')
draw_section(axes[0],'Yaw_Bearing',45,'#e2b86d','#997531')
hit=diag['terminal_hits'][0];endpoint_z=original['lengths'][3]['terminal_mm'][2]-diag['bridge_first_failure_lift_mm']
axes[0].plot([6.8,6.8],[132,endpoint_z],color='#b04434',lw=2.2)
axes[0].add_patch(Rectangle((6.8-.81,endpoint_z-.31),1.62,4.72,facecolor='#df7063',edgecolor='#aa342b',alpha=.8))
axes[0].annotate('Terminal space meets\nreaction socket floor',xy=(6.8,138.8),xytext=(11,134),
    arrowprops={'arrowstyle':'->','color':'#aa342b'},color='#923124')
axes[0].set_title('A. Bearing and bridge fitted together\nStraight tails at radius 6.8 mm',loc='left',pad=15)
t=np.linspace(0,math.pi/2,253);r=19.5-8*np.sin(t);z=139+8*(1-np.cos(t))
axes[1].plot(np.r_[r,11.5],np.r_[z,160],color='#b04434',lw=2.2)
q=np.array(diag['bare_bridge_candidate_centre_probe']['point_mm']);qr=np.linalg.norm(q[:2])
axes[1].scatter([qr],[q[2]],s=38,color='#9d2922',zorder=5)
axes[1].annotate('Wire centre inside bridge\nR11.5 staging candidate',xy=(qr,q[2]),xytext=(12.8,153),
    arrowprops={'arrowstyle':'->','color':'#aa342b'},color='#923124')
axes[1].set_title('B. Bearing deferred\nR8 bend to a straight tail at radius 11.5 mm',loc='left',pad=15)
fig.suptitle('Original M1.47 neck: the tested straight-tail positions are obstructed',fontsize=14,y=.98)
fig.subplots_adjust(left=.07,right=.98,top=.87,bottom=.24,wspace=.23)
fig.text(.07,.065,'Sections use the original source solids. Red terminal size is an ASSUMED requested space.\nThese two tested paths fail; this does not prove every possible assembly route is impossible.\nNo hole, printed part, board, connector or wire diameter was changed.',fontsize=10,color='#415760')
fig.savefig(OUT/'sections.png',dpi=160)
plt.close(fig)

links={k:os.path.relpath(STOCK/v,OUT) for k,v in [('original','bridge_then_shell_over_wires/screen.json'),
    ('left','bridge_left_tail_staging/screen.json'),('bare','bridge_before_bearing/screen.json'),
    ('diagnosis','bridge_then_shell_over_wires/diagnosis.json'),('guided','PH_guided_wire_entry/index.html')]}
overview=os.path.relpath(A8/'supplier_source_update/index.html',OUT)
now=datetime.now(timezone.utc).isoformat()
md=f'''# 原桥座的带线装配顺序检查

更新时间：{now}。M1.47 主模型、参数和两份合同保持原哈希。全部使用原桥座及轴承实体，没有套用未批准的通道候选。

![原桥座剖面与两条失败路线](sections.png)

## 结论

**不能把“先接好身体导线，再把桥座和上壳直接套下去”写成已通过的装配工序。**

1. 4根CAM线保持名义全长，14根身体导线保留，原29个插头空间按身体/上壳所属保留。R6.8临时直立线尾的最终静态排布通过；带轴承桥座下套时，第4根线端的请求空间与反力座底面相交约{hit['volume_mm3']:.3f}mm³。
2. 已检查4组左侧线尾位置，未找到满足间隙的排布。这些是具体失败范围，不能据此认定左侧不存在任何装法。
3. 将轴承延后安装后，R11、11.5、12、13mm的四组直立线尾仍未通过。R11.5候选的一处解析线中心（Z146mm）确在桥座材料内；不是仅因检查余量偏保守。其他候选的记录仍按原来的间隙失败解释。
4. 上壳的5条所试路径未通过：原方向下落时，后接口J3插头空间与一根IMU线重叠约0.300mm³；另外4条后移路径先遇到线端与上壳问题。这里保留了已建的插头空间，但后板和喇叭完整导线尚未建齐。

中心的小孔仍然存在；上下可通过范围在所试的四根线尾位置错开，不能把桥座描述成完全封闭或所有穿线方法都不可行。

## 已通过与未完成的边界

此前[PH插头带4根完整导线的插接阶段]({links['guided']})已有连续检查通过；它使用独立通道候选并把自由线尾暂留颈外，不能直接接成主模型的完整装配。
后续穿颈、头部装入、H01/H04、其他跨关节线/FFC、扎带和手部工具仍需处理。新的失败研究没有推翻此前局部通过，也没有关闭这些缺口。

端子1×1.8×4.1mm及0.31mm扩展仍是明确标注的请求空间；0.6604mm线外径与0.3mm间隙保持。名义长度保持，不是最终供应商裁线长度。没有新增孔、零件、改小端子/线径或移动PCB。

[桥和上壳]({links['original']}) · [左侧临时排布]({links['left']}) · [轴承延后]({links['bare']}) · [原实体剖面及点内诊断]({links['diagnosis']}) · [来源与实际命令](publication.json)
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MORI 原桥座带线装配检查</title>
<style>body{{max-width:1120px;margin:28px auto;padding:0 24px 40px;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#294851;background:#f1f5f5}}section{{background:white;padding:24px;border-radius:10px;margin:18px 0}}img{{width:100%;height:auto}}a{{color:#09687c}}.pending{{background:#fff0dc}}li{{margin:10px 0}}</style>
<p><a href="{overview}">← 资料与设计进度</a></p><h1>原桥座不能直接套过这组直立线尾</h1>
<section><p>这是装配顺序检查的失败结果，主模型没有修改。当前四线排布遇到上下错开的可通过范围；延后安装轴承也没有使本次测试的路线通过。中心小孔仍存在，并非桥座完全封闭。</p><a href="sections.png"><img src="sections.png" alt="M1.47原桥座实体径向剖面：已装轴承时线端碰反力座底面；轴承后装候选的一处导线中心位于桥座材料内"></a></section>
<section><h2>检查结果</h2><ul><li>带轴承桥座下套：第4根线端请求空间与反力座底面相交{hit['volume_mm3']:.3f}mm³。</li><li>4组左侧排布未找到满足间隙的候选。</li><li>轴承后装的4组直立排布未通过；R11.5候选已用原实体确认一处线中心落在材料内。</li><li>上壳5条路径未通过；原方向下落时后板J3插头空间会碰IMU线，后移路线先遇到线端与上壳问题。</li></ul><p>这些结果只排除所试路径，不证明其他装法不可能。实际端子仍有尺寸未知项。</p></section>
<section class="pending"><h2>完整装配尚未完成</h2><p><a href="{links['guided']}">此前PH带线插接阶段</a>的连续检查结果保留；它使用独立通道候选，后续穿颈和头部装入还未衔接。H01/H04后装、其余跨关节线/FFC、固定、手部工具及制作图继续待处理。</p><p>4根CAM名义全长、14根身体导线、29个插头空间与原尺寸保持；没有因失败而增加开孔或改小配件。没有发布制造图。</p></section>
<p><a href="README.md">详细说明</a> · <a href="{links['diagnosis']}">实体剖面诊断</a> · <a href="{links['original']}">桥/上壳检查</a> · <a href="{links['bare']}">轴承后装检查</a> · <a href="publication.json">来源与命令</a></p></html>'''
(OUT/'index.html').write_text(html)
report=dict(status='PASS',scope='Publication of failed finite installation candidates, not an assembly PASS',
    generated_utc=now,script_sha256=sha(SCRIPT),protected_sources=original['protected_sources'],source_files=inputs,
    outputs={n:sha(OUT/n) for n in ['README.md','index.html','sections.png']},commands=commands,
    original_bridge_order='BLOCKED',bearing_deferred_order='BLOCKED',
    whole_harness='BLOCKED',substituted_prints=[],main_applied=False,manufacturing_release=False,
    versions=dict(blender='5.2.2 LTS d13f752e3b9c',python=platform.python_version()))
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
state_path=A8.parent/'work_status.json';state=read(state_path)
state['native_bridge_tail_order']=dict(publication=str((OUT/'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT/'publication.json'),status='BLOCKED',native_prints_unchanged=True,
    alternatives_tested=['assembled_bridge','left_tail_positions','bearing_deferred'],whole_harness='BLOCKED')
item=next(i for i in state['remaining'] if i['id']=='harness')
item['latest_native_bridge_order_evidence']=str((OUT/'index.html').relative_to(A8.parent))
item['latest_native_bridge_order_detail']='原M1.47桥座带轴承直接套线、4组左侧排布及轴承后装4组排布均未通过；上壳5条路线亦未通过。已定位底面/桥座材料和后板插头对IMU线的问题。仅排除这些具体路线；主模型未改，完整装配仍待完成。'
state['updated_utc']=now
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',assembly='BLOCKED',main_unchanged=True,publication=str(OUT/'publication.json'))))
