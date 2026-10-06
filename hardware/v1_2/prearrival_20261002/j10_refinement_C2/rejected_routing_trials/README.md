# 未采用的布线试验

本目录的 04_manual_not_accepted.kicad_pcb 是失败试验，不是当前候选，也不是新版 PCB。不得制造。

该试验曾平移 D30/R50，并留下间距/走线问题；对应 ../reports/04_manual_drc.json 和 ../reports/04_manual_routes.json。当前候选由 finalize_study.py 回到已经做过空间筛查的原 D30/R50 XY，只保留明确列出的摆放变化，拆除了失败走线，仍有未连接项目。

较早 ../reports/01_placement_drc.json、02_placement_drc.json 和 03_routes_drc.json 同样是中间试验。最终状态仅以 ../reports/FINAL_PLACEMENT_ONLY_drc.json 与 ../validation.json 为准。
