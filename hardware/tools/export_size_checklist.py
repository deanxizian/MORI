#!/usr/bin/env python3
"""Keep the user's original blank checklist; export a sourced selection copy."""
from pathlib import Path
import csv
ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((ROOT/'dimensions/hardware_size_checklist.csv').open(encoding='utf-8-sig')))
# Catalog facts and allocated clearances are kept separate from measured values.
selection = {
 'wheel_motor': ('Pololu4863', '整体最大Ø25×65含编码器帽；分段/支架以厂家图为准', '20cm原厂线；自定义XH6；出线和弯折待样品', '98', 'NOT_TESTED', 'motor_selection.md；sources/motor25_drawing.pdf'),
 'encoder': ('Pololu4863集成48CPR', '整体尾帽最大Ø25，与Ø23占位冲突', '与电机同一6线束；5V供电+LVC14转换', '计入电机', 'FAIL', 'sources/motor25_drawing.pdf'),
 'motor_shaft': ('Pololu4863 4mm D轴', 'Ø4×外伸12.5；扁位3.5；短于占位14', '带轮夹紧长度、轴向止挡未选定', '计入电机', 'NOT_TESTED', 'sources/motor25_drawing.pdf'),
 'wheel': ('MORI-W95-W18 Rev0定制', 'Ø95×18目标，实物未制作', '保留独立6mm承重轴；不由电机悬臂承重', '轮系预算130/对', 'NOT_TESTED', 'mechanical_interfaces.json'),
 'wheel_axle': ('MORI Ø6×53.5定制轴候选', '制造图/材质/轴肩/轴向固定待定', '4mm电机轴与6mm轮轴通过皮带连接', '计入轮系', 'NOT_TESTED', 'mechanical_change_requests.md'),
 'wheel_bearing': ('NSK686ZZ ×4', '目录内6×外13×宽5，2.69g/只', '尺寸名义匹配；13.6试配孔仍需修配验收', '2.69/只', 'PASS', 'sources.md：NSK600系列；仅目录包络对照PASS，装配NOT_TESTED'),
 'drive_pulley': ('27T/2mm节距候选，精确SKU HOLD', '节圆17.189；挡边/轮毂/总宽待图', '电机孔4mm D/轮轴孔6mm；需独立夹紧', '计入轮系', 'NOT_TESTED', 'mechanical_change_requests.md'),
 'drive_belt': ('150mm周长/2mm节距/6mm宽候选，HOLD', '宽6大于预留4；等径带轮中心距48', '现中心距47.424，需张紧/轴距更改', '计入轮系', 'FAIL', 'mechanical_change_requests.md'),
 'head_servo': ('DFRobot SER0037 270°', '本体22.9×12.3×22.6；耳另计，宽超12', '23.6×12.6开口仅0.15/侧；JR3P，275mm线', '11.2', 'FAIL', 'sources/servo270.html；安装耳/有效行程未实测'),
 'servo_output': ('SER0037 20T/1.9花键', '不同于当前Ø4占位，配套舵盘接口需重画', '厂家M1.6×5螺钉；拆传动找中心', '计入舵机', 'FAIL', 'sources/servo270.html'),
 'head_bearing': ('NSK6805ZZ候选，HOLD', '内25×外37×宽7，三维比预留各大1', '须改轴/轴承座/轴向叠层；不压缩0.8mm头身间隙', '计入轴承紧固件预算', 'FAIL', 'sources.md：NSK6805ZZ'),
 'display_panel': ('Waveshare19192台架屏', '有效Ø32.4；玻璃外形/厚度未知；不满足Ø60', '正面光学改版待审；未缩放实屏', '模块预算15', 'FAIL', 'display_imu_selection.md'),
 'display_pcb': ('Waveshare19192', 'PCB40.4×37.5；总厚、孔位待确认', '接插件与器件不计入裸板厚度1.6', '计入显示模块', 'NOT_TESTED', 'sources/display_docs.html'),
 'display_connector': ('Waveshare19192 PH2.0 8P', '插头、出线后包络待实物', '头部转动线缆预留15mm弯折估值，±65°扫掠待测', '计入线束', 'NOT_TESTED', 'wiring.csv'),
 'face_protector': ('保留结构外观，材料待定', 'Ø65.4×1.2为结构目标；非供应商尺寸', '透光、胶层、遮光、可拆性待实测', '计入LCD及面罩预算', 'NOT_TESTED', 'mechanical_change_requests.md'),
 'battery': ('ANSMANN2447-0105候选，HOLD', '39×71×18，长度超过70；托盘70.6也不足', '12cm线，要求工厂加有极性插头；另留弯折与防磨', '99', 'FAIL', 'sources/ansmann_candidate.pdf'),
 'controller': ('ESP32-S3-DevKitC-1-N8R8 v1.1', '实际外形待核；分配65×30×18净空超过预留', '两microUSB留15mm插拔、天线末端15mm暂定净空', '板卡预算内', 'NOT_TESTED', 'architecture.md；净空是设计分配，不冒充实物尺寸'),
 'driver': ('Pololu2130 DRV8833', '平面20.3×17.8；高度3为未测估值', '针/线/新增0.39Ω电阻高度另核', '板卡预算内', 'NOT_TESTED', 'sources/driver_module.html'),
 'imu': ('Adafruit4438 LSM6DSOX', '25.6×17.8×4.6，三轴超预留', '刚性安装，短I2C线；方向和孔位待实测', '1.7', 'FAIL', 'sources/imu.html'),
 'bms': ('随ANSMANN工厂包，不选独立板', '不得将原32×4×22占位当成已适配', '包内保护/均衡/回灌规格待厂商确认', '计入电池', 'NOT_APPLICABLE', 'power_budget.md'),
 'charger_regulator': ('外置匹配充电器+Pololu2831/2858两路稳压', '三件不同功能，不占单一32×6×28包络', '充电器匹配HOLD；稳压/线缆/高度待安装', '板卡预算内', 'FAIL', 'power_budget.md'),
 'usb': ('DevKit原生双microUSB调试', '当前USB-C占位不是所选板接口', 'USB前拔J12；J14保留；外壳服务接口待重做', '计入主控', 'FAIL', 'power_budget.md'),
 'switch': ('额定≥5A/12VDC总开关，精确SKU HOLD', '8×7×5占位未经额定/安装验证', '还需可触及硬件急停，XB5AS8444仅外部台架', '线束/夹具预算内', 'NOT_TESTED', 'safety.md'),
}
for row in rows:
    v = selection[row['项目ID']]
    row.update({'候选型号':v[0], '实测尺寸':'未实测', '接口/连接器尺寸':v[2],
                '质量/g':v[3], '尺寸复核状态':v[4], '目录尺寸或明确估值':v[1],
                '核对依据及边界':v[5]})
with (ROOT/'dimensions/selection_size_checklist.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
print('Exported',len(rows),'selection rows; no measured dimensions fabricated')
