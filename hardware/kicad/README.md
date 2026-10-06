# MORI 原生 KiCad 工程

实际工具 **KiCad10.0.6**。入口 `MORI_carrier.kicad_pro`，同名.kicad_sch/.kicad_pcb；工程本地符号库、所需封装子集、库表、connectivity.json和carrier_bom.csv齐备。接口符号用真实针号和功能电气类型表示远端模块；自定义矩形不是芯片厂商符号外形，但网络与封装焊盘是真实原生对象。模块内部电路由原厂模块实现，见wiring.csv，不把载板当成完全集成设计。

76个载板封装（包含4安装孔及11测试点），模块连接口、看门狗、AND门、编码器电平转换、母线吸能/采样/USB隔离具体到引脚。原理图本地网名经KiCad原生导出，生成PCB时按导出的针脚网络赋值并逐针交叉核验。空置IC输出NC，未用输入固定电平；两个电源标志只说明SS34/急停NC外部供电路径，不能作为真正电源器件。

板框对应98×94平台内部，外接尺寸96×92、截角、孔中心Blender(±40,±42)，NPTH3.4。PCB(x,y)=(BlenderX+100, BlenderY+100)，PCB高度候选117；上视/下视和世界坐标不要混淆。舵机槽x[-38,-6]/y[-12,12]，线孔(14,±7)Ø10。元件已作粗布局，但没有按电流回路/噪声/天线/热细化，也未证明三维安装。

**UNROUTED / NOT FOR FABRICATION**：无走线、无铜区、无Gerber或钻孔生产文件。DRC必须报告未连接；不得通过忽略未连接规则把状态改成PASS。A0原理图适合在KiCad放大查看，另有SVG预览；电源与功能概览见architecture.md。

```sh
cd /Users/dean/Documents/MORI
python3 hardware/tools/create_design.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/tools/generate_kicad.py
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc hardware/kicad/MORI_carrier.kicad_sch --format json -o hardware/reports/erc.json
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc hardware/kicad/MORI_carrier.kicad_pcb --format json --schematic-parity -o hardware/reports/drc.json
```

CLI在本机可能输出Fontconfig/wx无GUI警告；是否成功按退出码、能重新加载的原生文件与报告判断，保留原始日志。ERC通过仅表示当前功能引脚规则；不检查外部线束实际电平/方向、封装真实样品、热、锂电安全和闭环稳定。

下一版布局：VM电容/吸能开关靠近DRV VMM；驱动与降压模块高di/dt环小；ADC RC贴近ADC连接端并远离H桥/天线；U1/U2/U5去耦贴电源脚；两电机电流回流不经IMU返回；地连续；ESP天线按厂家规范禁铜/禁金属并露出板边；模块引线短且成对，所有针1和极性在丝印可辨。放行前用实际模块3D模型核验高度/插拔和±65°头扫掠。
