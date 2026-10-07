# 当前原生 KiCad 工程

四套完整工程按原生文件打包，来源为固定提交 `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1`。运动／后接口 P5R7、电源 P5R6、IMU P5R4；没有改变尺寸、走线、符号或封装，也不代表制造放行。

| 工程 | 完整文件包 |
|---|---|
| 运动载板 P5R7 | [MORI_motion_P5R7.zip](MORI_motion_P5R7.zip) |
| 电源板 P5R6 | [MORI_power_P5R6.zip](MORI_power_P5R6.zip) |
| IMU 板 P5R4 | [MORI_imu_P5R4.zip](MORI_imu_P5R4.zip) |
| 后接口板 P5R7 | [MORI_rear_P5R7.zip](MORI_rear_P5R7.zip) |

原理图、设计规则、项目配置、接线表和说明仍在 `../kicad/` 以原生文本提供。PCB 与封装的完整序列化内容位于上述 ZIP；它们的行数超过 GitHub diff 上限，Git 属性不能阻止该接口展开这些文本。ZIP 使用普通 Git，不使用 LFS。每个包包含该工程的全部本地文件和配套库，供解压后直接在 KiCad 中检查。

在仓库根目录执行以下命令，`-n` 保留已有文件：

```sh
unzip -n hardware/v1_2/native_projects/MORI_motion_P5R7.zip -d .
unzip -n hardware/v1_2/native_projects/MORI_power_P5R6.zip -d .
unzip -n hardware/v1_2/native_projects/MORI_imu_P5R4.zip -d .
unzip -n hardware/v1_2/native_projects/MORI_rear_P5R7.zip -d .
```

然后从 `hardware/v1_2/kicad/MORI_*/` 打开对应 `.kicad_pro`。ZIP 内已带完整的仓库相对路径；无需重新缩放或移动 PCB。若本地已有修改，先保留并自行比较，不要覆盖。

[manifest.json](manifest.json) 记录每个 ZIP 及全部 242 个原始文件的 SHA256。2026-10-07 仅更新 connectivity/layout_notes/rule_mapping 的元数据；PCB、原理图、规则和配套库字节与原始归档一致。位置从包内实际 PCB 重新提取；这不是重新布线或制造验证。完整历史、旧方案和硬件验证记录仍在原始归档，不因本次打包获得重新验证。
