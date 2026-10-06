#!/usr/bin/env python3
"""Create review tables from current evidence; preserve user-filled quote intake."""
from pathlib import Path
import csv
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1_2'


def read(p):
    return json.loads(p.read_text())


def table(p, rows):
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    cat = read(ROOT / 'contracts/components.json')
    model = read(H / 'reports/engineering_model.json')
    budget = read(H / 'reports/budget_gate.json')
    cad = read(H / 'reports/cad_validation.json')
    rev = cat['revision']
    rows = []
    for p in cat['components']:
        rows.append(dict(component_id=p['id'], model=p['full_model'], required_quantity=p['quantity'],
                         priority=1 if p['id'] in ['wheel_servo','interaction_cam','display'] else 2,
                         selected_product_url='', seller='', selected_variant='', board_revision='',
                         price_cny='', quantity_tier='', minimum_order='', stock='', quote_date='',
                         shipping_cny='', tax_included='', accessories_included='',
                         source_current_status=p['confirmation_status'], reviewer_status='NOT_REVIEWED'))
    intake = H / 'procurement/quote_intake.csv'
    if not intake.exists():
        table(intake, rows)
    tools = [
        ('万用表','OWNED','断电核线、静态电压电流','用户已确认'),
        ('限流电源','OWNED','分级供电；不是吸能负载','型号/范围/分辨率待记录'),
        ('3.3V SWD调试器','NOT_OWNED','F412下载/调试；VTref感测不并接供电','可借用；价格UNKNOWN'),
        ('示波器≥100MHz','NOT_OWNED','6Mbps边沿、瞬态/回灌/启动波形','可借用；探头接地须匹配'),
        ('逻辑分析仪建议≥100MS/s','NOT_OWNED','S288报文和OE/回包间隙','可借用；低速廉价仪器不等价'),
        ('温度探头/记录器','NOT_OWNED','电机/稳压/二极管/电阻温升','可借用；触摸不代替记录'),
        ('电子负载/受控吸能装置','NOT_OWNED','稳压负载及受控回灌','先确认负载能力与保护'),
        ('卡尺、0.1g秤、角度/转速参考','NOT_OWNED','安装/质量/运动标定','借用或补齐；无现有假设'),
        ('托架及外部防摔约束','REQUIRED_NOT_BUILT','充电/维护/首轮平衡','托架打印材料计装机预算，测试约束单列'),
        ('返流焊/SMT装配服务','REQUIRED_QUOTE_PENDING','ICM LGA及细间距器件装配','服务劳动另列；基础打样费用不得漏计'),
    ]
    table(H / 'procurement/test_equipment.csv', [dict(item=a,status=b,purpose=c,note=d,price_cny='UNKNOWN') for a,b,c,d in tools])
    conflicts = [
        ('CAD','PASS','三块原生原理图与已布线PCB；真实ERC/DRC/网表检查已执行','硬件','查看cad_validation.json；不代表实物合格','不阻止继续审查'),
        ('COST','BLOCKED',f"{budget['required_lines']}项主BOM，{len(budget['unknown_price_ids'])}项缺价；仅有206元型号报价小计，最终总价及超额未知",'采购资料+硬件核验','先补三项淘宝链接/所选规格价格；其余按精确MPN小批量核价','完整采购/制造冻结'),
        ('BATTERY','BLOCKED','3S成品包/保护/均衡/NTC/持续与峰值电流未冻结；有尺寸合适的5.2A线索但不能覆盖约6A并发','硬件+供应方','获取可追溯规格与单件供货；据实修改并发限幅或包配置','电池采购/充电与实机上电'),
        ('CHARGER','BLOCKED','USB-C输入/CC或PD/3S CC-CV/NTC/均衡/反灌的成品模块未选定','硬件+供应方','匹配电池后完成模块资格；不能把P1电源板当充电板','充电功能及相关制造冻结'),
        ('POWER_FIT','BLOCKED','80×45×1.6板+16mm高电容及外部模块不符合44×16×10预留','硬件+结构','按mechanical_P1.json重新分配；不得缩放元件','机内电源装配/外壳孔位'),
        ('MCU_ADAPT','BLOCKED','F412RET6 V1.1候选已布线；国内所购版本/堆叠高度/固件板型适配未完成','采购资料+软件+结构','按ADR002选择精确版本，软件独立板型编译，实物高度核验','模块采购/装机/刷写'),
        ('CAM_ENVELOPE','BLOCKED','37×37板框已核；孔径/最高件/插头/净重/天线位置未齐','供应资料+结构','原厂完整图或收到后测量，不把12mm预留当实测','头部完整装机声明'),
        ('LCD_REV','BLOCKED','已核Rev1 STEP9.35mm；PDF9.1参考、孔位约0.06mm差异及采购修订未确认','供应资料+结构','匹配所购修订；保留FPC弯折与插拔空间','最终屏安装孔位'),
        ('FFC','BLOCKED','18P0.5mm200mm同面线已记录；CAM接触朝向与LCD16–18保留脚仍需核实','硬件+台架','完整端到端针序/通断与电压检查；TE在CAM端NC','屏幕接电'),
        ('PHY','NOT_TESTED','6Mbps/1Mbps UART时钟计算可实现；真实TTL门槛、释放、掉电及启动锁存未测','供应资料+台架','T05/T08，需要示波器/逻辑分析仪','执行器使能'),
        ('PROTOCOL','BLOCKED','CRC与长度HOST通过；官方C/Python负数/符号/舍入矛盾已复现','软件+供应方+台架','保留差异报告，明确候选解码，再按实际固件抓包/行为验证','真实扭矩单位/停止语义放行'),
        ('MOTOR_CONTINUOUS','NOT_TESTED','S288连续扭矩与低压曲线未知；56项仿真只是假设力矩条件','硬件+台架','限流/负载/温升/反馈年龄标定，禁止长堵转','宣称扭矩足够/自由平衡'),
        ('POWER_TRANSIENT','NOT_TESTED','P1已画反接、隔离、锁存、监测和双母线吸能；未有热/回灌/浪涌波形','硬件+台架','核稳压/功率电阻脉冲能力、二极管散热与软启动不足','功率上电/制造冻结'),
        ('ASSEMBLY_PARTS','BLOCKED','候选小料MPN、连接器对插件额定、完整模块包络与装配服务未全部确认','硬件+采购资料','按assembly_parts.csv核后缀/原厂封装，精确小批量供应；不把通用库称已审全部料','装配/制造冻结'),
        ('IMU_REV','BLOCKED','ICM原厂预生产版引脚已核，最新量产资料/实际批次及装配轴向待确认','硬件+供应资料+结构','核最新量产封装、刚性安装、DRDY/SPI台架','IMU装配/轴向放行'),
        ('VISION_AUDIO','NOT_TESTED','屏/相机/音频/网络并发资源已分析，没有真实时延/AEC/温升结果','软件+台架','按T07/T15压测并记录P95/P99与音频参考通路','视频跟随/声学性能声明'),
        ('WAKEWORD','BLOCKED','MORI中文离线唤醒模型未训练/取得，定制服务费用未知','软件+用户后续模型决策','保留功能目标，按钮及公开模型先验证；不得修改字符串冒充模型','自定义唤醒验收'),
        ('ENDURANCE','NOT_TESTED','2200mAh估算在18W平均时约55min；非已实现60min','硬件+软件+台架','按混合工况实测Wh/低压/温度，反馈电池质量和功耗','60分钟续航声明'),
        ('LICENSE','BLOCKED','宇树代码非商业条款、部分硬件/模型许可仍需逐项审查','后续发布任务','保留源许可，不统一改MIT，不把公开仓库等同销售授权','未来开源/销售发布资格'),
    ]
    table(H / 'reports/conflicts.csv', [dict(id=a,status=b,missing_or_conflict=c,owner=d,next_action=e,blocks=f) for a,b,c,d,e,f in conflicts])
    text = ['# P1 动力、质量和供电计算摘录','',
            '输入来自当前机械质量/几何与明确假设；计算脚本可运行。未称量、未台架、未自由平衡。完整数值仅保留计算精度，表中适度取整。','',
            '|情景|整机kg|被平衡机身kg|轮系kg|整机重心距地mm|机身COM距轮轴mm|pitch运动件g|',
            '|---|---:|---:|---:|---:|---:|---:|']
    for s, poses in model['scenarios'].items():
        p=next(p for p in poses if p['pitch_deg']==0)
        text.append(f"|{s}|{p['total_mass']:.2f}|{p['body_mass']:.2f}|{p['wheel_mass']:.2f}|{p['center_m'][2]*1000:.0f}|{p['l']*1000:.0f}|{p['head_pitch_mass']*1000:.0f}|")
    text += ['', '各情景对未知材料/器件质量乘0.75/1/1.35，电机与舵机按厂商质量保留，额外电源/线束预留50/90/160g。电池仍约190g假设；实际电源重排将改变COM/惯量。', '',
             '机器人PLA几何估算约%.0fg；加35%%工艺损耗约%.0fg。托架和试打件未得到切片用量，需另计；不得把这个质量当整机已称重或完整采购用料。' % (model['printing']['PLA_robot_g'],model['printing']['PLA_with_35percent_process_waste_g']), '',
             '离线平衡方程含机身/轮系惯量、轮驱反作用、速度降额假设、2/10/25ms延迟、饱和、摩擦和反向损失。每格是满足“最后1s倾角<2°、速度<0.1m/s且不越界”的条件试验数/6。电机是否能连续提供这些力矩未知。', '',
             '|假设每轮连续力矩Nm|light|nominal|heavy|','|---|---:|---:|---:|']
    for tq in [.06,.12,.24]:
        n=[sum(x['criterion_met'] for x in model['simulations'] if x['scenario']==s and x['limit_Nm_per_wheel']==tq) for s in ['light','nominal','heavy']]
        text.append(f'|{tq:.2f}|{n[0]}/6|{n[1]}/6|{n[2]}/6|')
    text += ['', '另有2个重型反向损失情景；共%d个中%d个满足条件。LQR仅用于离线敏感性诊断，不作为固件调参。S288的0.6Nm最大/堵转值不作连续额定。' % (len(model['simulations']),sum(x['criterion_met'] for x in model['simulations'])), '',
             '同一诊断控制器没有针对各力矩上限重新整定，带延迟与饱和时结果可不单调；此表不能用来给电机能力排序，也不是可靠性成功率。', '', '![延迟敏感性](balance_sensitivity.png)', '', '|头部计算|最不利需求Nm|4.8V额定/需求|','|---|---:|---:|']
    hp=max(model['head_loads'],key=lambda x:x['total_pitch_Nm'])
    hy=max(model['head_loads'],key=lambda x:x['total_yaw_Nm_at_up_to_10deg_body_lean'])
    text += [f"|pitch|{hp['total_pitch_Nm']:.3f}|{hp['rated_ratio']:.2f}|",f"|yaw，含机身±10°倾斜|{hy['total_yaw_Nm_at_up_to_10deg_body_lean']:.3f}|{hy['yaw_rated_ratio']:.2f}|",'',
             '采用5rad/s²加速度、0.01–0.04Nm线缆/摩擦假设；按所核旧SCS版本4.8V连续额定0.65kg·cm。约1倍多的条件余量不宽裕，实际线缆阻力、零点/联合姿态和供货版本需验证。', '',
             '|功耗假设状态|电池输入W|9.9V输入A|','|---|---:|---:|']
    text += [f"|{x['state']}|{x['battery_W']:.2f}|{x['battery_A_at_9p9V']:.2f}|" for x in model['power_states']]
    text += ['', '功耗是分轨输出假设经效率换算后的输入预算，不是电机实测数据。maintenance_charge一行只是维护逻辑负载，不能理解为已实现边充边开机。', '',
             '3S2200/2600mAh分别24.42/28.86Wh；80%可用能量、再留15%余量时，60min允许平均输入16.6/19.6W。2200mAh/18W仅约55min；不得先保证60min。早期interface_calculations另以90%转换效率算负载侧，不与这里电池侧功率叠乘。', '',
             '重型保守回灌脉冲加倍后%.3fJ；1000µF从9.5升到10.8V仅吸收%.3fJ。5.6Ω电阻在10.8V约%.1fW、等效脉冲约%.0fms；必须匹配实际脉冲曲线/重复率与散热，5W铭牌不能证明合格。' % (model['regen']['doubled_design_pulse_J'],model['regen']['cap_energy_9p5_to_10p8V_J'],model['regen']['dump_power_at_10p8V_W'],model['regen']['pulse_seconds']*1000), '',
             '当前29mm轮轴悬臂/6mm轴承间距下，3g外轴承反力约%.0fN；4mm实心轴弯曲应力约%.0fMPa。缺轴材/疲劳/轴承额定/打印座数据，结论为需求估算，未判承载通过。' % (model['bearing']['three_g_outer_N'],model['bearing']['shaft_4mm_3g_bending_MPa']), '',
             '完整结果：[engineering_model.json](engineering_model.json)、[电源容差/线宽](power_integrity.json)、[预算门槛](budget_gate.json)、[全部平衡情景](balance_sweep.csv)。']
    (H/'reports/calculation_summary.md').write_text('\n'.join(text)+'\n')
    tools_env=read(H/'reports/tool_environment.json')
    tools_env.update(kicad_version=cad['kicad_version'],ERC='PASS' if all(x['counts']['erc']==0 for x in cad['boards'].values()) else 'FAIL',DRC='PASS' if cad['status']=='PASS' else 'FAIL',new_v1_2_kicad_project_created=True,native_projects=list(cad['boards']),manufacturing_exported=False,updated_utc=datetime.now(timezone.utc).isoformat(),command='kicad-cli --version; exact validation argv in reports/cad/*/validation_commands.json')
    (H/'reports/tool_environment.json').write_text(json.dumps(tools_env,ensure_ascii=False,indent=2)+'\n')
    print(rev, len(rows),'quote rows; conflicts and model summary refreshed; CAD',cad['status'])


if __name__=='__main__':main()
