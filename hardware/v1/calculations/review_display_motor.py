#!/usr/bin/env python3
"""H0.3 selection review; simulation results are never bench results.

Run: hardware/.venv-v1/bin/python hardware/v1/calculations/review_display_motor.py
Uses the archived H0.1 mass envelope as a sensitivity input, not a new assembly.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import coupled_balance as plant
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1'
OUT = H / 'reviews'
G = 9.80665


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def initial_correction_torque(p, theta_deg, alpha):
    """Per-wheel torque for theta_ddot=-alpha at rest; includes motor reaction.

    A*xdd + b*thdd = tau/r
    b*xdd + C*thdd = m*g*l*sin(theta) - tau
    Does not include finite feedback delay, tyre slip, compliance or losses.
    """
    theta = math.radians(theta_deg)
    A, b = plant.plant_terms(p, theta)[0]
    C = p['Jbody'] + p['body_mass'] * p['l'] ** 2
    tau = (p['body_mass'] * G * p['l'] * math.sin(theta)
           + (C - b * b / A) * alpha) / (1 + b / (A * plant.R))
    # Check the analytical inverse against the coupled equations.
    acc = np.linalg.solve(plant.plant_terms(p, theta),
                          [tau / plant.R, p['body_mass']*G*p['l']*math.sin(theta)-tau])
    assert abs(acc[1] + alpha) < 1e-10
    return tau / 2


def main():
    OUT.mkdir(exist_ok=True)
    geometry = json.loads((ROOT / 'config/geometry.json').read_text())
    plant.R = geometry['wheel_diameter_mm'] / 2000
    inp = OUT / 'historical_mass_envelope_input.json'
    if not inp.exists():
        source = H / 'reports/mass_inertia.json'
        raw = source.read_bytes()
        old = json.loads(raw)
        write(inp, {'source': str(source.relative_to(ROOT)),
                    'source_sha256': hashlib.sha256(raw).hexdigest(),
                    'status': 'ASSUMED',
                    'scope': 'Archived H0.1 sensitivity envelope with FIT0521 belt layout; NOT H0.3 actual mass/inertia. Head in neutral; COM trim assumed.',
                    'scenarios': {s['case']: s['parameters'] for s in old['scenarios']
                                  if s['yaw_deg'] == s['pitch_deg'] == 0}})
    inputs = json.loads(inp.read_text())
    scenarios = inputs['scenarios']
    motor_nm = 300 / 1000 * G / 100
    torque_rows, runs = [], []
    caps = [('FIT1034_optimistic_direct', motor_nm),
            ('FIT1034_1to1_efficiency_85pct', motor_nm*.85),
            ('requirement_0p10', .10), ('requirement_0p20', .20)]
    for case, p in scenarios.items():
        torque_rows.append({'case': case, 'total_mass_kg': p['total_mass'],
            'body_mass_kg': p['body_mass'], 'com_height_above_axle_m': p['l'],
            'initial_tilt_deg': 10,
            'zero_angular_acceleration_Nm_per_wheel': initial_correction_torque(p, 10, 0),
            'corrective_2_rad_s2_Nm_per_wheel': initial_correction_torque(p, 10, 2),
            'corrective_5_rad_s2_Nm_per_wheel': initial_correction_torque(p, 10, 5)})
        k = plant.gain(p)
        for name, cap in caps:
            for delay in [2, 10]:
                for deadband in [0, .008]:
                    result, _, _ = plant.simulate(p, k, cap, delay,
                                                  theta0=10, deadband_nm=deadband, lag_ms=6)
                    result.update(case=case, cap_case=name,
                                  gains_for_simulation_only=k.tolist())
                    runs.append(result)
    summary = {name: {'criterion_met': sum(r['criterion_met'] for r in runs if r['cap_case']==name),
                      'run_count': sum(r['cap_case']==name for r in runs)} for name, _ in caps}
    old_d, new_d = 32.4, 53.28
    display = {'old_active_diameter_mm': old_d, 'new_active_diameter_mm': new_d,
        'mechanical_placeholder_diameter_mm': geometry['display']['active_diameter_mm'],
        'diameter_ratio': new_d/old_d, 'active_area_ratio': (new_d/old_d)**2,
        'old_area_fraction_of_placeholder': (old_d/geometry['display']['active_diameter_mm'])**2,
        'new_area_fraction_of_placeholder': (new_d/geometry['display']['active_diameter_mm'])**2,
        'unit_price_cny': 105.30, 'price_delta_cny': 105.30-71,
        'resolution_px': [480,480], 'rgb565_frame_bytes': 480*480*2,
        'rgb565_double_buffer_bytes': 480*480*4,
        'full_frame_30fps_payload_Mbit_s': 480*480*16*30/1e6,
        'assumed_QSPI_40MHz_raw_Mbit_s': 160,
        'vendor_typical_input_W_5V_colour_bar': 5*.116,
        'note': 'Bandwidth excludes commands, WAIT stalls, driver overhead, camera/audio contention; 40MHz is an initial design assumption. No measured fps/power. 262K panel colour specification does not by itself confirm RGB565 host setup.'}
    out = {'revision': 'V1-H0.3', 'date': '2026-09-22', 'calculation_run': 'PASS',
        'hardware_validation': 'NOT_TESTED', 'input': inputs,
        'geometry_sha256': hashlib.sha256((ROOT/'config/geometry.json').read_bytes()).hexdigest(),
        'display': display,
        'torque': {'FIT1034_vendor_gf_cm':300, 'converted_Nm':motor_nm,
            'continuous_rating_confirmed':False, 'wheel_radius_m':plant.R,
            'initial_state_requirements':torque_rows,
            'provisional_sourcing_target': {'continuous_wheel_Nm':.10, 'short_peak_wheel_Nm':.20,
                'qualification':'Engineering sourcing target only, not a proved minimum; continuous at thermal equilibrium and low battery, peak duration/current map must be specified and tested.'},
            'decision':'Remove FIT1034 direct/1:1 wheel drive from primary BOM. A future reduction design needs separate mechanical, inertia, efficiency and current/thermal validation.',
            'summary':summary, 'runs':runs,
            'limitations':['Historical 1.0–1.4kg mass envelope, not present assembly measurement.',
                '10deg initial tilt and 2/5rad/s² correction are explicit engineering scenarios, not measured external push tests.',
                'Rigid flat ground, no slip/compliance or motor torque-speed/thermal map. 6ms actuator lag, 2/10ms delay and 0/.008Nm reversal loss are assumptions.',
                'Unmodified H0.1 LQR is a sensitivity controller, not final firmware or a proof of the minimum achievable motor torque.',
                'FIT1034 torque is generously treated as a constant available cap, although the vendor has not identified continuous conditions.',
                'High-gain unlimited command peak is not the motor sizing requirement.']}}
    write(OUT/'display_motor_review.json', out)
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.8))
    for ax, diameter, label in zip(axes, [old_d,new_d,geometry['display']['active_diameter_mm']],
                                   ['Previous 1.28 in','New candidate 2.1 in','Mechanical placeholder']):
        ax.add_patch(Circle((0,0),geometry['head_diameter_mm']/2,facecolor='#efede7',edgecolor='#9a9995',lw=1.5))
        ax.add_patch(Circle((0,0),diameter/2,facecolor='#151919'))
        ax.text(0,0,f'{diameter:g} mm',color='white',ha='center',va='center',fontsize=12)
        ax.set(xlim=(-57,57),ylim=(-57,57),aspect='equal',title=label)
        ax.axis('off')
    fig.suptitle('Active display diameter relative to the 105 mm head',fontsize=14)
    fig.text(.5,.025,'Scale comparison only. Mounting, cable space and camera fit are not verified.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.92]);fig.savefig(OUT/'display_size_comparison.png',dpi=160);plt.close(fig)
    lines = ['# MORI H0.3：大圆屏与轮驱复核', '',
        '2026-09-22。计算已运行；实机、温升、站立和装配均 NOT_TESTED。', '',
        '撤回 1.28 寸小屏主推荐；新显示主候选为冠显 TS021WVC02NP-B1323B（立创 C55111244）。撤回 FIT1034 2804 的当前直驱/1:1 轮驱主推荐，FOC 路线本身仍保留。', '',
        '## 屏幕与国内采购', '',
        '|项目|原候选|新主候选|', '|---|---:|---:|',
        '|实际圆形显示直径|32.4 mm|53.28 mm|', '|分辨率|240×240|480×480|',
        '|单件公开价，不含运费|¥71.00|¥105.30|',
        '|显示面积比|1|'+f"{display['active_area_ratio']:.2f}|", '',
        '![显示区比例比较](display_size_comparison.png)', '',
        '新件页面实读库存 10 个、1 件起订。价格/库存是当日快照，不是订单；不计满减券或运费券。原模型 Ø58 是预留显示区；新屏实际 Ø53.28，黑色面罩可大于发光区，但不能把发光区画成 Ø58。', '',
        '厂商 V1.2 图纸：LCM 56.18×59.71 mm，厚 2.30±0.15 mm；40 针屏排线展开长 26.90±0.30 mm。独立 TR230S 转接板 34×34 mm、PCB 厚 1.0±0.1 mm；四孔 Ø1.70、中心距 30×30 mm。排针总高、排线弯曲半径和成套净质量尚未知。商城 19.57g 是毛重，不作净重。', '',
        '采购 NP（无触摸）版本；20 针 0.5mm FPC 接口与 2mm 间距 2×7 排针端号不同，不能混用。模块支持像素 SPI/QSPI，由 TR230S 接口桥接；没有增加第三颗应用 MCU。新驱动不能沿用 GC9A01 初始化。', '',
        f"5V 彩条条件典型输入 0.58W；RGB565 缓冲假设每帧 {display['rgb565_frame_bytes']:,}B，双缓冲 {display['rgb565_double_buffer_bytes']:,}B；30fps 净像素载荷 {display['full_frame_30fps_payload_Mbit_s']:.2f}Mbit/s。先用 QSPI 40MHz 预算，必须处理 WAIT 握手；并发摄像头/音频、实际像素格式与驱动仍待验证。不能把原小屏 0.15W 直接沿用到续航。", '',
        '连接器净空、背板与头部舵机/摄像头碰撞检查尚未完成；共享机械契约已交接真实分件尺寸，不改动机械母球或擅自冻结孔位。', '',
        '来源：[立创商品](https://item.szlcsc.com/58799605.html)、[厂商规格书归档](../procurement/evidence/TS021WVC02NP-B1323B_V1.2.pdf)。', '',
        '## FOC 电机为什么需要换', '',
        'FOC 是控制方法，不保证电机输出够大。FIT1034 的 300gf·cm 换算为 0.02942N·m；网页没有明确这是否为可长期持续值，电压/额定电流/功率标注也不自洽。1:1 皮带按假设 85% 效率只有约 0.025N·m/轮。', '',
        '下表复用历史 1.0–1.4kg 包络，区分机身与轮系质量，重心高于轮轴约 66–69mm。这里的 10° 是重心已配平后的初始倾角。较大圆屏、现版机械和新轮驱的实际惯量必须之后重建。', '',
        '|情形/整机质量|10° 时初始角加速度为零|初始回正加速度 2rad/s²|初始回正加速度 5rad/s²|',
        '|---|---:|---:|---:|']
    for row in torque_rows:
        lines.append(f"|{row['case']} / {row['total_mass_kg']:.2f}kg|{row['zero_angular_acceleration_Nm_per_wheel']:.3f}|{row['corrective_2_rad_s2_Nm_per_wheel']:.3f}|{row['corrective_5_rad_s2_Nm_per_wheel']:.3f}|")
    lines += ['', '表内单位均 N·m/轮。仅为初始瞬间的耦合动力学要求，尚未计延迟、有限角速度与摩擦。即使恰好角加速度为零，也不等于能把已有倾倒角速度刹住或稳稳站立。', '',
        '公式：A=M+Jw/r²，b=m·l·cosθ，C=Jbody+m·l²；两轮总扭矩 τ=[mgl·sinθ+(C−b²/A)·α]/[1+b/(Ar)]。包含马达对机身的反作用扭矩，不能用静态 mgl 单独确定平衡电机。', '',
        '随后运行离散控制、饱和、6ms 执行器滞后、2/10ms 反馈延迟及两档损失的 48 个情景。判据为末 1 秒倾角<2°、速度<0.1m/s；>30° 或 >0.8m/s 中止。', '',
        '|每轮可用扭矩情景|满足本次仿真判据|', '|---|---:|']
    for name, cap in caps:
        v=summary[name];lines.append(f"|{name} ({cap:.3f}N·m)|{v['criterion_met']}/{v['run_count']}|")
    lines += ['', '这些结果只说明该模型和控制器的裕量，不能证明更低扭矩绝对无法平衡，也不能证明通过者已经实机站稳。', '',
        '0.10/0.20N·m 两组在 2ms 延迟下均满足本次判据，10ms 下均未满足，说明还必须控制反馈时延并重新调参。单纯增大电机不构成稳定性证明。', '',
        '轮驱采购筛选先提高到**轮端连续约 0.10N·m、短时峰值至少 0.20N·m/轮**，并要求低电量、目标转速、峰值持续时间及温升数据。这是带余量的设计目标；目标输出 0.10m/s 对应约 20rpm，0.30m/s 对应约 60rpm。', '',
        '不直接用 3:1/4:1 减速掩盖不足：电机转子惯量会按速比平方折算，低位轮轴现有空间也不能直接容纳更大的从动轮；布局、齿隙、张力与损耗需重算。2S 低电量还低于 FIT1034/DRI0058 的最低输入要求。', '',
        '更大规格 FIT1036 4015 只作筛查：厂商“额定”与“最大”扭矩表相互矛盾，且最低 12V、体积 Ø45×26mm，未作为主推荐，不以商品标题替代连续能力证据。', '',
        '来源：[FIT1034 厂商页](https://www.dfrobot.com.cn/goods-4230.html)、[FIT1036 厂商页](https://www.dfrobot.com.cn/goods-4232.html)。', '',
        '复算：`hardware/.venv-v1/bin/python hardware/v1/calculations/review_display_motor.py`。完整输入、结果和限制见 [JSON](display_motor_review.json)。没有采购、改固件使能或导出制造文件。', '']
    (OUT/'display_motor_review.md').write_text('\n'.join(lines))
    print(json.dumps({'display':display,'initial_torque':torque_rows,'simulation_summary':summary},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
