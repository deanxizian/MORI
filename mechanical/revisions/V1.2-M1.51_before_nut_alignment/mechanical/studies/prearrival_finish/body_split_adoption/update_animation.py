"""One-time source migration; original generator retained in the M1.50 snapshot."""
from pathlib import Path
p=Path('mechanical/scripts/assembly_animation.py');s=p.read_text()
assert "assign(select('Body_Upper'" in s
s=s.replace("('承重桥落座并锁紧', '上壳保持15°／抬高14mm；桥单独下降18mm，再锁两枚M3'","('承重桥落座并锁紧', '外壳未装；桥下降18mm，侧向锁紧两枚M3，车轮后装'")
s=s.replace("('上壳附件台面预装', 'SP3040由两枚M2×5固定在上壳；耳尺寸估算；后接口板一起预装', 84", "('前后壳附件台面预装', '前壳固定SP3040，后壳固定接口板；两片壳分开预装，估算配合待实物', 108")
s=s.replace("('下壳合装', '车轮尚未安装；下壳从底部合入，四枚拼缝螺钉由下方锁紧', 66", "('前壳平移合入', '沿−Y装入前壳；底部一体插舌随后与后壳配合，完整软线随动待验证', 96")
s=s.replace("('上壳与承重桥协同装入', '桥预装螺母与6806轴承；上壳倾15°、桥保持水平，分别托住后下移／前移'", "('承重桥单独装入', '桥预装螺母、嵌件与6806轴承；保持水平，先下移再前移14mm'")
s=s.replace("('上壳回正并固定', '桥已锁紧；上壳从15°／抬高14mm回正落位，再锁框架螺钉', 96", "('后壳合入并锁紧', '后壳沿+Y合入；从四个底部工具孔锁框架螺钉，取消旧拼缝五金', 120")
s=s.replace('STAGE_ORDER=[1,2,3,4,5,6,7,15,19,8,20,9,10,11,21,22,12,13,14,16,17,18]', 'STAGE_ORDER=[1,2,3,4,5,6,7,19,8,9,10,11,21,22,12,13,14,15,16,20,17,18]')
s=s.replace("scene['motion_qualification'] = 'Independent upper shell and level bridge follow prearrival_closure/dual_body_sequence.json (407 sampled nominal positions and two M3 tool paths). The bench-to-insertion-start is a scene cut; full harness, hands and other illustrative stages are not qualified.'", "scene['motion_qualification'] = 'Current front/rear shell modules translate along Y; frame screws enter from below. Saved matrices are checked at half frames. Full flexible harness, human support and physical fits are not qualified.'")
s=s.replace("'Optics_Bench','Upper_Shell'", "'Optics_Bench','Front_Shell','Rear_Shell'")
a=s.index("    assign(select('Body_Upper'");b=s.index("    for side,sign in [('L',-1),('R',1)]:\n        assign(['Wheel_Spacer_",a)
s=s[:a]+'''    assign(select('Body_Front','Frame_Insert_0','Frame_Insert_1',prefix=('Speaker_Insert_',)),15,begin=.01,finish=.03,parent='Front_Shell')
    assign(select('Body_Rear','Frame_Insert_2','Frame_Insert_3',prefix=('Rear_Interface_Insert_',)),15,begin=.01,finish=.03,parent='Rear_Shell')
    from speaker_geometry import speaker_transform
    speaker_back=speaker_transform().to_3x3()@Vector((0,-1,0))
    assign(['Speaker_Gasket'],15,speaker_back*28,begin=.10,finish=.33,parent='Front_Shell')
    assign(['Speaker'],15,speaker_back*34,begin=.27,finish=.52,parent='Front_Shell')
    assign(select(prefix=('Speaker_Screw_',)),15,speaker_back*46,begin=.71,finish=.96,parent='Front_Shell')
    assign(['Rear_Interface_PCB','USB_Receptacle','Power_Switch'],15,(0,0,-24),begin=.20,finish=.68,parent='Rear_Shell')
    assign(select(prefix=('Rear_Interface_Screw_',)),15,(0,0,-20),begin=.69,finish=.94,parent='Rear_Shell')
    assign(select(prefix=('Frame_Screw_',)),20,(0,0,-150),begin=.73,finish=.98)
    # Independent rigid modules; no source mesh edits and no hidden old shell.
    for name,step,sign,finish in [('Front_Shell',16,1,.94),('Rear_Shell',20,-1,.55)]:
        r=roots[name];st=stages[step-1];span=st['end']-st['start']
        for fr,xyz in [(1,(0,sign*220,0)),(st['start']+8,(0,sign*220,0)),
                       (st['start']+round(span*finish),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    # The former bridge path is retained with both shells absent. Stage 8
    # finishes its final 18 mm descent before the transverse bolts arrive.
    st=stages[18];r=roots['Fixed_Bridge']
    for fr,xyz in [(1,(0,-14,144)),(st['start']+12,(0,-14,144)),
                   (st['start']+104,(0,-14,18)),(st['start']+110,(0,-14,18)),
                   (st['end'],(0,0,18)),(stages[7]['start']+8,(0,0,18)),
                   (stages[7]['start']+36,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
''' + s[b:]
a=s.index('    # Presentation-only object material overrides');b=s.index('    for o in list(actors.values())',a)
s=s[:a]+'''    # Highlight the actual fixed bridge without adding shell transparency.
    actors['Yaw_Base'].data=tagged(actors['Yaw_Base'].data.copy())
    actors['Yaw_Base'].data.name=AP+'Yaw_Base_DisplayMesh'
    bridge_mat=mat('Bridge_Highlight',(.045,.29,.39))
    actors['Yaw_Base'].data.materials.clear();actors['Yaw_Base'].data.materials.append(bridge_mat)
''' + s[b:]
s=s.replace("[roots['Upper_Shell'],roots['Fixed_Bridge']", "[roots['Front_Shell'],roots['Rear_Shell'],roots['Fixed_Bridge']")
s=s.replace("'shell_bench':((260,-370,-190),(0,0,134),350)","'shell_bench':((680,-250,-290),(0,0,102),790)")
s=s.replace("'shell_settle':((330,-500,285),(0,0,125),430)","'shell_settle':((450,-650,-100),(0,-40,90),700)")
s=s.replace("'shell_install':((380,-550,355),(0,0,184),800)","'shell_install':((380,-550,355),(0,0,184),670)")
s=s.replace("if s['index'] in [19,8,20]:footer='蓝色：承重桥；上壳半透明显示   |   两件分别支承，线束随动／人工支承待验证'", "if s['index'] in [19,8]:footer='蓝色：独立承重桥；身体外壳后装   |   台面支承、紧固扭矩及线束待验证'\n        if s['index'] in [15,16,20]:footer='前后分壳 · 两组底部定位插舌 · 四处底部工具孔   |   完整带线闭壳未通过'")
a=s.index('上壳附件先在台面预装，');b=s.index('双舵机先在离机座上锁紧；',a)
s=s[:a]+'''身体改为前后两片外壳。承重桥在身体外壳未装时单独下放、前移并锁紧。
前壳喇叭和后壳接口板在台面分别预装；内部总成完成后，前壳沿−Y、后壳沿+Y合入。
底部两组一体插舌定位，四枚原框架螺钉经底部工具孔锁紧；旧拼缝螺钉和嵌件取消。
每片模块含附件的名义平移路径各检查275个位置；保存后的动画另以半帧抽样。
完整软线长度、变形和带线合壳仍未完成，动画未把静态导线示意当作装配证明。
''' + s[b:]
s=s.replace('C压板先从侧面套到转动座，随驱动座一起下放。第16步转动座转60°，','C压板先从侧面套到转动座，随驱动座一起下放。随后转动座转60°，')
s=s.replace("body_evidence=ROOT/'reports/head_retention_body_sequence.json'","body_evidence=ROOT/'reports/body_split_validation.json'")
s=s.replace("'material_only_mesh_copies':['Yaw_Base','Body_Upper']","'material_only_mesh_copies':['Yaw_Base']")
s=s.replace("'upper_shell_path':'Two independent shell/bridge roots; lower and forward together, bridge seats and locks, shell settles last'","'body_sequence_kind':'front_rear','body_shell_path':'Front module -Y, rear module +Y; four frame screws from below; bridge previously fixed with shells absent'")
s=s.replace("'body_sequence_display_stages':[9,10,11]","'body_sequence_display_stages':[8,9,19,20]")
s=s.replace('# Preassembled bridge arrives inside the tilted upper shell at the camera\n    # cut. The independent roots below reproduce the audited two-body path.', '# The bridge is preassembled independently, with both body shells absent.')
s=s.replace('# Stable construction IDs; shell and bridge move independently in stages\n# 19 / 8 / 20. The bridge must lock before the shell settles.', '# Stable stage IDs preserve head/wheel subassemblies; bridge locks before front/rear shells.')
p.write_text(s)
