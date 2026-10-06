# GitHub 资料归档与下载

本轮按用户要求提交 **PR，暂不合并**。目标是形成可阅读、可定位和可下载的项目资料入口；原工作目录、未采用候选、硬件源和历史证据均保留。

## 上传范围

| 类型 | 处理 |
|---|---|
| 当前规格、契约、源代码、PCB 原生文件、采购与测试文档 | Git 管理，保留版本和原路径 |
| 当前三个 Blender 工程和大型 MCU 网格 JSON | Git LFS，下载后放回原路径 |
| 其余小型 CAD、视频、当前 STL、预览、HTML 图册 | 普通 Git；图册在本地静态服务打开 |
| 历史脚本、参数和较小报告 | 保留，用历史索引区分，不作为当前基线 |
| 历史 Blender 快照、自动备份、重复模型／视频及大批量中间数据 | 留本地，未全部上传；具体排除项由归档清单记录 |
| 安装依赖、工具链、编译目录、系统缓存和运行数据 | 不上传，保留锁文件、安装脚本和已有测试结果 |
| 密钥、真实环境文件、数据库、设备绑定及本机账户配置 | 不上传；示例配置保留 |
| 含会话／访问字段的第三方原始网页缓存 | 留本地，不公开缓存字段；相关资料仍通过原厂链接和来源记录追溯 |

机械历史快照和研究目录合计约 37 GB，大部分是二进制场景、重复渲染和计算数据。**GitHub 仓库不是本机目录的完整备份。** 未上传文件没有被删除；历史 Blender 对比和部分研究复算可能仍需要这些本地资产。

少数上游下载只留下 Git LFS 指针，并非实际 CAD／PDF。它们不作为有效模型上传；路径和指针来源记录在 [遗漏缓存清单](omitted_web_snapshots.json)，原文件仍留本地。

GitHub 普通 Git 对单文件有大小限制，因此当前大模型使用 LFS。[官方大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

## 下载当前资料分支

安装 Git LFS 后执行：

```sh
git clone --branch docs/project-archive-2026-10-06 https://github.com/deanxizian/MORI.git
cd MORI
git lfs install --local
git lfs pull
git lfs fsck
```

PR 合并前 `main` 只有初始化入口。直接下载 GitHub 的源码 ZIP 可能得到 LFS 指针，不能把几行文本的 `.blend` 当作有效模型；优先使用上面的克隆方式。

从项目根目录启动静态资料服务：

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

- 机械图册：`http://127.0.0.1:8000/mechanical/index.html`
- 装配动画：`http://127.0.0.1:8000/mechanical/animation/index.html`
- Blender 主模型：`mechanical/mori_v1_2.blend`

本次新增索引和采购表使用仓库相对链接。历史报告中的本机绝对路径、旧网址和命令作为证据原样保留，换机器时需替换根目录；未把它们批量重写成已经验证的可移植命令。

## 重建边界

机械脚本入口为 `mechanical/scripts/run_all.py`，尺寸源为 `config/geometry.json`；Blender、Manifold 和辅助 CAD Python 依赖需按原记录准备。软件依赖见 `package.json`、`pnpm-lock.yaml`、后端锁文件和 `tools/`。

`hardware/v1/sources/` 下两份未修改的历史上游仓库以固定 commit 的 Git submodule 保留；需要旧版研究资料时运行 `git submodule update --init`。当前 V1.2 的外部固件参考按锁文件与 `tools/fetch-v1_2-refs.py` 获取，不上传下载缓存和嵌套 `.git` 数据库。

这次没有执行建模、固件构建、硬件测试或完整跨机器复现。历史比较脚本可能读取未上传的旧 `.blend`／大数组；完整重跑前需取得对应资产，不能将缺失文件的检查跳过后宣称 PASS。当前模型可通过 LFS 直接下载查看。

## 审阅与来源

建议先审阅 [README](../README.md)、[资料索引](PROJECT_INDEX.md)、[当前状态](CURRENT_STATUS.md)和[采购表](../mechanical/procurement/M1.52_按厂家采购清单_2026-10-06.md)，再进入原生模型与 PCB。该 PR 是首次归档，所以源文件变更数量较多。

现有 GitHub Actions 流程保留为手动触发，防止资料上传被误认为重新执行了全部软件验收。本次没有新增自动部署或制造文件导出流程。

保留第三方通知与原许可证；本次未替 MORI 自有内容指定开源许可证。归档文件列表和 LFS 资产校验值见本目录下的 `publication_inventory.json` 与 `current_assets.json`。

本次归档检查见 [PUBLICATION_CHECKS](PUBLICATION_CHECKS.md)。
