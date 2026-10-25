# 下载、查看与重建

## 当前快照

```sh
git clone https://github.com/deanxizian/MORI.git
cd MORI
git lfs install --local
git lfs pull
python3 tools/check_project.py
python3 -m http.server 8000 --bind 127.0.0.1
```

默认克隆 main；审阅未合并 PR 时切换到对应分支。完整主模型、电子细模、旧版动画工程使用 LFS；GitHub 源码 ZIP 可能仅带 LFS 指针。其他原生工程包/视频/文档用普通 Git。静态页为 `http://127.0.0.1:8000/mechanical/index.html`。

最新自制 PCB 在 [hardware/driver](../hardware/driver/README.md)，完整 KiCad ZIP 的原生 PCB/原理图字节保持，只有库搜索表改相对路径；不包含制造文件。

## 按需恢复 CAD 输入

只看 Blender、STL、图册不需要恢复。重建前使用 Python 3.12、Blender 和脚本所需 manifold3d/OCP；运行时不纳入 Git。

```sh
python3 tools/restore_archive_assets.py --list
python3 tools/restore_archive_assets.py --group mechanical-data --group legacy-helpers --group mechanical-build-inputs --group native-pcbs --group m1-58-inputs --group m1-58-validation
python3 tools/restore_m1_55_evidence.py --group approval
```

工具按记录的 SHA256 验证并拒绝覆盖不同文件。原始恢复清单固定在 `48fe22aa75554c9d7bb237e2d2dcacca7f83dde1`；M1.58 新厂家/批准输入另装入本仓库普通 Git ZIP。旧 PCB 包移动到 `mechanical/input_assets/pcb_reference/native_projects/`，解出时保留旧路径，防止篡改当时输入。

只校验已保存的 M1.58 模型时，恢复 `m1-58-inputs` 与 `m1-58-validation` 两组即可。后者包含模型实际引用的 10 份精确实体数据，使用匹配主模型的原工作区字节；其中同名 CAM/相机资料较早期归档更新。若先前单独恢复过旧 `mechanical-data`，工具会拒绝覆盖不同文件，应先把冲突的旧副本移出当前输入位置，再恢复当前组，不要混用版本。

原独立对比 Blender 未发布，停靠托架只按已发布且校验哈希的矩阵回执比较，原 Blender 追溯明确为 BLOCKED。旧硬件保护清单也单列历史追溯状态，缺失/版本不同不会冒称通过；当前驱动板文件完整性由 `tools/check_project.py` 单独检查。

保存模型 M1.58 的电气输入早于当前 IF-C1-R4/C3。全量重建前要完成接收差异处理；恢复成功不代表当前合同已与模型同步，也不代表全部历史比较可重跑。实际主模型、STL、图与已发布检查的哈希见 [current_assets](current_assets.json)。

## 历史证据

[M1.55 证据包](review_evidence/M1_55_archives.json)和恢复工具保留，旧日期/输入/失败范围不改。原始归档见 [HISTORY](HISTORY.md)。本轮只发布有用的当前研究静态图和检查，没有发布全部过程 Blender/巨型网格或本机运行日志。

## 检查

`tools/check_project.py` 核对当前入口链接、版本、LFS 内容、资产/原生包/模型图哈希；它只验证发布完整性，不能替代机械干涉、实物装配、电路或上电资格检查。
