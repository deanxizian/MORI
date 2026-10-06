# P4 器件下方走线复核

**更正：本页旧分类不能证明符合用户布线要求，当前验收为 FAIL。** “对面铜层投影”和“接插件自身网络”均不能自动豁免。下述统计仅表示旧筛查范围，未检查完整路径的向外引出、抖动、最短拓扑和器件旋转方案；不能据此作放行结论。见 [用户复核](../user_review_20260923/README.md)。

这是独立于 ERC/DRC 的审查。`reviewed_routes.csv` 为每一条命中的线段记录板名、位号、网络、铜层、UUID、长度和处理理由；`review.json` 记录当前 PCB 哈希。原始矩形筛查文件也保留，未删除不利结果。

运动板、后接口板没有同面贴片器件实体内的线段候选。IMU 的 U1 有14条约0.096mm的封装边缘逃线，涉及 MISO_IC、3V3、GND、DRDY、CS_N、SCK、MOSI；它们从 LGA 焊盘向最近边界出线。

电源板的10条矩形筛查候选中，9条位于圆柱电解的矩形包围框角部，按实际 Fab 圆形复核不进入圆柱投影。另一条为 C10/W_VM：从正引脚(48,20)直向左出到(45.5,20)，焊盘外、圆柱内约1.5mm，保留短而宽的电容供电支路。

通孔连接器的塑料壳包围引脚，仍有具名的壳内引出线段：运动51、IMU16、电源74、后接口12条筛查记录。这些是线段/外形配对数量，不是插座数量。它们只使用对应插座自身的网络和已定义的最近两侧逃线通道；不是允许任意其他信号穿过插座。更长的接插件壳内路线同样保留在表内，供逐项查看，未用一个“GND例外”隐藏。

运动 U100 为架空 WeAct 插接模块，其投影下包含载板电路。这部分单独记录，实际模块底部、排母和焊点高度仍需机械核对。对面铜层的投影重合也单独记录，不能将上述数量理解为“所有层均无器件投影下铜线”。

四板 DRC 忽略列表为空；运动内层没有信号走线。后板两个顶面承托区的二维器件/露铜/过孔检查为 PASS，完整外壳安装仍为 BLOCKED。源规则 R14 要求的每处45°转角0.499999mm退让没有全部落实，记录为 FAIL；扇出/测试点工艺、钢网及完整三维装配也不能用零DRC代替。**不宣称47条源规则或用户视觉验收全部通过。**

复核命令（在项目根目录）：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/audit_body_routes_P4.py motion imu power rear
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/review_body_exceptions_P4.py
```
