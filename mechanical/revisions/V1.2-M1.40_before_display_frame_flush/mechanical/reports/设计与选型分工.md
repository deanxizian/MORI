# 电子模型与来源 · V1.2-M1.40

正式交接：hardware/v1_2/handoff/mechanical_P5R6.json；motion/power/rear为P5R6，IMU为P5R4。硬件原生文件和components.json保持只读。

- motion: `hardware/v1_2/kicad/MORI_motion_P5R6/MORI_motion_P5R6.kicad_pcb`；哈希匹配True，最大导入顶点误差0.00000mm；这只验证导入，不是实物精度。
- imu: `hardware/v1_2/kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pcb`；哈希匹配True，最大导入顶点误差0.00000mm；这只验证导入，不是实物精度。
- power: `hardware/v1_2/kicad/MORI_power_P5R6/MORI_power_P5R6.kicad_pcb`；哈希匹配True，最大导入顶点误差0.00001mm；这只验证导入，不是实物精度。
- rear: `hardware/v1_2/kicad/MORI_rear_P5R6/MORI_rear_P5R6.kicad_pcb`；哈希匹配True，最大导入顶点误差0.00000mm；这只验证导入，不是实物精度。

原厂LCD与WeAct保留原厂CAD1:1；CAM33700按官方37×37mm板框、32.6mm孔网格与官方照片重建，OV3660按对应照片重建。照片估计的孔径、厚度、器件高度不是厂商完整CAD，更不是MEASURED。相机装配位置本轮退入3.8mm，镜头和载板尺寸没有缩放。电池仍为Tenergy31013的71×55×20mm候选包络，未实测出线/BMS/公差。

电源板的两路5V降压已集成在U60/U70，未额外建两块5V模块。当前另两块工程参考是轮驱9V D36V50F9、头部6V D24V22F6，依硬件交接保留；实际电气/热能力及预算未获资格验证。

查看每个器件的evidence、dimension_basis、limitations和source_native_sha256。原厂CAD、原生布局、库模型、厂图重建和照片估算分开标记。没有采购件被标为MEASURED。全体未完成项见[当前装配报告](REPORT.md)。
