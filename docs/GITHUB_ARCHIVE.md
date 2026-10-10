# 当前资料与独立归档

原 PR #1 包含 45,604 个文件和约 8,340 万行新增内容，GitHub 完整 diff 接口返回 406 / too_large。现在用 10 份叠加 PR 提供当前源码、契约、原生 PCB 与模型；每份只比较相邻层，修复记录见 [REVIEW_CLOSURE](REVIEW_CLOSURE.md)；合并后以 main 为完整当前树。

## 当前资料

安装 Git LFS 后克隆 main，可得到合并后的完整当前资料树：

```sh
git clone --single-branch --branch main https://github.com/deanxizian/MORI.git
cd MORI
git lfs install --local
git lfs pull
git lfs fsck
python3 -m http.server 8000 --bind 127.0.0.1
```

本地图册为 `http://127.0.0.1:8000/mechanical/index.html`，视频入口为 `/mechanical/animation/index.html`。三个 Blender 工程使用 LFS，STL、视频、原生 PCB 工程包和源码使用普通 Git。GitHub 的源码 ZIP 可能只有模型的 LFS 指针；请使用上述克隆方式。

GitHub 完整 diff 对本批原生 CAD 没有采用本地 Git 的 binary 属性；原 PCB/封装组因此仍触发 20,000 行限制。现在四套完整 KiCad 工程存为普通 Git ZIP，PCB、原理图及封装库原字节保持；本轮仅修正 JSON 元数据，并保留原理图、设计规则、项目配置等可读文本。使用前按 [原生工程说明](../hardware/v1_2/native_projects/README.md)解压，再用 KiCad 审阅几何和连线。没有为这些小型 CAD 增加 LFS，文本网格缓存也未混入源码审查。

## 数据与旧工具

完整当前建模流程仍会读取厂家源模型、生成网格和部分旧工具。大部分留在原始快照；原快照未上传的两个厂家网格包含在小型输入 ZIP 中，通过明确命令按需恢复：

```sh
python3 tools/restore_archive_assets.py --list
python3 tools/restore_archive_assets.py --group mechanical-data --group legacy-helpers --group mechanical-build-inputs --group native-pcbs
```

外部恢复项仅从固定提交 `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1` 读取清单中的文件，逐个验证大小及 SHA256；遇到已有但不同的文件就停止，不覆盖本地工作。未纳入清单的历史比较脚本或研究数据需要从下面的完整归档获取。恢复资料不等于重建已验证；本轮已实际重建当前主模型、导出 STL 和交叉编译 F412RE；额外历史比较仍可能缺少未公开的大型历史资产，不能据此宣称全部历史流程已可复现。

- [数据恢复清单](archive_assets.json)
- [当前模型与原生 PCB 哈希](current_assets.json)
- [原始归档树](https://github.com/deanxizian/MORI/tree/48fe22aa75554c9d7bb237e2d2dcacca7f83dde1/)
- [原归档 PR #1（已关闭）](https://github.com/deanxizian/MORI/pull/1)

2026-10-07 按用户要求删除原归档分支，当时 GitHub 仅保留 `main` 分支。原始提交仍由已关闭的 PR #1 引用，历史链接和恢复脚本继续使用上述固定提交；删除的是分支引用，没有删除本地资料或改写 Git 历史。原始提交包含当时已上传的历史、报告、研究脚本和来源资料；约 37 GB 的本地大型历史资产原本就未整体上传，仍留在原工作目录。独立归档不是承诺完整备份本机。

新导航中的缺省证据链接指向不可变归档。原始资料快照保持；当前源码已包含审查修复。部分历史链接／绝对路径仍需到归档树查看。基线版本与未完成问题见 [当前状态](CURRENT_STATUS.md)。

## M1.54 后续模型更新

本节保留 2026-10-08 的阶段说明；当前为下节的 M1.55。

2026-10-08 本次 PR 同步 M1.53 C6 与 M1.54 CAM USB 朝右，详见 [模型更新](M1_54_MODEL_UPDATE.md)。新的 26 个批准基线／工具输入保存在约 0.65 MiB 的普通 Git ZIP 中，由同一 `mechanical-build-inputs` 恢复组按哈希解包；原始归档提交和四套硬件工程包不变。当前状态与模型哈希见 [CURRENT_STATUS](CURRENT_STATUS.md) 和 [current_assets.json](current_assets.json)。本地未采用线束研究没有混入当前模型，也未承诺完整上传。

## M1.55 资料更新

2026-10-10 更新同一份 [PR #13](https://github.com/deanxizian/MORI/pull/13)，尚未合并到 main。审阅最新模型时使用 `codex/mechanical-m1-54-model-sync` 分支；合并后才由 main 提供这一版。

三份 Blender 工程继续用 Git LFS。新增批准输入、几何执行证据和未采用线束记录分别为普通 Git ZIP，约 1.33、14.29 和 36.79 MiB，无需新增 LFS 规则。成员哈希和未包含的本地研究资产见 [包清单](review_evidence/M1_55_archives.json)。

```sh
python3 tools/restore_m1_55_evidence.py --list
python3 tools/restore_m1_55_evidence.py --group approval
```

工具也可按需恢复 `validation` 或 `harness-records`，遇到已有不同文件会停止。原始执行证据保持日期和路径，研究记录包没有包含二进制缓存、比较 Blender、全部图片或第三方源载荷，不能当作可独立重跑全部研究的完整备份。545 个本地硬件来源保护项尚未公开，本次机械 PR 不代为发布它们；完整保护重放的限制见 [M1.55 更新](M1_55_MODEL_UPDATE.md)。
