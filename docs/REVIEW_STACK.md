# PR 审阅顺序

这些 PR 依次叠加，每份 base 是上一层分支。按顺序审阅与合并；**本次不执行合并**。上一层合并后再将下一份 PR 的 base 改为 main，避免重新引入整包 diff。

| 顺序 | 范围 | 分支 | base |
|---|---|---|---|
| 1 | 项目规则、许可与归档属性 | [review/01-foundation](https://github.com/deanxizian/MORI/tree/review/01-foundation) | main |
| 2 | 网页、后端、协议与仿真源码 | [review/02-software](https://github.com/deanxizian/MORI/tree/review/02-software) | review/01-foundation |
| 3 | 固件与软件验证工具 | [review/03-firmware](https://github.com/deanxizian/MORI/tree/review/03-firmware) | review/02-software |
| 4 | 硬件选型、电气契约与接线 | [review/04-hardware-contracts](https://github.com/deanxizian/MORI/tree/review/04-hardware-contracts) | review/03-firmware |
| 5 | 四块当前原生 KiCad 项目 | [review/05-native-pcbs](https://github.com/deanxizian/MORI/tree/review/05-native-pcbs) | review/04-hardware-contracts |
| 6 | 机械参数与正式交接 | [review/06-mechanical-parameters](https://github.com/deanxizian/MORI/tree/review/06-mechanical-parameters) | review/05-native-pcbs |
| 7 | 当前机械构建流程 | [review/07-mechanical-builders](https://github.com/deanxizian/MORI/tree/review/07-mechanical-builders) | review/06-mechanical-parameters |
| 8 | 机械检查及展示工具 | [review/08-mechanical-tools](https://github.com/deanxizian/MORI/tree/review/08-mechanical-tools) | review/07-mechanical-builders |
| 9 | 当前模型、STL 与装配视频 | [review/09-current-models](https://github.com/deanxizian/MORI/tree/review/09-current-models) | review/08-mechanical-tools |
| 10 | 资料导航、恢复工具与校验记录 | [review/10-navigation](https://github.com/deanxizian/MORI/tree/review/10-navigation) | review/09-current-models |

完整当前资料树位于最后一层 `review/10-navigation`。原 PR #1 由这组拆分取代；其提交和原始归档分支保留，供历史资料定位。

[归档与下载](GITHUB_ARCHIVE.md) · [项目索引](PROJECT_INDEX.md)
