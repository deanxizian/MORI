# R108P 发布复查

[native_readback.json](native_readback.json)记录实际 KiCad 版本、完整命令、退出码和输出。工程 ZIP 解压到独立临时目录后检查，原生文件字节未变。[source_receipt.json](source_receipt.json)记录接收文件哈希与 91 个接插件针位核对；它的 PASS 仅表示接收一致。

[原生针位复查](connector_readback.json)再次通过 KiCad API 直接读取解压板，核对 91 行针位、9 个连接器、封装与候选 BOM；[仓库检查记录](repository_checks.json)记录发布完整性和 31 项工具回归。

复查结果：40 项未连接、其余 DRC 0、图板差异 0、启用项全严重级 ERC 0。四类历史 ERC 忽略项仍明列。DRC 使用 `--exit-code-violations`，因此退出 **5**；没有把这个退出码当作工程通过。全板视觉、实机及制造均未获资格。

解压工程后可在该目录运行（需要 KiCad 10）：

```sh
kicad-cli pcb drc --format json --schematic-parity --refill-zones --severity-all --exit-code-violations -o drc_reopened.json MORI_Interface_C3.kicad_pcb
kicad-cli sch erc --format json --severity-all --exit-code-violations -o erc_reopened.json MORI_Interface_C3.kicad_sch
```

本次原始复查输出：[DRC](drc_reopened.json)、[ERC](erc_reopened.json)。这些命令没有 `--save-board`。原作者检查命令保存在[上级目录](../verification_commands.json)，保留当时路径，与本次便携工程复查区分。

仓库发布完整性仍由 `python tools/check_project.py` 核对，包括 ZIP 成员、来源 PCB 哈希和当前资产清单。该检查不能取代电路、回流、热、机械或实物验证。
