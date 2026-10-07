# 当前资料与独立归档

原 PR #1 包含 45,604 个文件和约 8,340 万行新增内容，GitHub 完整 diff 接口返回 406 / too_large。现在用 10 份叠加 PR 提供当前源码、契约、原生 PCB 与模型；每份只比较相邻层，全部保持未合并。

## 当前资料

安装 Git LFS 后克隆最后一层，可得到完整的当前资料树：

```sh
git clone --single-branch --branch review/10-navigation https://github.com/deanxizian/MORI.git
cd MORI
git lfs install --local
git lfs pull
git lfs fsck
python3 -m http.server 8000 --bind 127.0.0.1
```

本地图册为 `http://127.0.0.1:8000/mechanical/index.html`，视频入口为 `/mechanical/animation/index.html`。三个 Blender 工程使用 LFS，STL、视频、原生 PCB 和源码使用普通 Git。GitHub 的源码 ZIP 可能只有模型的 LFS 指针；请使用上述克隆方式。

KiCad 的 PCB、原理图、符号和封装文件按整体图形工程审阅，Git 属性关闭行式 diff，不改变原始字节；DRU、契约、接线和说明仍显示文本差异。请用 KiCad 查看原生几何和连线。文本网格缓存不会作为数百万行源码混入审查。

## 数据与旧工具

完整当前建模流程仍会读取厂家源模型、生成网格和部分旧工具。它们留在原始快照，通过明确命令按需恢复：

```sh
python3 tools/restore_archive_assets.py --list
python3 tools/restore_archive_assets.py --group mechanical-data --group legacy-helpers
```

工具仅从固定提交 `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1` 读取清单中的文件，逐个验证大小及 SHA256；遇到已有但不同的文件就停止，不覆盖本地工作。未纳入清单的历史比较脚本或研究数据需要从下面的完整归档获取。恢复资料不等于重建已验证；本轮没有运行建模或固件构建。

- [数据恢复清单](archive_assets.json)
- [当前模型与原生 PCB 哈希](current_assets.json)
- [原始归档树](https://github.com/deanxizian/MORI/tree/48fe22aa75554c9d7bb237e2d2dcacca7f83dde1/)
- [归档分支](https://github.com/deanxizian/MORI/tree/docs/project-archive-2026-10-06)

原归档提交继续保留，源文件没有删除，也没有改写 Git 历史。它包含当时已上传的历史、报告、研究脚本和来源资料；约 37 GB 的本地大型历史资产原本就未整体上传，仍留在原工作目录。独立归档不是承诺完整备份本机。

新导航中的缺省证据链接指向不可变归档。收到的源代码和原生 PCB 文档保持原字节，因此部分内部历史链接／绝对路径仍需到归档树查看。基线版本与未完成问题见 [当前状态](CURRENT_STATUS.md)。
