#!/usr/bin/env python3
"""Publish H0.3 display selection and withdrawal of unqualified wheel candidate.

Deterministic from archived H0.2. Never overwrite mechanical-owned allocations.
No procurement, GPIO freeze or fabrication release is performed.
"""
import copy
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
H=ROOT/'hardware/v1'
P=H/'procurement'
A=H/'revisions/V1-H0.2'
REV='V1-H0.3'
DATE='2026-09-22'


def read(p): return json.loads(p.read_text())
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvwrite(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
def mechanical_owned(d):
    return json.dumps({k:v for k,v in d.items() if not k.startswith('hardware_')},sort_keys=True)


def main():
    baseline = ROOT / 'config/project_baseline.json'
    if baseline.exists() and read(baseline).get('spec_version') != 'V1':
        raise SystemExit('REFUSED: historical H0.3 publisher cannot overwrite the active V1.2 hardware baseline. Use an archived checkout to reproduce H0.3.')
    assert read(H/'reviews/display_motor_review.json')['calculation_run']=='PASS'
    cat=read(A/'bom_candidates.json')
    parts=read(A/'procurement/domestic_parts.json')['parts']
    for p in parts:
        if p['id']=='LCD_0201213':
            p.update(bom_id=None,selection_decision='撤回主推荐：显示Ø32.4过小，用户要求放大；保留历史采购证据')
        elif p['id']=='FIT1034':
            p.update(bom_id=None,selection_decision='撤回当前直驱/1:1轮驱主推荐；扭矩裕量筛选FAIL',
                engineering_status='FAIL',engineering_issue='约0.0294Nm且连续条件未知；1:1含损耗12/12恢复情景失败。没有可直接采用的减速布局。详见reviews/display_motor_review.md')
        elif p['id']=='DRI0058':
            p.update(bom_id=None,selection_decision='随FIT1034路线撤回主BOM；保留报价比较，不能锁定新轮驱驱动',
                engineering_issue='最低8V；缺已核相电流采样；新电机/电源与控制接口确定后重新选择功率板。')
    screen=copy.deepcopy(next(p for p in parts if p['id']=='LCD_0201213'))
    dimensions={'active_diameter':53.28,'panel_frontplane_WH':[56.18,59.71],
        'panel_depth':2.30,'panel_depth_tolerance':0.15,
        'panel_FPC_unfolded_length':26.90,'panel_FPC_unfolded_length_tolerance':0.30,
        'carrier_pcb_WH':[34,34],'carrier_pcb_thickness':1.0,
        'carrier_hole_diameter':1.70,'carrier_hole_pitch_WH':[30,30],
        'header_assembled_depth':None,'assembled_total_envelope':None}
    screen.update(id='LCD_C55111244',bom_id='LCD',exact_model='TDO 冠显 TS021WVC02NP-B1323B / 立创 C55111244 / TR230S',
        purchase_option='NP无触摸版；不要替换成CP触摸版或仅ST7701S RGB裸屏',
        domestic_product_url='https://item.szlcsc.com/58799605.html',unit_price_cny=105.30,
        subtotal_cny=105.30,published_starting_price_cny=None,price_status='PASS',
        stock_observation='现货10个；1个/袋；最小起订1；最快4小时发货（网页动态快照）',
        price_basis='1+单件阶梯价105.30元；不扣满减券；不含运费',access_date=DATE,
        vendor_dimensions_mm=dimensions,vendor_mass_g=None,
        voltage_or_rating='480×480；SPI/QSPI像素接口，TR230S；VCC3.3–5.5V、典型5V；逻辑3.3V；5V彩条116mA典型',
        shaft_hole_interface='LCM 40P FPC接独立34×34转接板；主机20P/0.5mm FPC或2mm间距2×7排针。两连接器端号不相同；4孔Ø1.70、30×30中心距。',
        selection_decision='新显示主候选：采购规格/单价/现货已核；机械与驱动尚未放行',
        engineering_issue='排针高度/FPC回环/成套净重未知；19.57g为商城毛重。SPI/QSPI WAIT时序、RGB565配置、TR230S驱动及相机音频并发NOT_TESTED。',
        engineering_status='BLOCKED',physical_test_status='NOT_TESTED',
        archived_http_evidence=None,archived_http_sha256=None,
        browser_observation='procurement/evidence/LCD_C55111244_browser_observation.json',
        datasheet='procurement/evidence/TS021WVC02NP-B1323B_V1.2.pdf',
        shipping_basis='地址结算未核；页面运费券不作免邮，运费仍在SHIP额度中')
    parts.append(screen)
    write(P/'evidence/LCD_C55111244_browser_observation.json',{
        'date_local':DATE,'timezone':'Asia/Shanghai','url':screen['domestic_product_url'],
        'method':'从本任务真实cua浏览器AX输出人工摘录；不是HTTP推断',
        'product':'TS021WVC02NP-B1323B','lcsc_code':'C55111244',
        'observed_quantity_1_price_cny':105.30,'observed_stock_pieces':10,'MOQ':1,
        'packing_pieces_per_bag':1,'shipping_promise_text':'最快4小时发货',
        'gross_mass_g':19.57,'net_mass_g':None,
        'not_ordered':True,'shipping_cost_confirmed':False,
        'notes':'静态HTTP捕获405不作为无货；动态页面已实际显示价格和库存。'})
    byid={r['id']:r for r in cat['items']}
    for row in byid.values():row['revision']=REV
    lcd=byid['LCD']
    lcd.update(model=screen['exact_model'],source_url=screen['domestic_product_url'],
        procurement_channel=screen['domestic_product_url'],purchase_option=screen['purchase_option'],
        unit_price=105.30,currency='CNY',price_date=DATE,stock_access_date=DATE,
        vendor_dimensions_mm=dimensions,vendor_mass_g=None,
        voltage_or_rating=screen['voltage_or_rating'],shaft_hole_interface=screen['shaft_hole_interface'],
        notes=screen['engineering_issue'],confirmation_status=screen['selection_decision'],
        stock_observation=screen['stock_observation'],price_status=screen['price_basis'],
        procurement_evidence='procurement/domestic_parts.json#LCD_C55111244',
        shipping_basis=screen['shipping_basis'],selection_status='PRIMARY_CANDIDATE_NOT_RELEASED')
    for key,model in [('WH_FOC','待选：每轮轮端连续约0.10Nm、短时峰值至少0.20Nm的FOC轮驱'),
                      ('FOC_DRV','待选：与新FOC电机/供电及电流控制匹配的成品驱动板')]:
        row=byid[key]
        row['withdrawn_H0_2_reference']={'model':row['model'],'unit_price_cny':row['unit_price'],
                                       'source':row['source_url'],'not_selected':True}
        row.update(model=model,unit_price=None,planning_unit_allowance_cny=None,
            source_url='',procurement_channel='',price_date=None,stock_access_date=None,
            vendor_dimensions_mm=None,vendor_mass_g=None,purchase_option=None,
            voltage_or_rating='输入电压与低电量持续能力、峰值时长未冻结',shaft_hole_interface='待选；不得沿用旧轴/孔位或控制接口',
            domestic_availability_status='BLOCKED',stock_observation='新主型号未选定',
            procurement_evidence='reviews/display_motor_review.md',
            selection_status='BLOCKED',engineering_status='BLOCKED',
            confirmation_status='FIT1034/DRI0058退出主BOM；采购价格不计零，也不继承旧报价',
            price_status='新型号待核；旧型号价格不能充当新方案成本',notes='连续/峰值为工程筛选目标，非认证性能。FOC仍为优先路线；没有自动切换有刷备选。')
    byid['FOC_SUPPLY'].update(model='待新FOC轮驱电压确定后选择匹配供电和回灌路径',
        notes='原45元仅为沿用情景额度，不是报价；2S/驱动范围与回灌需重新确认。')
    cat.update(revision=REV,review_date=DATE,status='PROTOTYPE_DISPLAY_CANDIDATE_UPDATED_WHEEL_RESELECTION',items=list(byid.values()),
        selection_review='reviews/display_motor_review.md',
        physical_models_status='H0.3仅复用历史质量包络做轮驱敏感性分析，不是新屏/新电机实物惯量。')
    write(H/'bom_candidates.json',cat);csvwrite(H/'bom_candidates.csv',cat['items'])
    write(P/'domestic_parts.json',{'revision':REV,'last_update':DATE,'access_date_policy':'各行access_date为实际观察日期，不批量刷新历史库存',
        'procurement_complete':False,'assembly_released':False,'parts':parts})
    write(P/'evidence/observed_stock_register.json',{'revision':REV,'date':DATE,
        'method':'真实网页/浏览器结果人工摘录；每行access_date是观察日期，未重新确认的库存不刷新日期。',
        'records':[{k:p[k] for k in ['id','exact_model','domestic_product_url','unit_price_cny',
            'stock_observation','domestic_availability_status','access_date']} for p in parts]})
    csvwrite(P/'BOM_国内采购核验.csv',parts)
    budget={'revision':REV,'status':'BLOCKED','budget_policy':cat['budget_cny'],
        'full_landed_quote_cny':None,'blocking_reason':'FOC主电机/驱动重选，电池及必要小料报价未闭合',
        'screen_price_delta_cny':34.30,'routes':{}}
    for route in ['FOC','BRUSH']:
        rs=[r for r in cat['items'] if r['route'] in ['COMMON',route]]
        known=sum(r['quantity']*r['unit_price'] for r in rs if r['unit_price'] is not None)
        unknown=[r['id'] for r in rs if r['unit_price'] is None]
        no_allowance=[r['id'] for r in rs if r['unit_price'] is None and r['planning_unit_allowance_cny'] is None]
        partial=known+sum(r['quantity']*r['planning_unit_allowance_cny'] for r in rs if r['unit_price'] is None and r['planning_unit_allowance_cny'] is not None)
        budget['routes'][route]={'domestic_public_price_subtotal_cny':round(known,2),
            'unquoted_rows':unknown,'unquoted_count':len(unknown),'no_valid_allowance_rows':no_allowance,
            'partial_total_with_known_allowances_cny':round(partial,2),
            'planning_total_with_unquoted_allowances_cny':None if no_allowance else round(partial,2),
            'not_a_landed_quote':True,'stock_and_price_complete':False,'risk_reserve_included':False,
            'note':'未选型电机/驱动不按0元补齐；部分小计不是整机总价。'}
    write(P/'budget_domestic.json',budget);write(H/'reports/budget.json',budget)

    mp=ROOT/'contracts/mechanical_interfaces.json';mech=read(mp);before=mechanical_owned(mech)
    env=mech['hardware_candidate_envelopes']
    for key in ['wheel_foc','foc_driver_each','display']:
        row=byid[env[key]['bom_id']]
        env[key].update(candidate_model=row['model'],vendor_dimensions_mm=row['vendor_dimensions_mm'],
            vendor_mass_g=row['vendor_mass_g'],source_url=row['source_url'],domestic_purchase_url=row['procurement_channel'],
            candidate_revision=REV,accessed=DATE,shaft_hole_interface=row['shaft_hole_interface'],
            procurement_status=row['domestic_availability_status'],measurement_status='NOT_TESTED',
            dimension_status='VENDOR_VERIFIED' if row['vendor_dimensions_mm'] else 'ASSUMED',
            vendor_hole_coordinates_mm=None)
    env['display'].update(fit_status='BLOCKED: 按真实Ø53.28显示区适配；LCM/34×34背板/40P排线分开布局，摄像头与舵机净空未验。',
        vendor_hole_coordinates_mm=[[-15,-15],[15,-15],[-15,15],[15,15]],
        hole_coordinate_frame='转接板中心为原点的板内W/H坐标；不代表整机安装位置。Ø1.70孔，不是M2直穿孔。',
        proposed_additional_clearance={'panel_peripheral_mm':1,'rear_connector_and_wire_mm':12,
                                      'note':'ASSUMED候选服务空间；插头高度和FPC弯曲半径未核，不能据此直接开孔。'})
    for key in ['wheel_foc','foc_driver_each']:
        env[key].update(fit_status='BLOCKED: 原FIT1034/DRI0058退出主BOM，重新选型；旧尺寸不能用于冻结机构。',
                        proposed_additional_clearance=None)
    mech['hardware_candidate_revision']=REV
    mech['hardware_handoff'].update(file='../hardware/v1/reviews/display_motor_review.md',status='BLOCKED')
    mech['hardware_display_decision']={'revision':REV,'active_diameter_mm':53.28,
        'mechanical_geometry_status':'待机械任务接受真实器件与组合姿态检查；不缩放硬件、不把现模型当已改完',
        'source':'../hardware/v1/reviews/display_motor_review.md'}
    assert mechanical_owned(mech)==before
    write(mp,mech)
    ep=ROOT/'contracts/electrical_interfaces.json';electric=read(ep)
    electric['procurement_revision']=REV
    update=electric['procurement_update'];update['pinmap_valid_for_new_candidates']=False
    update['no_wiring_release']='H0.1 GPIO表不适用于H0.3；LCD接口和轮驱变化后重新审查引脚/DMA，未冻结。'
    update['changed_candidates']['wheel']={'part':None,'status':'BLOCKED',
        'withdrawn':'FIT1034 + DRI0058 current direct/1:1 route',
        'sourcing_target_wheel_continuous_Nm':.10,'sourcing_target_wheel_peak_Nm':.20,
        'torque_command_unit':'未冻结；无标定不得将电压FOC、PWM或协议整数写成Nm'}
    update['changed_candidates']['display']={'part':screen['exact_model'],'status':'BLOCKED',
        'supply_nominal_V':5,'signal_level_V':3.3,'interface':'TR230S SPI/QSPI pixel write + WAIT handshake; reset',
        'pixel_resolution':[480,480],'chosen_clock_Hz':None,'design_start_clock_Hz':40000000,
        'typical_5V_colour_bar_input_mA':116,'framebuffer_RGB565_assumption_bytes':460800,
        'connector_pin_reference':'../hardware/v1/interfaces/display_TR230S_V1-H0.3.csv',
        'GPIO_assignment':None,'camera_audio_concurrency':'NOT_TESTED','driver':'NOT_TESTED; not GC9A01 compatible'}
    electric['hardware_freeze']=False;electric['pcb_release']=False;electric['procurement_release']=False
    electric['status']='PROTOTYPE_H0_1_PIN_REFERENCE_SUPERSEDED_BY_H0_3_NOT_FOR_WIRING'
    write(ep,electric)

    # Datasheet connector numbering only. The two input headers differ at pins 1/2.
    pin_rows=[]
    base=['GND','VCC','GND','CS#','GND','SDO1','SDO0','SCL','SDO3','SDO2','RESET#','WAIT#','QSPI-INT','D/C#','TP-INT_NC','TP-SDA_NC','TP-SCL_NC','TP-RST_NC','TP-VCC_NC','TP-GND_NC']
    for connector,signals in [('FPC20_0p5mm_XF2M-2015-1A',base),('HEADER14_2mm_2x7',['VCC','GND']+base[2:14])]:
        for i,signal in enumerate(signals,1):
            pin_rows.append({'revision':REV,'part':'TS021WVC02NP-B1323B','connector':connector,'pin':i,
                'signal':signal,'mode':'QSPI candidate','MCU_GPIO':'UNASSIGNED',
                'note':'端号按厂家插座图确认；不按线色/镜像猜线。WAIT为模块就绪，手册方向栏有I/I-O矛盾待确认。无触摸NP版触摸脚NC；QSPI模式D/C不接。',
                'status':'NOT_TESTED','source_pages':'vendor V1.2 pp5–6,17'})
    csvwrite(H/'interfaces/display_TR230S_V1-H0.3.csv',pin_rows)
    lines=['# MORI V1-H0.3 国内采购核验','',
        '2026-09-22更新屏幕和轮驱取舍；其余行保留原观察日期。当前仍不可整套下单。', '',
        '**2.1寸圆屏 C55111244 已核单件 ¥105.30、现货10个；旧1.28寸撤回。FIT1034与DRI0058退出主BOM，FOC主型号重选，不能再把旧268元当新轮驱报价。**', '',
        '[大圆屏与动力复核](../reviews/display_motor_review.md) · [主候选BOM](../bom_candidates.csv) · [分项预算](budget_domestic.json)', '',
        '|用途|采购型号/国内商品页|单价CNY|观察日期/供货|选择结论|','|---|---|---:|---|---|']
    for p in parts:
        price=f"{p['unit_price_cny']:.2f}" if p['unit_price_cny'] is not None else '待核'
        lines.append(f"|{p['purpose']}|[{p['exact_model']}]({p['domestic_product_url']})|{price}|{p['access_date']} / {p['stock_observation']}|{p['selection_decision']}|")
    lines+=['','FOC路线已核价部分 ¥548.30，不含尚未选定的轮驱及其他未报价项；整机规划总额暂留空，不能写成零成本补齐。保留有刷备选的含额度情景 ¥1476.30，仍不是成交总价。屏幕本体仅比旧候选增加 ¥34.30，连接件另计。', '',
        '价格/库存为公开页面快照；未向厂家发消息、未加入购物车、未下单。真实连续扭矩、温升、画面并发和续航均NOT_TESTED。']
    (P/'BOM_国内采购核验.md').write_text('\n'.join(lines)+'\n')
    conflicts=list(csv.DictReader((A/'conflicts.csv').open(encoding='utf-8-sig')))
    for r in conflicts:
        if r['id']=='G01':r.update(status='BLOCKED',evidence='屏幕增加34.30元；FOC主电机/驱动撤回重选，整机总额留空，不把未知费用当0。',release_condition='完成新轮驱及其余未报价行，不再沿用旧1322元情景作为当前总额。')
        if r['id']=='G02':r.update(status='BLOCKED',evidence='FIT1034当前1:1路线筛选FAIL；每轮约0.025Nm含假设损耗，12/12恢复情景未通过。',release_condition='按约0.10Nm连续/0.20Nm短时轮端峰值筛选；校核低电压、热、速比、反馈与安装。')
        if r['id']=='G04':r.update(status='BLOCKED',evidence='改用TDO2.1寸Ø53.28；105.30元现货10。LCM56.18×59.71×2.30，转接板34×34独立布局；舵机仍需耳/行程校核。',release_condition='按真实屏幕/FPC/背板与摄像头、两轴头机构复核组合姿态；不沿用1.28寸夹具。')
    csvwrite(H/'conflicts.csv',conflicts)
    intro='''# MORI V1-H0.3：大圆屏与轮驱重选

屏幕主候选改为 TDO TS021WVC02NP-B1323B（立创C55111244）：实际显示Ø53.28mm、480×480、QSPI/SPI，单件105.30元，2026-09-22页面现货10个。旧1.28寸小屏撤回。

FIT1034 2804 + DRI0058退出当前主BOM，FOC路线保留，具体新轮驱待选。旧268元轮驱报价和1322元整机情景不能当成新方案成本。轮端连续约0.10Nm、短时峰值至少0.20Nm是后续筛选目标，尚非已验证能力。

- [本次复核、尺寸与计算结果](reviews/display_motor_review.md)
- [主候选BOM](bom_candidates.csv) / [国内采购核验](procurement/BOM_国内采购核验.md)
- [可复算脚本](calculations/review_display_motor.py) / [48组仿真JSON](reviews/display_motor_review.json)
- [显示模块端号表](interfaces/display_TR230S_V1-H0.3.csv)：没有擅自分配MCU GPIO

共享契约已交接新屏分件包络并撤销旧轮驱主候选；机械母球、现有模型和固件未改。H0.1 GPIO表不能用于新器件接线。

全部硬件试验NOT_TESTED。V1 KiCad/PCB尚未完成、ERC/DRC未执行，未采购或导出制造文件。历史H0.2文件在revisions/V1-H0.2/。本次仅完成屏幕取舍和轮驱裕量审查，不宣称整机硬件工程已经完成。
'''
    (H/'README.md').write_text(intro)
    top=ROOT/'hardware/README.md';s=top.read_text()
    start=s.find('<!-- H0.3 REVIEW START -->');end=s.find('<!-- H0.3 REVIEW END -->')
    if start>=0 and end>=0:s=s[:start]+s[end+len('<!-- H0.3 REVIEW END -->'):].lstrip('\n')
    top.write_text('<!-- H0.3 REVIEW START -->\n当前硬件候选版本 **V1-H0.3**：大圆屏已换型，旧2804轮驱主推荐撤回。[最新报告](v1/reviews/display_motor_review.md) / [BOM](v1/bom_candidates.csv)。以下H0.2及A0内容为历史。\n<!-- H0.3 REVIEW END -->\n\n'+s)
    files=[H/'bom_candidates.json',H/'bom_candidates.csv',P/'domestic_parts.json',P/'BOM_国内采购核验.md',
        P/'budget_domestic.json',mp,ep,H/'reviews/display_motor_review.json',H/'reviews/display_motor_review.md',
        H/'interfaces/display_TR230S_V1-H0.3.csv']
    assert byid['WH_FOC']['quantity']+byid['HD_SERVO']['quantity']==4
    assert byid['WH_BRUSH']['quantity']+byid['HD_SERVO']['quantity']==4
    assert byid['MCU']['quantity']==2 and byid['CAM']['quantity']==1
    checks={'revision':REV,'status':'PASS','scope':'selection artifact and arithmetic integrity, not hardware qualification',
        'mechanical_owned_allocations_preserved':True,'actuators':4,'main_MCUs':2,
        'historical_GPIO_not_released':True,'physical_test_status':'NOT_TESTED',
        'command':'python3 hardware/v1/tools/publish_display_motor_review.py',
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'files':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    write(P/'validation.json',checks);write(H/'reports/deliverables_manifest.json',checks)
    status=read(A/'reports/validation_status.json')
    status.update(revision=REV,selection_review='reviews/display_motor_review.md',
        artifact_checks={k:v for k,v in checks.items() if k!='files'},
        generated_at_utc=checks['generated_at_utc'],
        historical_H0_2_checks='revisions/V1-H0.2/reports/validation_status.json',
        new_wheel_route='BLOCKED',display_procurement='PASS',display_mechanical_and_driver='NOT_TESTED',
        erc='NOT_TESTED',drc='NOT_TESTED',physical='NOT_TESTED',procurement_release=False)
    write(H/'reports/validation_status.json',status)
    print(json.dumps({'revision':REV,'display_unit_cny':105.30,'display_stock_observed':10,
        'wheel_primary':'BLOCKED_RESELECT','mechanical_allocations_preserved':True,'budget':budget['routes']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
