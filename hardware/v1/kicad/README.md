# V1 KiCad 状态：BLOCKED

实际工具为 KiCad CLI **10.0.6**，已检查 `sch erc --help`、`pcb drc --help`。这不是工具缺失。V1预算、器件包络和电源门槛没有通过，遵照用户要求“先冻结可核验器件与接口，再绘制电路”，本目录目前没有新V1原生原理图或PCB，也没有Gerber/装配文件。

需要先解除的依赖包括：FOC确切驱动/协议/供电、可完成采购的总价、2S充电/保护/均衡匹配、峰值放电、M0031 FPC和供电图、两舵机/屏幕/电源的机械冲突、功率/保护连接器额定、板框与孔位。随意以通用连接器代替这些引脚再画一块“0 ERC/DRC”的板，不能构成可复核原型。

`hardware/kicad/` 与 `hardware/revisions/A0.5/kicad/` 的原生工程保留，但属于旧架构。其已有ERC/DRC结果**不代表四执行器、双MCU、双轴头、摄像头V1通过**。本轮不复制改名伪装新板。

后续V1细化范围：两个WROOM模组（完整电源/EN/BOOT/USB下载）、IMU和DRDY、两种互斥轮驱接口、双舵机PWM/反馈保护、跨域UART/I2S、屏幕/摄像头/音频、独立逻辑轨、USB-C输入/CC/充电、保险/反接/急停/watchdog/过压消能、测试点与机械安装孔。原理图符号每个pad核对数据手册，载板封装含FPC接触面、插头高度、天线净空与连接器出线。PCB先按四层候选评估实际回流/热需求，再有依据地决定是否改两层。

原生工程存在并完成接线/布局布线后，应实际运行并保留完整输出（以下为未来命令，**尚未执行**）：

```sh
KICAD=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$KICAD" sch erc --format json --severity-all --exit-code-violations -o hardware/v1/reports/erc.json hardware/v1/kicad/MORI_V1.kicad_sch
"$KICAD" pcb drc --format json --severity-all --schematic-parity --exit-code-violations --refill-zones -o hardware/v1/reports/drc.json hardware/v1/kicad/MORI_V1.kicad_pcb
```

未运行的ERC/DRC结果为null，不是0。未来的每个警告/错误逐项解释，不能增加忽略来清零；零未连线和原理图一致性也必须检查。只有图纸、封装、电源与接口都可复核、DRC状态清楚后，才导出标记 **PROTOTYPE / NOT BENCH VALIDATED** 的制造文件。采购与PCB下单均不在本任务默认授权内。
