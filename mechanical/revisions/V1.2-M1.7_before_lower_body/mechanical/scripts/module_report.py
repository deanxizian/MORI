"""Current simple-module assembly and printing notes, from executed evidence."""

def structure_text(p,structure,mass,checks,bom,service):
    current=mass['totals'];whole=current['whole_robot']['mass_g_rounded'];head=current['head_pitch']['mass_g_rounded']
    before=sum(x['volume_mm3'] for x in structure['before'].values())/1000
    after=sum(x['volume_mm3'] for x in structure['after'].values())/1000
    roof=p['wheel_diameter_mm']/2+p['structure']['simple_modules'].get('drive_roof_top_from_axle_mm',30.5)
    deck_bottom=p['layout']['deck_z_mm']-p['layout']['deck_thickness_mm']/2
    battery_top=p['layout']['battery_center_mm'][2]+p['layout']['battery_max_xyz_mm'][2]/2
    battery_gap=deck_bottom-battery_top
    table='\n'.join('| '+r+' |' for r in [
        '降低安装板 | 完整平板，删除中央穿孔、下沉底托与侧壁 | 上表面Z127，舵机底面直接落在板上；板底Z123',
        f'左右侧板 ×2 | 侧板高度{deck_bottom-roof:g}mm，上下短折边 | 从外侧放入；上、下各2枚M2；不加垫块或立柱',
        '浅双电机底托 | 短鞍座、局部轮轴承座、浅顶面 | 两电机从底部装入，保留共用短底盖',
        'Yaw轴承座 | 原有开口圆筒向下延伸7mm，轴承位置保持 | 两枚M2从上方安装；下端接新板面，无独立垫高件',
        '平板头托 | 两块短平侧板、平后板、直切角和短固定耳 | 后平面贴床为候选；保留原转轴、LCD侧连接及头壳固定点，CAM紧固待确认',
        '浅屏幕框 | 圆环、两只短侧耳、局部相机座 | 先在台面装LCD/相机，再用4枚侧向M2接U形托；可向前取出',
        '俯仰U形托 | 平面U轮廓与短舵机座 | 两侧承重轴承；2枚M2接下面的独立转台',
        'Yaw短转台 | 轴颈、短法兰与薄遮光边 | 独立于U形托安装；保留必要遮光，删除深承重杯壁',
        '电池托盘 | 平底、低侧边与绑带孔 | 先完成底托螺钉，再放入托盘；两枚侧限位螺钉可拆',
        '电机底盖 | 一块薄平板 | 两枚原试配M2从下方操作；垫片压缩量待实物确定'])
    mass_status=next(x['status'] for x in checks['checks'] if x['id']=='structure_mass_targets')
    mass_note=f'质量目标检查为{mass_status}；需结合未四舍五入的质量预算、实物称重和动力试验判断，不能根据取整估重宣布合格。'
    return f'''# MORI {p['revision']} — 简单分件与装配

M1.7将轮胎外径由95增到105mm，轮轴、电机和独立承重轴承一起升高5mm，保持两轮接地和腹部25mm离地。短电机底托顶面升到Z81，侧板相应缩短；电池与托盘整体升高3mm，让出底托螺钉头及抽出路径。轮胎仍是未选型的软材料要求，不能把候选几何当现货。

相机移到额头独立窗口，60mm黑面罩和真实圆屏一起对齐头部正前方中心。相机使用短折台就近安装，不增设细长悬臂。原厂LCD整体上移6.2mm、尺寸不变；黑面罩和显示中心均对齐头球中心。CAM、相机、LCD同属pitch运动组，实际FPC长度与紧固仍待核。M1.6平板头托、直切角、短固定耳以及M1.5低平板继续保留。

保留M1.5降低7mm的身体安装板和无下沉槽设计，板上表面Z127与Yaw舵机底面相接。

保留 **{structure['support_printed_parts_after']}个简单支撑组件**，数量不变。支撑实体总体积约 **{before:.0f} → {after:.0f}cm³**；该头托单件体积和球壳内余量见flat_head_check.json。原16处模块连接继续采用试配M2×12；身体板的4枚候选M3×8保留。头壳固定耳保留原安装点的试配通孔，最终螺钉、嵌件和板卡紧固仍待阶段B。

| 组件 | 保留的形状与作用 | 安装方式 |
|---|---|---|
{table}

## 已执行的检查

- wheels_camera_change.json记录实际轮径/轴高、相机与黑面罩投影间隙及白壳桥接射线；独立相机视场另按99条射线检查。
- flat_head_check.json记录新旧头托的实际网格体积、全部顶点到头球心的距离及球壳内的名义余量；与实际壳体固定耳的配合、双轴运动及工具路径由各自实体检查覆盖。圆孔用于转轴和麦克风通道，主体没有球面裁切。
- lowered_deck_check.json检查舵机底面下15处实际网格射线、板底最低面和实体交叠，验证中央平面与取消下挂托槽。当前电池包络顶面Z{battery_top:g}mm，板底Z{deck_bottom:g}mm，名义竖向余量{battery_gap:g}mm；这不代表真实电池插头和走线已经适配。
- 当前结果：{checks['counts']}。刚性实体与130组双轴姿态中没有观察到超过阈值的未说明干涉时，也不能宣布完整实物适配；LCD两个连接器仍使用已披露的保守代理。
- 新增16处螺钉按直径4.2mm、长度30mm工具杆检查，从上方或两侧操作。先拆外壳；底托接侧板时电池尚未装入；关节先装底座，再装运动器件。完整工具手柄、手指、螺纹啮合和实物扭矩仍NOT_TESTED。
- 屏幕/相机组件向前、侧板向外、Yaw座向上分别按3mm步长进行刚体拆装采样。各项需先拆哪些件写在module_service_checks.json；不把爆炸图当成装配证明。
- 保留电池41步抽出、两电机各21步装入、轮转一周、双轴联合姿态、线束预留与打印网格检查。候选STL单位回读见export_manifest.json。

## 装配顺序

1. 裸底托在台面支撑，装电机、试配垫和短底盖；实际轮输出连接、轴向锁紧仍待采购版本确认。
2. 先接左右侧板，再接顶板。此时不装电池，露出底托4枚上方螺钉；顶板4枚螺钉同样从上方操作。
3. 将Yaw舵机放到降低平板的中央平面，再安装延伸后的Yaw座。底面落座不等于已锁固：舵机安装耳紧固与防转仍待采购版本确认，不能按本模型直接给出最终锁紧扭矩。在台面组Yaw轴承/短转台与俯仰U托；再组双侧轴承和头部U托。
4. LCD与相机先装在浅屏幕框上，连接短排线，再从前方装到头部U托。4枚侧向螺钉在头壳关闭前安装；维修时先拆头壳、断开对应排线，再取出前组件。
5. 安装板卡/IMU、线束和电池托盘。外壳闭合前确认每个螺母、导线和接口，尤其核对电池上方{battery_gap:g}mm名义空间中的实际线束。最后装外壳、轮轴/轮组，禁驱状态手动检查动作。

## 哪些面和零件被删掉

- 延续M1.6：删除头托两侧高圆弧翼和后部球面裁切轮廓，改为平面和直切角。保留短壳体耳、矩形CAM背板、声道孔及天线让位；它们有具体安装或通道用途。
- 延续M1.5：删去舵机下沉托槽、两侧壁与中央贯穿孔；没有新增舵机托座、垫块或隔层。板上的局部主控/IMU安装平面保留。
- 删除承重舱的整片后围墙与多余包围壁，保留两块宽侧板、短折边及必要轴承座。
- 删除头内整片前围墙，屏幕只用浅圆框和两只短侧耳；相机在同一前组件上就近固定。
- 删除俯仰机构的深球杯，保留简单U托、独立短转台及薄遮光边。
- 删除按旧电源/USB占位搭出的专用高架。P1的80×45电源板、完整装件以及充电模块的最终固定片仍 **BLOCKED**；橙色占位仍保留，现阶段不能据此制造完整电装。
- 保留声腔、独立麦克风声道、相机遮光件、关节遮光薄片和外置托架：各有声学、光学或维护作用。外壳与轮毂继续独立分件，轮窝及轮毂尺寸随新轮径重新生成。

## 打印与质量边界

当前整机估重约 **{whole/1000:.2f}kg**，俯仰运动件约 **{head}g**。{mass_note} 这些估算仍按PLA1.24g/cm³、当前支撑件95%有效填充、外壳98%及其他件65%计算，至少±35%不确定度。材料减量来自实际删除网格，没有降低密度假设以求通过。

降低安装板以连续板底贴床，取消了原下挂托槽需要处理的悬空区域；浅框和底盖同样优先大平面贴床。头部U托可将后平面贴床，俯仰U托可将大Y平面贴床。局部耳台、横孔和转台遮光边仍需切片检查支撑。候选STL保留装配坐标，打印方向提示见BOM的print_orientation_candidate字段；尚未进行实际切片/试打。所有配合孔、嵌件、材料层向、静载、冲击、蠕变和疲劳仍需样件验证。

当前模型已生成并实际检查；待硬件确认、待打印、待实机平衡。上一版位于{p['structure']['comparison_baseline']['blend']}；该历史文件仅作对比，不定义当前参数。
'''


