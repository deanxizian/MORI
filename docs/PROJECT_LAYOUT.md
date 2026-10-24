# 项目目录规则

当前只有一套成品入口。版本由 `config/project_baseline.json` 和根 README 说明，不再平行保留 V1、V1.2 两套项目首页。

```text
MORI/
├── README.md                 项目首页、带壳整机图、当前入口
├── AGENTS.md                 工作约束与已确认设计决定
├── config/                   项目版本、唯一机械尺寸源
├── contracts/                电气、机械、软件接口契约
├── mechanical/               当前总装、STL、图册、生成器
│   ├── input_assets/         重建输入；pcb_reference 不是当前电路
│   ├── reports/              当前检查记录
│   ├── studies/              有引用价值的独立研究，明确未采用项
│   └── procurement/          成品采购与实测记录
├── hardware/driver/          唯一当前自制 PCB 快照、BOM、线束表
├── firmware/                 成品运动/交互固件
├── apps/                     网页控制台与暂停的移动端
├── backend/                  本地服务与模拟连接
├── simulation/               离线模拟
├── software/                 软件入口、回归测试与调试工具
├── test_rig/                 独立树莓派验证车
├── docs/                     状态、需求、更新记录及关键证据
├── tools/                    获取依赖、构建、资料检查
└── refs/                     按锁文件获取的第三方依赖
```

- 已采用模型始终看 `mechanical/mori_v1_2.blend`；文件名的 v1_2 是原构建命名，实际修订号为 M1.58。独立研究不能覆盖这个入口。
- PCB 只看 `hardware/driver/`。旧多板原生资料移到 `mechanical/input_assets/pcb_reference/`，是保存模型的构建依赖，不参与当前采购或布线。
- 规格原文保留，冲突条目由 `docs/REQUIREMENTS.md` 的后续用户决定解释；不要按目录名称推断硬件选型。
- 新进度修改 `CURRENT_STATUS.md` 和对应域入口；已冻结的原始检查不改数字、不升级 PASS。历史执行证据保留日期与来源路径。
- 研究只发布必要摘要、图和检查。可再生成的缓存、过渡模型、全部调参原始日志不加入 Git。
- 本机尚在使用的原始样机试验放在 `test_rig/local/`；原 `hardware/bringup`、`hardware/test_rig`、`mechanical/test_rig` 仅留被 Git 忽略的兼容链接，避免打断其他对话。`.local/` 保存待分类本机资料，均非发布内容。
- Git 工作区是实际工程副本，不是聊天缓存。本次常用 Documents/MORI 已更新；另两个活跃工作区的未提交设计和实验记录未改写。
