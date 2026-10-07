# 拆分发布检查

这轮只检查资料拆分及交付，不是新的机器人设计或硬件验证。原始提交为 `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1`；具体结果见 [SPLIT_VALIDATION.json](SPLIT_VALIDATION.json)。

- 594 个收到的源文件、原生 CAD 文本与资产，其 Git blob 与原归档一致；四套工程 ZIP 中全部 242 个原始文件也与原提交逐字节一致；导航、归档属性和恢复工具单独维护。
- 172 个可恢复数据文件已对照原提交验证大小和 SHA256，LFS 数据核对对象指针。
- 23 个当前关键文件在本地验证了完整 SHA256，包括三个 Blender 工程、视频、尺寸源、契约和四套原生 PCB 主文件（PCB 现打包于 ZIP）。
- 新导航中的 91 个本地链接及 77 个固定提交证据链接检查通过。收到的原始源码说明保留原文，内部历史路径可能需要完整归档。
- 恢复工具实际下载一个公开资料文件，重复执行保留原文件；已有不同文件、路径越界、符号链接、损坏下载及并发新建文件的保护检查通过。
- 本地 `git lfs fsck` 通过；Gitleaks 扫描 10 个提交的约 4.68 MB 文本差异，无发现。原生 CAD 的二进制 diff 和 LFS 载荷不在这次文本扫描范围。GitHub 忽略本地 binary 属性，原 PCB/封装组达到 220,265 行，仍返回 406；已改用保留完整原字节的工程 ZIP，最终远端结果待更新。

本轮使用 Git 2.54.0、Git LFS 3.8.0、GitHub CLI 2.92.0、Gitleaks 8.30.1。主要检查命令为 `git ls-tree -rz`、`git show`、`git diff --check`、`git lfs fsck`、`gitleaks git --log-opts=main..HEAD`，以及 SHA256／恢复工具行为检查。不会将 GitHub diff 可读、扫描通过或源码完整解释为工程构建、自动代码审查或实物验证通过。
