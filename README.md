# MORI

MORI V1.2 两轮主动平衡机器人原型，仍为 **PROTOTYPE / UNVALIDATED**。

本次将首次归档拆成 10 份依次叠加的 PR，便于审阅当前源码、契约、原生 PCB 和机械资料。各 PR 的 base 是前一份分支；全部保持未合并。

- [完整资料树与导航](https://github.com/deanxizian/MORI/tree/review/10-navigation)
- [不可变的原始归档快照](https://github.com/deanxizian/MORI/tree/48fe22aa75554c9d7bb237e2d2dcacca7f83dde1)
- 当前规格：[MORI_SPEC_V1_2.md](MORI_SPEC_V1_2.md)
- 协作与证据边界：[AGENTS.md](AGENTS.md)

当前三个 Blender 工程使用 Git LFS。原生 KiCad 文件仍用普通 Git 保存完整字节，按图形工程文件审阅；不把其大量序列化内容作为源码文本 diff。历史快照、研究数组及生成报告保留在原始归档，不混入当前审查。
