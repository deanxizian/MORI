# 2026-10-07 代码审查修复记录

复核范围为拆分 PR #2–#11 的 52 条意见及最终组合树。原始资料快照保留；本轮修复源码、资料可复现性和已确认的网格碎片。**这是原型资料归档的代码审查，整机仍未制造放行。**

## 实际验证

- 网页 13 项测试、Vue 类型检查和生产构建通过。真实 Chromium 验证凭据刷新、序号恢复、同模式授权切换、describe POST、撤销后重新配对；无浏览器错误。
- 后端/仿真 57 项、旧软件 24 项、证据与恢复工具 15 项测试通过；V1/V1.2 C 核心通过 ASan/UBSan。
- F412RE 使用 Arm GNU 14.2.Rel1 实际交叉编译。开启物理平衡门的负向构建被拒绝；没有烧录或上电。
- 最新 R5 机械交付包包含 853 个文件，独立解压后逐文件哈希、完整执行证据及篡改生成脚本的拒绝检查通过。当前主模型八阶段 core 重建通过，62 个渲染视图均为 1200 px / 32 samples；此前 R4 包的独立完整重建及再次打包亦已通过，详见下方带日期的记录。
- 四个工程包只更新 JSON 元数据；所有 PCB、原理图、封装库及其余成员字节保持。
- Blender 5.2.2 LTS / manifold3d 3.5.3 重建完成；当前 130 个联合姿态等核心检查：25 PASS、0 FAIL、9 NOT_TESTED、10 BLOCKED。21 个 STL 均为单一连通实体。历史扩展检查未冒充本轮重跑。
- 局部修复范围按 201 个零件的世界坐标面片核对。头前壳只移除四个 <0.001 mm³ 游离碎片；Display_Frame 仅约 0.000002 mm 浮点变化，Display_PCB 对称差体积约 0.00000469 mm³。未改尺寸或硬件位置。

命令、版本、输出摘要和证据哈希见 [review_evidence](review_evidence/manifest.json)；原始源与复核关系见 [模型基线](../mechanical/input_assets/M1_52_review_baseline.json)。本轮视频未重渲染，保留的 M1.52-A1 是有日期的原始演示。

## 逐项处理

