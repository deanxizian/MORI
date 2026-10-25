# PR 审阅顺序

这些 PR 依次叠加，每份 base 是上一层分支。按顺序审阅与合并；本轮按用户授权在复核后合并并清理分支。后续合并时需维护依赖关系：普通 merge 后可将下一份 base 改为 main；如使用 squash/rebase，先重放下游分支，避免重复差异。

| 顺序 | 范围 | PR | base |
|---|---|---|---|
| 1 | 项目规则、许可与归档属性 | [#2](https://github.com/deanxizian/MORI/pull/2) | main |
| 2 | 网页、后端、协议与仿真源码 | [#3](https://github.com/deanxizian/MORI/pull/3) | review/01-foundation |
| 3 | 固件与软件验证工具 | [#4](https://github.com/deanxizian/MORI/pull/4) | review/02-software |
| 4 | 硬件选型、电气契约与接线 | [#5](https://github.com/deanxizian/MORI/pull/5) | review/03-firmware |
| 5 | 四块当前原生 KiCad 项目 | [#6](https://github.com/deanxizian/MORI/pull/6) | review/04-hardware-contracts |
| 6 | 机械参数与正式交接 | [#7](https://github.com/deanxizian/MORI/pull/7) | review/05-native-pcbs |
| 7 | 当前机械构建流程 | [#8](https://github.com/deanxizian/MORI/pull/8) | review/06-mechanical-parameters |
| 8 | 机械检查及展示工具 | [#9](https://github.com/deanxizian/MORI/pull/9) | review/07-mechanical-builders |
| 9 | 当前模型、STL 与装配视频 | [#10](https://github.com/deanxizian/MORI/pull/10) | review/08-mechanical-tools |
| 10 | 资料导航、恢复工具与校验记录 | [#11](https://github.com/deanxizian/MORI/pull/11) | review/09-current-models |
| 11 | 审查修复及组合树复核 | [#12](https://github.com/deanxizian/MORI/pull/12) | review/10-navigation |

修复前的完整资料树位于第 10 层；审查修复在第 11 层中汇总。这些 PR 均已合并，以 `main` 为准，临时审查分支已删除。原 PR #1 由这组拆分取代并关闭；2026-10-07 按用户要求删除剩余的原始归档分支，当时 GitHub 仅保留 `main`。历史资料继续通过 PR #1 引用的固定提交定位，见下方归档说明。

[归档与下载](GITHUB_ARCHIVE.md) · [项目索引](PROJECT_INDEX.md)
