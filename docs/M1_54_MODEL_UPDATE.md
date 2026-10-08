# M1.54 模型同步

把用户已确认的两项改动同步到 Blender 主模型、电子细模、STL、图册和装配动画。相对 GitHub 原 M1.52 基线，固定偏航桥现有左侧槽口外缘加宽 0.8 mm；CAM 整板和板载双麦转动 −90°，USB 朝机器人右侧 +X。没有新增打印件、螺钉或线束。

- [C6 实际剖面对比](../mechanical/studies/c6_adoption/index.html)
- [CAM 转向前后对比及安装路径](../mechanical/studies/cam_right_adoption/index.html)
- [当前模型图册](../mechanical/index.html) · [主模型](../mechanical/mori_v1_2.blend) · [装配视频](../mechanical/animation/index.html)
- [当前检查报告](../mechanical/current_report.html) · [未完成事项](CURRENT_STATUS.md)

## 重建与证据

主流程使用实际 Blender 命令完成构建、结构元数据、几何检查、62 视图渲染、21 个 STL 导出、金属件设计参考导出、交付一致性及报告生成。具体命令、时间、输入／输出哈希和日志位于 [流水线执行包](../mechanical/reports/pipeline_execution.zip)。衍生模型和动画独立回读，当前发布结果另记于 [交付复核](review_evidence/M1_54_publication.json)。

新增的批准前基线、精确网格和原工具扫掠共 26 个文件，按原字节压缩到普通 Git 文件 `mechanical/input_assets/m1_54_approval_inputs.zip`（约 0.65 MiB）。[恢复清单](archive_assets.json)记录每个成员的大小、SHA256 和包哈希。先按[归档说明](GITHUB_ARCHIVE.md)恢复源模型，再运行：

```sh
python3 tools/restore_archive_assets.py --group mechanical-build-inputs --group native-pcbs
MORI_CAD_PYTHON=/path/to/cad-python python3 mechanical/scripts/run_all.py --core
```

完整当前流程还依赖归档说明中的厂家数据及 legacy helpers。解包会拒绝覆盖已有的不同文件。三份 Blender 工程继续使用 Git LFS，视频、STL 和本次小型基线包使用普通 Git。

历史保护清单曾误收录一个 `__pycache__/*.pyc` 文件。本次保留原清单，只在源文件保护检查中明确排除该机器生成缓存；302 个实际硬件源文件仍逐个校验，任何源文件不匹配均失败。两份批准前配置现在也验证记录中的原始 SHA256。

另修正动画回读：读取原生碰撞体前先恢复验证集合并刷新装配变换。独立诊断确认原流程会留下 4 个屏幕／螺钉碰撞体的旧矩阵；修正只影响检查流程，不改变模型、动画轨迹或打印件。

## 范围与限制

现有 201 个原生零件、130 个组合头部姿态、拓扑、光学及核心路径按当前输入复核。CAM 的原四孔轴集合和固定件保持；三种 USB 本体只是有尺寸边界的空间预留，不是完整采购件或插合实测。C6 改动以独立批准网格复核，原始比较记录仍注明 M1.53 日期。

装配动画仍为 22 步、85.75 秒、1280×720、24 fps；CAM 阶段沿已检查的折线路径运动。视频用于装配说明，不证明连续扫掠、人手操作、完整线束或制造可行性。

用户已决定 SC-0090-C001 配件及微雪排线资料待到货后核对；两份询问稿保留且未发送。完整线束、上部反力夹初装、正式 USB 源端、电源替代候选及实物验证均未由本次局部改动放行。硬件源和 `contracts/components.json` 保持不变。