| 序号 | PR | 处理 |
|---|---|---|
| 1 | [#2](https://github.com/deanxizian/MORI/pull/2) | 补 REFERENCES.md；原 S01–S08 的对应关系明确标为 NOT_SUPPLIED，不猜造原作者来源。 |
| 2 | [#2](https://github.com/deanxizian/MORI/pull/2) | 后续固件层已有 THIRD_PARTY_V1_2.md；合并完整依赖树后链接可解析。 |
| 3 | [#2](https://github.com/deanxizian/MORI/pull/2) | 只忽略根目录 reports/v1、reports/v1_2，不再屏蔽 hardware 内的必要报告。 |
| 4 | [#3](https://github.com/deanxizian/MORI/pull/3) | 两个无载荷动作显式 POST {}；浏览器确认 describe 与 revoke 返回 200。 |
| 5 | [#3](https://github.com/deanxizian/MORI/pull/3) | 上传授权变化立即提交 CAMERA_MODE；以命令确认及服务端状态更新界面。 |
| 6 | [#3](https://github.com/deanxizian/MORI/pull/3) | 退出跟随同时清除头部目标和速度。 |
| 7 | [#3](https://github.com/deanxizian/MORI/pull/3) | C 测试夹具由紧随的固件层提供；完整树测试通过，不把中间层当独立产品。 |
| 8 | [#3](https://github.com/deanxizian/MORI/pull/3) | 按含路径的规范化完整网关地址保存凭据；刷新仅恢复认证，不自动占用控制权或 ARM。另修复重连序号回退。 |
| 9 | [#3](https://github.com/deanxizian/MORI/pull/3) | 会话变化、断线、重连立即拒绝并清除 pending commands。 |
| 10 | [#3](https://github.com/deanxizian/MORI/pull/3) | WAV 校验、预算拒绝与服务商错误分别处理；服务商异常不伪装为输入格式错误。 |
| 11 | [#3](https://github.com/deanxizian/MORI/pull/3) | 生成 JSON Schema 为各命令声明所需权限；99 个组合与运行时校验一致。 |
| 12 | [#3](https://github.com/deanxizian/MORI/pull/3) | 先 fsync 删除日志，再提交 SQLite；启动重放日志，崩溃后删除不丢失。 |
| 13 | [#3](https://github.com/deanxizian/MORI/pull/3) | 配对限速改成有界的每来源固定时间窗；错误尝试不能永久封死所有客户端。 |
| 14 | [#3](https://github.com/deanxizian/MORI/pull/3) | 零延迟立即生效；其他延迟按采样时刻插值。 |
| 15 | [#3](https://github.com/deanxizian/MORI/pull/3) | 未知回放场景直接报错。 |
| 16 | [#3](https://github.com/deanxizian/MORI/pull/3) | 心跳被拒绝或过期立即撤销本地租约并停止发送运动目标。 |
| 17 | [#4](https://github.com/deanxizian/MORI/pull/4) | DISARM、故障和释放冻结头部；HEAD_TARGET 及执行循环都要求已使能且通过相应门。 |
| 18 | [#4](https://github.com/deanxizian/MORI/pull/4) | 缓存全部保留的命令 ID 和结果，A/B/A 重试不再次执行或续租。 |
| 19 | [#4](https://github.com/deanxizian/MORI/pull/4) | 补两个小型基线 ZIP；新增只针对不可变快照的验证入口，44 个归档成员通过。历史完整审计缺资料时明确 BLOCKED。 |
| 20 | [#4](https://github.com/deanxizian/MORI/pull/4) | ARM 重置持续饱和计时与状态。 |
| 21 | [#4](https://github.com/deanxizian/MORI/pull/4) | 记录实际 Git HEAD、dirty 状态；去掉“没有 Git 仓库”的旧结论。 |
| 22 | [#4](https://github.com/deanxizian/MORI/pull/4) | 远端 CI 没有执行证据时标为 NOT_TESTED，不能由本地测试代替。 |
| 23 | [#5](https://github.com/deanxizian/MORI/pull/5) | BOM 对齐 motion/rear P5R7、power P5R6、IMU P5R4 的当前集合。 |
| 24 | [#5](https://github.com/deanxizian/MORI/pull/5) | 测试计划新增当前 P5R7 基线与前置条件；历史步骤保留明确边界。 |
| 25 | [#5](https://github.com/deanxizian/MORI/pull/5) | 合同改为已采用的 6806ZZ，30×42×7 mm。 |
| 26 | [#5](https://github.com/deanxizian/MORI/pull/5) | 合同按用户 SP3040 图纸记载；未标尺寸仍是估算。 |
| 27 | [#5](https://github.com/deanxizian/MORI/pull/5) | FFC 16–18 脚同步已收到 A2 的 NC 定义，实物方向复核仍待完成。 |
| 28 | [#5](https://github.com/deanxizian/MORI/pull/5) | 默认目标改为 STM32F412RE：正确启动文件、宏及 512 KB Flash / 256 KB RAM 链接边界；交叉编译通过，物理使能门保持关闭。 |
| 29 | [#5](https://github.com/deanxizian/MORI/pull/5) | 取消“可按表制作”的含义；每行长度与制造状态明确 NOT_TESTED/BLOCKED。这张表仅是端点定义，供应商裁线图仍未完成。 |
| 30 | [#5](https://github.com/deanxizian/MORI/pull/5) | PH 线壳的错误电容封装字段置空，明确其不是 PCB 焊接封装。 |
| 31 | [#6](https://github.com/deanxizian/MORI/pull/6) | 从四块实际 PCB 重新解析位置、转角、面及封装；重复运行不产生变化。 |
| 32 | [#6](https://github.com/deanxizian/MORI/pull/6) | 元数据中的交接/审阅链接指向固定归档提交，恢复工具也包含所需输入。 |
| 33 | [#6](https://github.com/deanxizian/MORI/pull/6) | 移除 rear 中误复制的 IMU 钢网通过结论；该项标为 NOT_TESTED。 |
| 34 | [#7](https://github.com/deanxizian/MORI/pull/7) | project_baseline 对齐当前 P5R7 接收集和工程包。 |
| 35 | [#7](https://github.com/deanxizian/MORI/pull/7) | 机械接口 MCU 记录对齐 WeAct F412RET6。 |
| 36 | [#7](https://github.com/deanxizian/MORI/pull/7) | 恢复清单包含 E-pin fit A1 交接，哈希对照原始提交。 |
| 37 | [#7](https://github.com/deanxizian/MORI/pull/7) | 扬声器待测项改为用户选择的 SP3040，保留耳厚/孔径等未测尺寸。 |
| 38 | [#7](https://github.com/deanxizian/MORI/pull/7) | 由 TDK 轴向图、原生 U1 转角及 PCB 变换导出名义 sensor→body = diag(1,-1,-1)；实物方向、标定与驱动配置仍未放行。 |
| 39 | [#7](https://github.com/deanxizian/MORI/pull/7) | 机械接口同样对齐 6806ZZ 及既定轴承座方案。 |
| 40 | [#7](https://github.com/deanxizian/MORI/pull/7) | 当前外壳接口删除已取消的电源开关出口；硬件断电/急停实施仍列为 BLOCKED。 |
| 41 | [#7](https://github.com/deanxizian/MORI/pull/7) | 检查结果遵守 PASS/FAIL/NOT_TESTED/BLOCKED/NOT_APPLICABLE；资料来源类别独立记载。 |
| 42 | [#8](https://github.com/deanxizian/MORI/pull/8) | 补固定哈希的公开 CAD/PDF/网格恢复清单和本地网格 ZIP；实际从恢复资料重建主模型成功。 |
| 43 | [#8](https://github.com/deanxizian/MORI/pull/8) | 视频先写唯一临时文件；成功后原子替换，并写 rendered_video、文件大小及 SHA256；失败不会拿旧 MP4 冒充本次输出。 |
| 44 | [#8](https://github.com/deanxizian/MORI/pull/8) | 构建清单读取实际 manifold3d 安装版本，本次为 3.5.3。 |
| 45 | [#9](https://github.com/deanxizian/MORI/pull/9) | M1.44 以后路由到当前报告生成器；缺失、过期或不匹配模型的证据会失败，不覆盖历史图册。 |
| 46 | [#9](https://github.com/deanxizian/MORI/pull/9) | 打包输入从构建清单与恢复清单推导，逐一校验，不再依赖 M1.10 固定白名单。 |
| 47 | [#9](https://github.com/deanxizian/MORI/pull/9) | 继续执行前核对全部源输入及前序产物哈希；过期、缺失或失败记录均拒绝。 |
| 48 | [#9](https://github.com/deanxizian/MORI/pull/9) | 验证实际 PNG 大小、SHA256、几何哈希及完整视图集合；仅有清单不算通过。 |
| 49 | [#9](https://github.com/deanxizian/MORI/pull/9) | 失败重试须有更晚成功记录、匹配日志和实际产物哈希；不再只改文字就标成功。 |
| 50 | [#9](https://github.com/deanxizian/MORI/pull/9) | CAD 解释器由 MORI_CAD_PYTHON 或当前 Python 决定，并实际检查导出器直接使用的 OCP 可导入。 |
| 51 | [#10](https://github.com/deanxizian/MORI/pull/10) | 源模型清除四个已定位微小游离体，主壳面片完全保留；STL 导出拒绝 Head_Front 多连通体。 |
| 52 | [#11](https://github.com/deanxizian/MORI/pull/11) | 资产表用 GIT_ZIP_MEMBER 明确原生 PCB 所在 ZIP、成员路径、成员哈希及 ZIP 哈希。 |

## 尚未解决的工程事项

### PR #12 二次审查

`ddfaf9d` 的自动审查完成于 2026-10-07，提出 10 条意见。本次追加处理如下；旧阶段的机械限制继续约束结构设计，当前工作是用户要求的整个仓库审查修复。

- F413/F412：原始 `48fe22aa` 中 `contracts/components.json#/components` 的 `motion_mcu` 已选 WeAct F412RET6；保留匹配这一硬件的构建，并修正仍写 F413 的 `software_profile.json`。没有换板。
- Head_Front：保留单独记录的四个数值碎片清理。它属于本次审查修复，不冒称原 M1.52 两枚螺母改动；主壳的 17,554 个面片逐一保持。没有外形或接口重设计。
- components.json：本次仓库审查按既有 SP3040 和 6806ZZ 选择校正过期说明；原始硬件快照和全部 PCB/原理图/库字节保留。没有宣称新电气设计或制造放行，后续机械设计仍不得擅改硬件源。
- 相机轮询：处理关闭/失联时的 HTTP 失败，丢弃旧帧；真实 Chromium 注入 409/401 各 4 次，没有未处理的 Promise 错误。
- 当前报告：`--core` 同步运行 STEP 导出、交付检查和报告生成；打包核对报告、HTML 及全部相关产物指纹，拒绝旧 PASS。
- 构建输入：仅校验构建清单、明确的当前补充输入和厂家源；不再强制恢复历史报告、A0 参数或旧运行时缓存。
- 原生工程包：先在内存中生成并校验所有新 ZIP，再以临时文件替换。写前保留恢复日志/备份；后续项目或最终清单失败时回滚，中断后重跑先恢复。两个注入故障测试和幂等检查通过。
- 网关凭据：按完整规范化地址（含路径）隔离；旧的仅 origin 凭据不自动迁移，避免发到同域名下另一个机器人。
- 头部禁驱：独立 `torque_enabled` 默认关闭，DISARM/FAULT/释放立即关闭，位置静止不能代表禁驱；STOP_MOTION 保持与故障停机不同。主机测试通过，实体适配器仍未接通。
- 删除重放：跳过数据库已记账的 tombstone，仅实际删除内容时重建索引；正常重启不再重复 VACUUM。

新增网页回归后共 11 项，存储/网关 12 项、归档工具 10 项和 V1 C 核心均通过。首次新 core 流程暴露了 OCP 环境被误要求安装完整 cadquery 的检查错误，已改为检查导出器实际依赖；失败记录保留，不把它计为通过。 后续从 851 文件的 R4 ZIP 独立解压，完整 `run_all.py --core` 八个阶段及再次打包全部通过；本次验证渲染为 128 px / 1 sample，主模型原有的高分辨率图片未替换。当前几何仍为 25 PASS、0 FAIL、9 NOT_TESTED、10 BLOCKED。见 [完整重建结果](review_evidence/round2-core-result.json)。

第 29 项的供应商裁线长度没有被凭空填入；相关表已明确降为端点定义，制造仍 BLOCKED。S01–S08 原编号对应关系也没有原始资料，只能明确未提供。头部舵盘、上部反力夹初装、完整带线闭壳、WeAct E 孔针实物匹配、急停实施、打印强度及实机运行见 [当前状态](CURRENT_STATUS.md)。这些边界继续保留，代码合并不改变它们。

### 追加交付边界检查

对 `2da643c` 的复审提出三条补充意见：报告生成器现在允许无 Git 的独立目录，并避免借用父目录仓库的身份；基线 ZIP 要求完整且唯一的成员集合、全包 CRC 和逐项哈希；机械流水线保存实际命令、输入/脚本指纹、产物指纹和日志到 `pipeline_execution.zip`，打包逐项核验这些执行记录，修改任一脚本后不得沿用旧 PASS。15 项工具回归及原始固件归档 48 项校验通过，完整新流水线八阶段也已通过，执行记录保存在 pipeline_execution.zip。R5 交付包独立解压校验通过；故意修改 validate.py 后被拒绝，恢复原始内容后重新通过。当前几何指纹及全部 21 个 STL 的 SHA256 与前次模型一致，电子细节模型和历史演示无需重复生成。见 [本轮结果](review_evidence/round3-core-result.json) 与 [独立包检查](review_evidence/round3-package-integrity.json)。


### 最后一轮行为与交付检查

`75abb96f` 复审的四项补充已处理：提交八阶段 `pipeline_execution.zip` 与其引用的四个金属轮轴设计文件；两个证据入口统一调用 `project_git`，拒绝继承父仓库身份；同一 CAMERA_MODE 下只更新上传授权，保留目标、观测和 HEAD/BODY 跟随，真正切换模式仍取消旧目标；WebSocket 在初次鉴权、接收命令及后台遥测发现凭据失效时均以 1008 关闭，浏览器清除保存的凭据，普通网络断线继续保留配对。网页 13 项、后端/仿真 57 项、工具 15 项回归通过；新增测试覆盖 HEAD/BODY 双向授权切换、未知与撤销令牌、空闲连接撤销、浏览器重载和正常断线。

从 d7f8379c 干净 Git 检出后，按公开固定来源恢复并核验 529 项输入，通过当前流水线与打包完整性检查，无需为了补缺失执行证据重新构建。普通远端文件完整哈希复核、LFS 对象编号/大小/文件头检查和本地 LFS fsck 均通过。见 [干净检出记录](review_evidence/round4-clean-checkout.json)。

## PR #13：M1.55 交付与恢复复核（2026-10-10）

对 `ac9cae054e` 的六项 P2 意见已落实到代码与交付流程：最终页面生成后再写动画交付哈希；H06 原始数值报告和入壳要求作为独立资料包发布；机械合同同步已完成的 R2 保存后检查；动画脚本与页面生成器按 R2 及匹配证据输出状态，不再恢复旧的裸件装入阻挡提示。实发舵盘、最终锁紧、完整带线装配和强度仍保持未验证。

恢复器在任何写入前检查所有目标和父目录，并拒绝“某个选定文件同时被用作其他文件的目录”。每个 ZIP 只校验和打开一次，成员仍逐项校验并独占发布。新增回归覆盖后置父路径为文件时零写入、包数量恒定的读取次数、并发文件保护、错误哈希的临时文件清理，以及 R2 页面在证据缺失／过期时不得输出通过。25 项工具测试通过。

完整数字交付重新生成；[206 个零件的精确前后对比](review_evidence/M1_55_review_geometry_equivalence.json)无几何、位姿或分类变化。来源保护首次被 Finder 的 `.DS_Store` 变化阻断，修正后仅排除该缓存与 Python 字节码，846 份硬件来源文件继续逐项受保护。初次失败日志与后续实际执行记录均保留在[几何执行包](evidence/M1_55_validation_evidence.zip)。最终哈希、资料恢复及导航核验以[本轮发布记录](review_evidence/M1_55_publication.json)为准；GitHub Review 和合并状态以 [PR #13](https://github.com/deanxizian/MORI/pull/13) 为准。
