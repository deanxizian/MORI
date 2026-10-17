# 交付范围与复核

本包从本地未提交的验证车目录整理而来，来源路径和每个导入文件的 SHA-256、字节数及 ZIP 内成员都在 [import_manifest.json](import_manifest.json)。源工作区 HEAD `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1` **不包含这些原先未跟踪的验证车文件**，不能用该提交恢复它们。公开版本以本次 PR 的提交为准。

## 包含

- R37/R41、R55、R59 和 R60 对比方案的原始打印件、设计记录、Blender 装配和预览。
- 主要已选模块的厂家规格书/CAD 压缩包、当前清单、接线和逐孔紧固件表。
- v159 部署清单的完整 295 文件闭包，原许可和离线测试。
- 第 71 轮原始遥测及结果摘要、第 95 轮已有的本机摘要/回执、相机和 CAD 检查记录。

## 不包含，也未删除

- 全部 R0–R60 中间生成缓存、重复导出、渲染过程文件和全部历史 Blender。它们仍在原本地目录，未被本次整理清理。
- 全部物理测试大日志；尤其第 95 轮完整日志仍待从 Pi 取回。
- 私人相机照片、语音录音、云 API 凭据、蓝牙配对资料、下载的工具链和构建缓存。
- 未冻结的第三/第四层头部方案、所有 CAM/语音/人物应用的一键部署和主项目固件适配。
- 全链条历史 CAD 生成脚本。最终 STEP/STL/Blender 可直接打开；历史 JSON 不是自包含的从零构建工程。

## 检查

```sh
# 仓库根目录；标准库即可，约数秒到数十秒
python3 test_rig/tools/check_release.py
python3 test_rig/tools/verify_trial71.py

# 硬件无关控制回归；还需要 C++17 编译器
cd test_rig/control
python3 -m unittest discover -s tests -q
```

`check_release.py` 核验导入文件和压缩成员、源码清单、五个 STL 的连通性/闭合边和正体积，以及新入口文档的本地链接。可选 CAD 复核另需 `cadquery-ocp==7.8.1.1.post1`，使用 `tools/check_step.py`；结果只覆盖现有 STEP，不能证明材料强度或真实装配。

本次实际执行记录在 [publication](evidence/publication/)：v159 492 项、v142 410 项离线测试通过，五个 STEP 为有效单实体，五个 STL 无开放/非流形边，原始第 71 轮指标重算一致。原始上游与历史文件的空白字符不做格式化，避免破坏来源哈希；新文档和工具按正常空白检查。

Blender ZIP 使用普通 Git，解压不依赖 LFS。主项目自己的 Blender 仍遵循根目录 LFS 说明。厂家 PDF/CAD 和参考模型保留原始来源与权利；本次公开不改变第三方许可，也没有新增商品库存、价格、认证或制造放行承诺。
