# MORI 左右转头舵机移入头部：实际模型位置预研

状态：**仅试摆，完整装配仍 BLOCKED**。本研究未修改已交付的 M1.8 模型和共享几何参数。原尺寸 SCS0009 本体及输出端以刚体变换倒装，未缩放采购件。

## 当前结论

头内下层有可容纳舵机的候选位置：输出末端离地 192mm，相对头中心 -30mm；绕竖轴朝向 90°。舵机本体和输出端总体包络为 X±6.05、Y−10.55～21.95、Z192～220.45mm。它属于只左右旋转的 yaw 支架，不跟着屏幕进行俯仰。

采用机身旋转的布置：舵盘/输出端通过尚待设计的抗扭连接固定到身体，舵机外壳与 yaw 转台连接。头部载荷仍应由独立 yaw 轴承及双侧 pitch 轴承承受。控制方向和零位需重新标定，不能沿用旧舵机正负号。

试摆20组位置与朝向后，对选中位置做 130 个联合姿态采样：yaw −60～60°、步长10°；pitch −20～25°、步长5°。实际三角实体检查中，舵机本体/输出端与现有采购件、壳体和支架重叠 0 项，与既有线束预留体重叠 0 项。最近的现有非替换零件间隙约 4.3mm，见 placement_study.json。原模型LCD的两个连接器仍采用保守代理，不构成完整精确装配通过；有限采样不是连续运动证明。

## 腹部空间和重量

原舵机本体加安装耳的外接包络约32.5×12.1×25.25mm可移出腹部，输出端也随布局移动。但是腹部承重座、固定反力连接和走线仍然占空间，**不能把这个外接框直接称为新增可用PCB空间**。S3电源板外形、装件高度和孔位尚未确定，因此本报告没有声称完整电源板可以装入。

本体与输出端共约 13.3g 的既有假设质量移高；其他零件不变时，整机重心估算上升约 0.7mm。新安装件质量、未来PCB下移均未计入。该估算不是实測重心或平衡资格。

## 尚未完成

- 舵机安装耳固定、轴向锁紧及螺丝刀路径。
- 身体固定反力连接、承重座简化及实际释放的PCB区域。
- 新线束服务环、端口拔插和弯曲疲劳。
- 完整电源板布局、头部转动惯量、打印强度与实机平衡。

预览中青色为移入头内的舵机。LCD被隐藏以便观察，碰撞检查仍包含LCD；旧电源占位在本预览隐藏，不代表电源设计已完成。试摆 .blend 中现有支架只是参照，缺失固定连接，不能按该文件打印或装配。

## 复现

在 MORI 项目根目录，依次执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/study_head_yaw.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/render_head_yaw_study.py
```

工具使用项目既有 Blender5.2.1 LTS 与 Manifold。源模型SHA256：`7164bc59cd2f0b656374820bf161718398719e84f87cff1d49fde9ca97fd66c0`。运行日志见 mechanical/studies_yaw_head.log、render.log；预览图和试摆文件哈希见 preview_provenance.json。
