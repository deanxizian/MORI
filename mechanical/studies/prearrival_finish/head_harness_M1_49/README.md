# M1.49 部分走线候选

M1.49当前原件上，11条局部路线已把身体入口抬至Z138mm；130姿态、局部线间下界0.423mm通过。CAM四根线已从Motion J5接到颈部Z200mm；其中一根上调1.05mm走线层，四根同时排布与七条局部容量样线共存检查通过，最小数值间隙下界0.330mm。所有打印件不变。头部端口、另外七根线的完整两端、FFC、固定与应力释放、带线装配及制作图仍未完成；这是独立候选，未加入主模型。

当前可用输入：

- spaced_entry_candidates.npz / spaced_entry_screen.json：11条较高入口的等长局部曲线，slot0..10。
- spaced_local_packing.json：局部线间PASS。
- body_layered_candidates.npz：身体路线池，选中的id见body_layered_four_screen.json。
- body_layered_four_candidates.npz：已连接的CAM四根身体至颈部曲线，pin1..4 × 13yaw；头部端尚未连接。
- selected_body_motion.json：当前主模型的身体段运动检查PASS。
- render_routes.py生成独立预览，主模型未变。

更早的入口/同平面组合失败记录保留，不作为当前可用路线。未执行任何旧脚本前缀，始终通过harness_context读取当前原件。

当前实体检查以current_source_verification.json为准：隐藏代理变换更新问题修复后，1716次局部/1152次身体段检查重跑PASS，所有集合显示状态切换后实体指纹一致。早期报告保留为历史，曲线本身和线间计算未变。
