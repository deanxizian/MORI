# 当前发布检查

当前硬件入口已更新为 **C3 R108P**。独立解压后运行 KiCad 10.0.6 原生检查，40 项未连接、其余 DRC 0、图板差异 0、启用项全严重级 ERC 0；原生工程字节未改。实际命令、退出码和历史忽略项见[硬件发布记录](../hardware/driver/publication/README.md)。工程仍 FAIL / PROTOTYPE / UNVALIDATED，不可制造。

## 此前的项目整理记录（R98I）

1.3.0-dev.1 / 2026-10-25 的[实际检查记录](review_evidence/project_1_3/publication.json)。25项工具回归、13项前端测试、前端构建、验证车376件资产与77个链接、当前模型/图/STL哈希及新目录恢复检查通过。

KiCad工程包解出后 ERC0、其余DRC0、原理图一致性0，但仍有45项未连接，工程状态仍FAIL。主模型重新打开为M1.58，没有改几何或再生成视频。扫描的8个候选“密钥”均为JSON证据文件SHA256，逐条分类见[审阅记录](review_evidence/project_1_3/secret_scan_review.json)。

这些是发布完整性检查，不是整机装配、电路、强度、热或平衡资格验证；当前待办见[状态](CURRENT_STATUS.md)。旧日期检查保留在review_evidence，用于追溯，不沿用为当前通过。

PR #15 复审修复后：工具回归增至31项；当前保存模型的便携输入恢复与真实 Blender 校验完成，0 FAIL，原有 BLOCKED/NOT_TESTED 保留。详见[本次修复记录](review_evidence/project_1_3/review_fixes.json)。
