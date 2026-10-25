# 两台 S288 的串接线收在原电机座内

针对用户“舵机1~2的线不能藏在里面吗”，补查一套内部 U04 名义路线。三根导线各保留约 190 mm，利用两台电机前后对角空腔回绕，中间分层通过 1.6 mm 的电机间缝。串接采用两台电机的下方插口。**此研究没有改变上梁、底盖、舵机位置、固定孔或任何打印件，不需要为 U04 增加出线槽。**

这里的“内部”是现有打印电机座的内部。原厂 S288 以 1:1 来源几何检查，没有把线放进舵机的齿轮腔。线路主体额外避开两台原厂电机的完整外包框，不能利用模型内的空腔钻进电机；只有厂口短尾按源实体检查。

## 已完成检查

| 项目 | 当前结果和边界 |
|---|---|
| U04 静态实体 | `inside_check.json` PASS：0 / 0.5 / 1 mm 塑壳外伸试值 × 6 种几何线位配对，18 组名义 OD1 路线无相交；不代表实际电气针号重排 |
| 190 mm 长度 | 直线和圆弧采用解析弧长，三根分别 190 mm；用户给的是近似长度，不能作为加工裁线数值 |
| 所选路线余量 | 所选 1 mm 外伸试值增粗至半径 0.6 / 0.7 mm，无实体相交；离散网格与电机最小约 0.3 mm，与上座约 0.6 mm，线间约 0.4 mm |
| 主控进线共存 | `inside_compatibility.json` 9 个短段与 U04 无相交；短段穿过未开孔的上梁，原上梁对该短段仍是障碍，完整 U03 仍 BLOCKED。这是共存容量检查，不是出口放行 |
| 原上座落下 | `inside_sequence.json`：上座和两上软垫从上方 50 mm 落下，101 个位置无新增硬质相交；两软垫接触 NOT_TESTED，四处源轴承交叠约 0.000022 mm³，低于既有阈值，仍单列 |
| 螺钉／身体壳 | 四枚底盖螺钉各 69 个位置、前后壳各 275 个位置，均未碰这组 U04；不含其余柔性线路 |
| 底盖比较 | 底盖向上装入的 51 个位置未碰 U04，仅线与底盖几何比较，不代表可以带着全部总装这样拆装 |
| 结构／文件 | 0 打印件变化、0 新零件、0 新紧固件；26 个主模型／STL／电子细模／视频保护文件保持原散列 |

## 实物仍需核对

原配线仅有“导线段约 190 mm、单线含绝缘约 1 mm、插头几乎藏入”的用户报告。插头外伸毫米值、压接直尾、静态最小弯曲半径、三芯能否分别弯折、固定方式及真实防夹还没有测量资格。当前采用 0 / 0.5 / 1 mm 外伸、1 mm 直尾、尾部 3 / 5 / 7 mm 弯曲半径和线路主体最小 3 mm 半径，均是 ASSUMED。若三芯粘连，必须按实物调整，不能直接将三条独立路径当作真实线束。

余线如何留在空腔内、不被合盖移动，以及主控 U03 的单独出口、最终新载板端点、全部线束并存还未完成。**只对 U04 可不改打印件；不等于所有进出线都无需开口。**

原厂 S288 本轮仍是局部未采用参考，最新完整主模型仍 M1.58 的旧简化电机外形。`inside_U04_UNADOPTED.blend` 仅是局部审阅模型。未更新视频或提交 PR；未向硬件对话发送指令，未制造或上电放行。

## 图和来源

- `inside_closed.png`：原上座保持连续，串接线收在里面。
- `inside_open.png` / `inside_plan.png`：仅隐藏上座方便看线；所有检查均使用完整实体，隐藏是展示操作。
- 原厂 STEP 和变换来源见 `../s288_vendor_fit_M1_58/vendor_mesh.json`、`fit_review.json`；STEP SHA256 `6857b4a8a753a473ff0e1172aeb74e464bb3d3ca694625fcbfababd5e621952a`。
- 保留早期线间相交、主控进线相交以及增粗失败：`inside_first_check.json`、`inside_compatibility_before_drop.json`、`inside_drop_aligned_check.json`，均不是当前结果。
- 当前源散列在三份 `inside_*` 检查报告，实际命令／版本／日志在 `commands.json`。Blender 5.2.2 LTS，Python 3.13.13，numpy 2.3.4，manifold3d 3.5.3。一次未传 `--main` 的运行错误保留在 `internal_U04_drop.log`，已改用显式主模型输入。

复现当前研究（只写本目录，保护主模型）：

```sh
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py internal_U04_staggered_drop check_inside.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py internal_controller_coexistence check_inside_compatibility.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py internal_U04_sequence check_inside_sequence.py --main
python3 mechanical/studies/s288_interconnect_M1_58/run_stage.py internal_U04_render render_inside.py --main
```

PROTOTYPE / UNVALIDATED。以上 PASS 均限于所述名义几何，完整柔性装配 BLOCKED，实物防夹、线材弯折和固定 NOT_TESTED。
