#!/usr/bin/env python3
"""Add the bounded A2 evidence/handoff without adopting a failed PCB candidate."""
from pathlib import Path
import csv, hashlib, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
H=ROOT/'hardware/v1_2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def writecsv(p,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def readcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    calc=json.loads((HERE/'calculation_results.json').read_text())
    # Preserve all original endpoint strings and expand every existing harness row.
    src=H/'wiring_P5R7/04_线束汇总.csv';rows=readcsv(src)
    ph={'H01':(2,'5854'),'H02':(2,'5853'),'H03':(3,'5853'),'H04':(8,'5853'),
        'H05':(8,'5853'),'H06':(4,'5853'),'H07':(4,'5853'),'H08':(5,'5854'),
        'I01':(2,'5853'),'SVC01':(2,'5853')}
    expanded=[]
    for old in rows:
        id=old['线束'];series='5856';plug='AMASS XT30U-F candidate; pairing to XT30UPB-M not released'
        contact='integral solder cup; verify exact drawing/insulation';straight=5
        if id in ph:
            n,series=ph[id];plug='JST PHR-'+str(n);contact='JST SPH-002T-P0.5S'
        elif id in ['P_J7','P_J8','P_J9','P_J18']:
            series='5855';plug='JST XHP-'+('2' if id=='P_J18' else '3');contact='JST SXH-001T-P0.6'
        wire=calc['wire_screen'][series]
        note=old['说明'];other='见原始端点；供应商端完整型号未冻结'
        if id in ['H01','H02','H03','H04','H05']:other=plug+' / '+contact+' 同号'
        if id=='H05':note+='；侧出线候选 C1 FAIL，正式板仍直出；不减小导线允许弯曲半径'
        if id=='H06':other='CAM 厂配 JST SH 尾线；厂家线材/接续工艺待核，不将 PH 线硬压 SH 端子'
        if id=='H07':other='PHR-2 ×2 / SPH-002T-P0.5S；旧 SW1 外部操作功能已取消，急停实施待确认'
        if id=='H08':other='充电板未选；PHR-2 到电源 J16；RAW源端保护/共地分支工艺仍缺'
        if id in ['P_J2','P_J3']:other='Pololu D36V50F9 #4094 VIN/GND 或 VOUT/GND 焊盘；板上不依赖通用2.54针承载功率'
        if id in ['P_J4','P_J5']:other='Pololu D24V22F6 #2859 VIN/GND 或 VOUT/GND 焊盘；焊线固定/尾长待机械复核'
        if id in ['P_J7','P_J8']:other='S288 原厂线；电机端型号/编号/线材待厂家确认，禁止猜配'
        if id=='P_J9':other='SCS0009 原厂链路线；上游承受两只并发；动态服务环/另一头插座待核'
        if id in ['P_J11','P_J12']:other='AC05 Ø0.8±0.03 引线，经耐热支承/接续；固定件待选，电阻两端不接地'
        if id=='P_J18':other='CAM USB 5V 供电尾线完整型号未选；不能接单节 BAT；电脑USB前断开机器人5V'
        expanded.append(dict(线束=id,起点=old['起点'],终点=old['终点'],逐针关系=old['逐针关系'],
            自制板端壳候选=plug,自制板端子候选=contact,另一端=other,
            导线筛查样本='Alpha '+series+' (not procurement release)',AWG=wire['AWG'],
            绝缘外径最小mm=wire['OD_min_mm'],绝缘外径最大mm=wire['OD_max_mm'],
            厂家弯曲10D保守mm=wire['minimum_bend_radius_at_max_OD_mm'],
            端后直段分配mm_ASSUMED=straight,成品束外径mm='',裁线长mm='',
            固定及维护='端子后留松弛；独立应力释放；长/束径由完整机械服务路径复核',
            动态寿命='NOT_TESTED',装配状态='BLOCKED',价格='待国内核价',备注=note))
    writecsv(HERE/'harness_detail.csv',expanded)
    ffc=readcsv(H/'wiring_P5R7/06_屏幕FFC待核对.csv')
    for row in ffc:
        if int(row['针号'])>=16:
            row.update(屏幕信号='NC',定义状态='PASS',接线状态='BLOCKED',说明='CAM/LCD官方原理图均未接；不短接GND；实际方向/连续性/线厚弯曲仍待核')
    writecsv(HERE/'ffc_pinmap.csv',ffc)
    tests=[]
    def test(id,pre,op,equipment,observe,passing,stop,risk):
        tests.append(dict(ID=id,前置条件=pre,操作=op,设备=equipment,观测量=observe,通过条件=passing,
          停止条件=stop,风险=risk,记录字段='日期/操作者/实物批次/图纸hash/设置/读数或波形/温度/异常/照片',状态='NOT_TESTED'))
    test('T01','全断电、无电池；接口版本已核','逐针连续性、相邻短路与正负校对','万用表及合适转接治具','针对针关系、相邻阻抗','与当前逐针表一致；不损伤接点','任何编号不符/可疑短路','禁止向小型母端子插入粗探针')
    test('T02','不接电机/电池/外接USB；板上断电短路检查合格','限流电源缓升供电并记录启动','限流电源+万用表','输入电流、5V/3V3、ARM默认状态','逻辑轨在选定器件允许范围内；未解锁不使能','持续限流/电压异常/异味/异常发热','限流值按最小单板负载分阶段设定，不直接使用总保险额定')
    test('T03','J10及线束机械/DRC已通过','断开H05/H07、逻辑重启，核默认禁驱','限流电源+万用表；瞬态需示波器','ARM_Q/FAULT_N/主电源许可','每种故障均清锁；恢复不自动ARM','断线留下有效驱动许可','低速万用表不能证明微秒响应')
    test('T04','只有单个悬空电机、机械支撑、可达急停','低限流短时使能；方向/反馈/超时','限流电源+万用表+协议日志','总线/方向/电压/平均电流','反馈符号与左/右定义一致且超时撤销命令','丢帧/方向相反/限流/堵转','禁止地面直接试站及长时间堵转')
    test('T05','实际电阻/耐热支承/护罩/瞬态设备齐备；电池不参与初次测试','受控能量注入，先小能量，再逐档到声明包络','限流电源+示波器+电流探头或已校准分流器+热电偶','母线/漏极/栅极、脉宽、重复频率、各温度','全波形低于绝对额定并满足厂家重复脉冲降额；周边材料温度合格','过压/长导通/异常升温/接头松动','现有万用表和电源不足完成；不以主观手感代替温升')
    test('T06','实际成品包、保险和完整线束型号冻结','用电子负载/受控测试源验证启动/持续/过载保护配合','电流记录设备+可控负载；合格实验条件','I(t)、压降、接点/导线温度','满足厂家曲线与电池/导线能力并留设计余量','超任何元件允许值','不让用户直接短接锂电池来验证分断能力')
    test('T07','充电板协议/输入限流/CV精度/NTC与包匹配已确认；机器人在托架','先电池模拟器核CC/CV/终止/热敏；再合格成品包充电','USB-PD分析/功率仪、电池模拟器、温度记录','VBUS/输入电流/CV/温度/CHG_N','不超过后板连续输入上限；协议和终止满足包规格；禁驱有效','无正确协议/超CV/无温度保护/机器人被意外上力','当前模块未选，禁止拿BMS过压截止当充电终止')
    test('T08','FFC方向/连续性已核；CAM供电与LCD能力相符','低亮度彩条，逐步并发相机/音频/WiFi','限流电源+万用表+固件帧率日志；异常需示波器','3V3最低值/电流/帧错误/图像/音频','无重启/持续错误；实测余量符合各器件要求','3V3异常/排线热/触摸异常','严禁带电插拔FFC和同时并联电脑USB与机器人5V')
    test('T09','急停执行方案已批准并完成接点电路','逐项按下/复位/断线；验证两个控制回路','限流电源+万用表+状态日志','Q90许可/ARM清除/重新解锁','急停清除使能；释放不会自动ARM','任一状态自动重启执行器','切断力矩可能倒下；先机械支撑，双接点不是认证冗余')
    writecsv(HERE/'test_plan.csv',tests)
    # Evidence index separates a successful HTTP fetch from a usable source document.
    evidence=[]
    for p in ['source_downloads.json','more_sources.json']:
        evidence+=json.loads((HERE/p).read_text())
    for row in evidence:
        row['evidence_status']=row['status']
        if row['id']=='idec_xa':row['evidence_status']='BLOCKED';row['reason']='Redirected to home HTML; not a retrieved datasheet'
    for id,path,url in [
      ('lcd_schematic','sources/lcd_schematic_full.pdf','https://media.githubusercontent.com/media/waveshareteam/1.85inch-Touch-LCD-Module/main/schematic/1.85inch%20Touch%20LCD%20Module.pdf'),
      ('laska_schematic_v11','sources/laska_v11.pdf','https://raw.githubusercontent.com/LaskaKit/PD-IP2326_2-3S_Charger/main/HW/IP2326_2-3S_charger_v1-1.pdf')]:
        p=HERE/path;assert p.read_bytes().startswith(b'%PDF')
        evidence.append(dict(id=id,path=path,url=url,access_date='2026-10-02',sha256=sha(p),evidence_status='PASS'))
    evidence.append(dict(id='lcd_lfs_pointer',path='sources/lcd_schematic.pdf',evidence_status='NOT_APPLICABLE',reason='Git LFS pointer; replaced by validated full PDF, never treated as source content'))
    dump(HERE/'evidence_index.json',evidence)

    # Current native sources are immutable. Include both PCBs and schematics in receipt.
    native={}
    for kind,rev in [('motion','P5R7'),('rear','P5R7'),('power','P5R6'),('imu','P5R4')]:
        name='MORI_'+kind+'_'+rev
        for ext in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru']:
            p=H/'kicad'/name/(name+ext);native[str(p.relative_to(ROOT))]=sha(p)
    geometry=json.loads((HERE/'j10_candidate/reports/geometry.json').read_text())
    drc=json.loads((HERE/'j10_candidate/reports/drc.json').read_text())
    payload={'revision':'V1.2-H0.5-P5R7','addendum_id':'P5R7-prearrival-A2','date':'2026-10-02',
       'status':'BLOCKED','base_handoff':'hardware/v1_2/handoff/mechanical_P5R7.json',
       'base_handoff_sha256':sha(H/'handoff/mechanical_P5R7.json'),
       'scope':'selection evidence, wiring constraints and failed fixed-hole J10 trial; no released PCB/outline changes',
       'mechanical_request':'mechanical/studies/prearrival_finish/HARDWARE_INPUT_REQUEST.md',
       'mechanical_received_calculation':calc['inputs'][0],
       'mechanical_received_revision':calc['mechanical_revision'],
       'native_source_manifest':native,'native_boards_replaced':False,'mechanical_main_modified':False,
       'J10_side_entry':geometry,
       'J10_native_check':{'ERC_violations':0,'DRC_errors':sum(v['severity']=='error' for v in drc['violations']),
          'DRC_warnings':sum(v['severity']=='warning' for v in drc['violations']),'unconnected':len(drc.get('unconnected_items',[])),
          'status':'FAIL','report':'hardware/v1_2/prearrival_20261002/j10_candidate/reports/drc.json'},
       'brake_resistors':[{'id':id,'mpn':mpn,'ohm':ohm,'body_max_diameter_mm':7.5,'body_max_length_mm':18,
            'wire_diameter_mm':.8,'wire_tolerance_mm':.03,'lead_span_mm':63,'lead_span_tolerance_mm':1,'mass_nominal_g':1.9,
            'data_status':'VENDOR_DOCUMENTED','thermal_clearance_mm':None,'mount_holes':None,
            'mounting_release':False,'pulse_qualification':'BLOCKED','bench':'NOT_TESTED'}
           for id,mpn,ohm in [('wheel','AC05000005608JAC00',5.6),('head','AC05000001009JAC00',10)]],
       'fuse':{'candidate':'029707.5WXNV','holder_candidate':'0FHM0001SXJ','adopted':False,'holder_dimensions_mm':None,
               'status':'BLOCKED','missing':['pack fault current/protection coordination','holder complete drawing','CN quote']},
       'charger':{'selected_mpn':None,'status':'BLOCKED','candidates_reviewed':['PWChip Module140','LaskaKit LA123029'],
                  'reference':'hardware/v1_2/prearrival_20261002/power_selection.md'},
       'physical_disable':{'former_external_SW1_function':'RETIRED; native footprint preserved',
            'installation_decision':'PENDING_USER','implementation':'BLOCKED'},
       'harness':'hardware/v1_2/prearrival_20261002/harness_detail.csv',
       'harness_length_and_bundle_diameter':'BLOCKED; no fabricated bend or wire sizes',
       'FFC':{'pin16_17_18':'NC at both schematic ends','cable':'vendor supplied same-side 18P 0.5mm 200mm',
          'thickness_mm':None,'bend_radius_mm':None,'fitted_pin1_orientation':'BLOCKED','direct_plug_approved':False},
       'physical_tests':'NOT_TESTED','procurement_release':False,'manufacturing_release':False}
    handoff=H/'handoff/mechanical_P5R7_prearrival_A2.json';dump(handoff,payload)

    for kind in ['components','electrical_interfaces']:
        p=ROOT/'contracts'/(kind+'.json');raw=p.read_bytes();original=json.loads(raw);d=json.loads(raw)
        backup=HERE/'inputs'/(kind+'_before_A2.json')
        if not backup.exists():backup.write_bytes(raw)
        d['prearrival_A2']={'id':payload['addendum_id'],'date':'2026-10-02',
          'handoff':str(handoff.relative_to(ROOT)),'report':'hardware/v1_2/prearrival_20261002/README.md',
          'evidence_index':'hardware/v1_2/prearrival_20261002/evidence_index.json',
          'J10_candidate_status':'FAIL; not adopted','physical_tests':'NOT_TESTED','manufacturing_release':False}
        if kind=='components':
            for c in d['components']:
                if c['id'] in ['p1_dump_wheel','p1_dump_head']:
                    c['data_status']='VENDOR_DOCUMENTED'
                    c['dimensions_mm']={'body_max_diameter':7.5,'body_max_length':18,'lead_diameter':.8,'lead_diameter_tolerance':.03,'lead_span':63,'lead_span_tolerance':1}
                    c['mass_g']=1.9;c['source_date']='2026-10-02'
                    c['per_field_evidence']={'dimensions_mm':'Vishay28730 Rev05-Dec-2024 p4','mass_g':'vendor nominal, not measured'}
                    c['selection_status']='CANDIDATE_REPETITIVE_PULSE_AND_MOUNTING_PENDING'
                    c['missing']=['repetitive pulse/thermal qualification','complete heat-isolated mount','CN landed quote']
                    c['mounting_release']=False
                if c['id']=='lcd_cable':
                    c['data_status']='VENDOR_DOCUMENTED';c['source_date']='2026-10-02'
                    c['per_field_evidence']={'pitch_positions_length_contact_sides':'Waveshare35079 package list','thickness_bend_and_mated_orientation':'UNKNOWN'}
                    c['missing']=['cable thickness/strip/stiffener/bend specification','pin1 physical mating orientation','CAM3V3 current margin','CN order inclusion/quote']
                if c['id']=='physical_disable':
                    c['selection_status']='NATIVE_SW1_RETAINED_EXTERNAL_OPERATION_CANCELLED'
                    c['notes']=c['notes'].split(' A2: exterior switch')[0]+' A2: exterior switch and opening cancelled by user M1.38. Robot emergency-stop implementation remains BLOCKED; native SW1 is not proof of accessible operation.'
                if c['id']=='p4_external_master_fuse':
                    c['shaft_hole_interface']=None
                    c['candidate_A2']={'fuse':'029707.5WXNV','holder':'0FHM0001SXJ','rating_A':7.5,'adopted':False,'status':'BLOCKED'}
        else:
            for row in d['display_ffc']['pin_number_review']:
                if row['pin']>=16:
                    row.update(display_net='NC',number_mapping_status='DOCUMENT_MATCH',notes='A2: official LCD schematic L1 pin16-18 not connected, matching CAM NC; physical orientation/continuity pending')
            d['display_ffc']['matching_status']='SIGNALS_AND_RESERVED_NC_DOCUMENTED; PHYSICAL_MATING_AND_POWER_PENDING'
            d['display_ffc']['A2_evidence']='hardware/v1_2/prearrival_20261002/ffc_pinmap.csv'
            d['safety']['physical_disable_implementation_status']='BLOCKED: external SW1 opening cancelled M1.38; native control topology retained, replacement installation undecided'
            add=d.setdefault('mechanical_handoff_addenda',[])
            if str(handoff.relative_to(ROOT)) not in add:add.append(str(handoff.relative_to(ROOT)))
        assert d['revision']==original['revision'],'No released PCB revision change'
        assert p.read_bytes()==raw,'Concurrent edit; re-read and merge before writing'
        dump(p,d)
    dump(HERE/'publish_manifest.json',{'handoff_sha256':sha(handoff),'native_sources':native,
        'contracts_after':{kind:sha(ROOT/'contracts'/(kind+'.json')) for kind in ['components','electrical_interfaces']},
        'harness_rows':len(expanded),'FFC_rows':len(ffc),'test_rows':len(tests),
        'manufacturing_outputs_exported':False})
    print('A2 evidence published; failed J10 candidate NOT adopted.')

if __name__=='__main__':main()
