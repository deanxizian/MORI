> 本文记录H0.1历史动力/功耗模型。H0.2采购更改后，旧模型会拒绝把原质量和电机假设当成新BOM结果。当前可运行的国内预算/电压/能量筛选见 `../tools/build_domestic_bom.py` 和 `../tools/check_domestic_feasibility.py`。

# 重跑 V1 计算

在项目根目录执行：

```sh
python3 -m venv hardware/.venv-v1
hardware/.venv-v1/bin/python -m pip install -r hardware/v1/requirements.txt
python3 hardware/v1/tools/build_catalog.py
hardware/.venv-v1/bin/python hardware/v1/calculations/model.py
```

本次已实际执行。脚本仅写 `hardware/v1/reports/` 自有输出；catalog脚本只写自身候选BOM。`build_interfaces.py`会发布共享契约和根pinmap，不能在另一任务正在改契约时盲目运行；脚本保留机械原分配与首次快照，遇到不同版本电气契约会拒绝覆盖。

质量输入来自 `mechanical/reports/mass_budget.json` 和 `bom.json`，不是凭空设一个整机质量。网格原点惯量用

`I_COM = I_origin − m[(r·r)E − rrᵀ]`

转换，g·mm²乘1e−9变kg·m²；重组原机械模型后的总COM惯量先断言与机械报告一致。替换电池/两电机/两舵机/IMU等质量，并删除显示的重复分块占位质量，再增加实际设计尚未建模的线束/载板/保护小料。未得厂家质量的器件仍标ASSUMED，保留分项。轻/中/重采用打印有效质量0.8/1.0/1.3倍及不同线束/载板余量，不能把它理解成所有零件都用全局20%填充。

坐标变换依V1：`Rz(yaw) Rx(head_pitch)`，yaw组仅Rz，pitch组同时旋转；机身绕轮轴的前倾另按−X。机身质量排除旋转轮系，电机定子/齿轮箱在当前皮带布局属于机身；轮系绕X的惯量计入等效平移质量。4012未知轮毂不能继承此质量分配与安装位置，取得图纸后替换。

平衡的二自由度理想动力学（theta为前倾）为：

```text
A = M_total + sum(J_wheel)/r²
B = m_body*l*cos(theta)
C = J_body_COM + m_body*l²
A*xdd + B*theta_dd = tau_sum/r + m*l*theta_dot²*sin(theta) − rolling_drag
B*xdd + C*theta_dd = m*g*l*sin(theta) − tau_sum − pitch_drag
```

这里明确包括电机对机身的反作用力矩，不只算m*g*l静态力矩。基于该SI模型重新解LQR，仅用于敏感性分析，不复制Hover增益。2ms采样、0.5ms RK4积分、2/10/30ms命令时延、6ms执行器一阶滞后、每轮0.05/0.10/0.20Nm饱和、假设0.008Nm死区和滚动摩擦。初始10°扰动；超过30°或0.8m/s终止，3s后末1s角度<2°且速度<0.1m/s为该仿真的收敛判据。没有轮胎滑移、地面柔性、皮带弹性、电机温度和完整电气动态；模型角度围绕预先校正的平衡点，真实COM前后偏置还需标定。

低电压脚本只作单独敏感性：FIT0521额定6V的空载/堵转端点拟合R与有效输出系数，在4.5/5/6V和不同转速下加1.5A限流；因为厂家中间性能点矛盾，拟合结果不是真实Kt/连续扭矩。FOC没有曲线，保留null。与候选供应商数据相冲突时，不能用仿真“证明电机能用”。

续航使用24.12Wh×80%可用SOC窗口×90%容量/老化余量=17.37Wh；轨转换损耗已计入每状态电池功耗，避免重复扣效率。5.34/7.34/11.34W仅是待测负载情景，所得时间不是续航承诺；若实际平均20W，只有约52min。必须以T14混合工作实测确认。

预算按原币种逐项合计。USD→CNY7.2、EUR→CNY8.0为敏感性假设而非当前汇率；汇率范围另列。未知单价保持null；“已知标价小计”“未知额度情景”“到岸价合规”分别记录。打印原型材料由490.65g打印件×1.2支撑/废料+150g托架/试打假设计算；按70元/kg约51.71元，外包机时/服务价仍未知。

JSON保留浮点数是为了复算；展示质量/重心/惯量只应使用约2位有效数字，不代表实物测量精度。