def printing_audit(bom):
    hints={
      'Head_Front':'球面外观壳与局部开口，保留；开口朝上/斜放由切片比较',
      'Head_Rear':'球面后壳与维修分缝，保留；分缝朝下作候选',
      'Body_Upper':'上壳承接外观与接口；原4点框架座需承载样件',
      'Body_Lower':'保持球腹、轮窝与离地；局部沉孔需孔壁小样',
      'Speaker_Mount':'声腔的围壁是功能面；开口向上试打，密封与声学未测',
      'Parking_Cradle':'独立维护支撑，平底向下；使用时车轮禁驱',
      'Body_Top_Shroud':'必要薄遮光环，平面向下',
      'Yaw_Stop_Flag':'运动限位短片，平面向下；接触角与强度未测'}
    rows=[]
    for a in bom:
        if a['category']!='PRINTABLE':continue
        n=a['id'];hint=a.get('print_orientation_candidate') or hints.get(n)
        if not hint:
            if n.startswith('Wheel_'):hint='保留简单轮毂/盖/转接片；轴向竖直为试打候选，配合与锁紧未冻结'
            elif n.startswith('Mic_Duct'):hint='短独立声道有必要；避免切片支撑堵住孔'
            elif n.startswith('Coupon'):hint='同材料配合小样，先于整件打印'
            elif n.startswith('Dock_Pad'):hint='软接触垫，材料与压缩量待测；不混入硬壳STL'
            else:hint='小型功能固定/光学/线束件，保留；按开口与最大平面选方向并检查切片'
        rows.append(f"| {n} | {a['name']} | {hint} |")
    return '# 每个候选打印件的作用与试打方向\n\n当前BOM派生，方向只是候选，尚未切片或试打。采购参考件不列为打印件。\n\n| 对象 | 作用 | 简化决定与打印提示 |\n|---|---|---|\n'+'\n'.join(rows)+'\n'
