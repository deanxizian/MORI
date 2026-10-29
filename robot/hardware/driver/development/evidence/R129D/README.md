# C3 R129D：补充一处参考地过孔

2026-10-26，将独立开发稿由 R127B 继续到 R129D。只新增 GND 通孔 `(1.95,16.45)`，铜环外径 0.50 mm、钻孔 0.30 mm；没有移动器件、修改旧铜、规则、禁布区、针位或板框。PCB SHA256：`42c17eaeb2588938e987a824ffdf5ba4770982bce8673eca89e7faefa16811df`。

原生填铜后为 **33 项未连接 / 0 其他 DRC / 0 图板差异 / 0 启用 ERC**。相对 R127B 的严格回归 PASS，2489 项精确计划核对通过；50 项供电铜宽筛查、全部旧焊盘连接、155 个 GND 焊盘、63 项关键邻接和旧参考地均无退化。相对原包 R108P 的原始几何审计仍为 FAIL，保留此前明确移件/改线差异。

新孔原生铜环完全接触 In1/In4 地填铜。MOTION_3V3 原换层孔 `(1.05,16.55)` 到最近双参考面地孔的距离由 4.026941 mm 降到 0.905539 mm；历史回流提示 **7 → 6**。2 mm 是项目筛查阈值，不能当作 IPC 标准、阻抗或 EMC 合格结论。原生正反面图和六层几何图已逐张查看，图像哈希在 `image_manifest.json`。

- [实际命令](commands.json)、[填铜检查](refill-drc.json)、[只读 DRC](drc.json)、[ERC](erc.json)。
- [精确修改计划](edit_plan.json)、[严格逐步回归](step-regression.json)、[计划差异核对](planned-delta.json)、[地孔接触检查](stitch-review.json)、[局部图审](visual_review.json)。
- [原始 R108P 回归](regression.json)、[当前结果](result.json)、[剩余连接](remaining_connections.csv)。

同轮 R129A 的 FAULT_N 候选损伤相机供电和参考地，R129B/C 的右侧地孔割裂 MOTION_3V3，均未采用；不能把候选减少的回流提示单独作为通过依据。失败方案、命令和报告见相邻 `R129_search/`，本机完整试验副本仍在 `robot/.state/c3-completion/trials/`。

R129D 只采用到本任务的独立开发稿。发布仍为 R108P，机械主模型和软件未采用本候选；工程仍 FAIL / PROTOTYPE / UNVALIDATED，不可制造。额定、浪涌、热、串扰、EMC、整板和实物检查仍未完成。
