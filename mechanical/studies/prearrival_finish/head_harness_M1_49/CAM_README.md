# M1.49 CAM四线贯通候选

M1.49当前原件上，CAM四根线已从Motion J5贯通到CAM J11的估计出线点，保持逻辑1→1至4→4；130个组合姿态的实体、线间及自身接近检查通过。为避开俯仰舵机，调整了三条局部路线的相位和一根身体段，并错开头部最后转弯的位置。所有打印件及硬件位置保持。该线束仍是独立候选，未加入主模型。固定与应力释放、另外七根导线的完整两端、FFC/FPC、带线装配和供应商制作图尚未完成。

- 主入口：cam_index.html。
- 当前520条曲线：cam_joined_candidates.npz，key为pinN_yY_pP。
- cam_joined_verification.json记录组合证明、全部依赖哈希与早期失败诊断的有限复用。
- 当前下段：front_lower_curves.npz；七根局部样线：front_neck_candidates.npz。
- 固定、另外七根完整导线、FFC/FPC、带线装配和供应商下料图未完成。
- 本目录index.html保留此前局部阶段，不能替代cam_index.html的更新状态。
- head_harness_M1_49的独立Blender含未应用的候选线；主模型与动画没有新增线束。
