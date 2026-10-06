# MORI V1.2 · 参数化机械预研

当前模型是 `mori_v1_2.blend`，图册 `index.html`，主报告 `../reports/mechanical_v1_2.md`。M1已完成，M2接口尚未冻结，M3为候选打印件；不是已适配实物的生产工程。当前M1.9采用120/160/105mm名义头/身/轮，实际正常高282mm，腹部离地20mm，轮壳目标4mm。

唯一共享几何输入 `../config/geometry.json`；机械限制包络/接口 `../contracts/mechanical_interfaces.json`。硬件拥有components.json，本次只读核对V1.2-H0.3-S3，机械任务未修改该文件；新原厂尺寸用ADR-MECH-013交接，不修改硬件真值。旧A4保存于revisions/V1-A4_before_V1_2，models/MORI_V1_A.blend仅为当前模型兼容链接。根目录旧params/scripts/models为旧版历史，不参与此管线。

## 重新生成

本机已实际执行：Blender5.2.1LTS，Blender Python3.13.13，Manifold3.5.3。1坐标单位=1mm，scene scale_length0.001；STL按mm导入。

```bash
cd /Users/dean/Documents/MORI
python3 mechanical/scripts/run_all.py
```

可用MORI_BLENDER指定Blender可执行文件。`--core`仅生成build/validate/render/export，不刷新汇总和图册。脚本只重建有mori_owner标签的项目对象，外来对象保留；重复生成验证实际运行两次。比较脚本仅临时切换配置的A/B选择，不保存另一份权威参数。

当前vendor二进制适配macOS ARM64/CPython3.13；其他平台须使用Blender自带Python安装manifold3d==3.5.3到scripts/vendor。完整管线的图册合成需要普通Python安装Pillow；可先运行 `python3 -m pip install Pillow`。单张Blender图及 `--core` 管线无需Pillow。完整管线末尾的图册合成在本机用已装Pillow的Python环境运行。

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python mechanical/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/render.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/export.py
```

## 可编辑对象与运动

MORI_V1_Assembly场景：CTRL_Yaw的Z为yaw、子级CTRL_Pitch的X为pitch。+X右、+Y前、+Z上。yaw正向左，pitch正向抬头；身体前倾另取-X。轮轴沿X且实际高度等于胎半径52.5mm。CAM、屏幕、相机属于pitch组，头机构分yaw/body组。

DATUMS保留数学母球/原始截面/轴，B身体明确采用小幅卵形修形。DOCK是独立禁驱维护托架；KEEP_OUT为天线/插头预留，COUPONS为试样。每件带分类、数据状态、运动组和验证状态。原厂只证实部分字段时完整零件仍标ASSUMED，不能把它当MEASURED。LCD35079已导入原厂113实体STEP，保留完整原厂外形与1:1刚性变换；旧假定矩形冲突被实际圆形CAD替代。两个连接器的三角转换有拓扑问题，保留所有原厂三角面，检查时使用源CAD保守外接框，因此完整精确装配仍BLOCKED。CAM板框37×37mm和孔中心距32.6mm已核；12mm装件厚度只是预留，其余未选型模块保持PLACEHOLDER。橙色内件表示资料未全，不是实测板卡。

较大的参数变化会要求重排支架和板卡；自动重建不是对所有参数组合的装配保证。所有改变必须重新验证。修改真实器件包络不能靠非等比缩放。

## 输出与限制

exports/stl只输出打印候选及试样，保留装配坐标。采购硬件和轮胎不在STL中。轮转接盘尚待原厂输出/锁紧细节，不能直接加工投产。平面面罩模板见exports/templates。实际逐件尺寸和状态在reports/bom.csv/json。

图册、渲染、爆炸图和STL来自同一套实际几何；爆炸偏移只用于画面。报告记录实体干涉、联合姿态、光学遮挡、轮胎间隙、取电池路径、单位回读、估算质量/惯量。有限采样、保守线束、全局壁厚/自交未测和未知器件安装孔都单列；待试打、台架、实机平衡和预算/续航验证。

## 采购件原厂尺寸与CAD

V1.2-M1.1已引入的采购件尺寸依据、未知项见reports/purchased_dimensions.md，逐对象审计见reports/purchased_geometry_audit.json。源文件保存在sources/v1_2_verified_dimensions/，哈希在机械接口JSON中。未选商品、缺厚度/插头和未确认版本都不能当成最终加工依据。

Blender重建直接读lcd35079_mesh.json，不依赖OpenCascade。若需从原厂STEP重新生成该缓存，在独立Python环境中安装cadquery-ocp==7.8.1.1.post1，然后执行：

```bash
python3 mechanical/scripts/convert_vendor_step.py
python3 mechanical/scripts/run_all.py
```

转换器不修改原始STEP。毫米/比例/原厂文件哈希写入缓存；113个源BRep通过有效性检查，107、108两子实体的网格缺陷并未修复成功。默认线性弦差0.015mm，108/109细分0.001mm；拓扑修复尝试仅在内存、容差上限0.0001mm。不要用代理网格导出采购件或宣称完整实体装配已验证。

原厂PDF参考9.1mm深度与STEP9.35mm不同，三柱坐标有约0.06mm差异，最终安装孔和螺钉需先确认采购版本。LCD三柱后架和面罩模板是试配候选。M1.1曾将相机窗口上移3mm；最新窗口位置及圆屏居中以当前共享参数和camera_kinematics.json为准。

## 当前 M1.9：两处舵机联合重排

轮驱S288绕原X轴分别−90°/+90°横躺，机身最高点77→62.5mm。电池中心103→91mm，主安装板顶面127→115mm，电池上方仍有5mm名义间隙。电源板80×40×18mm容量区放在独立平托板上；这是待硬件适配的设计空间，不是实际S3板尺寸。

Yaw SCS0009倒装在头内yaw组，机壳随左右转头，输出/舵盘通过可拆D形反力轴固定到身体。独立承重轴承及开口宽侧板桥承担头重。head_yaw与舵机相对输出角符号相反；IMU安装绕身体Z转90°，实际轴向、零位和反馈需实机标定。软件/电气文件未改，详见../reports/decisions/ADR-MECH-021-combined-belly-relayout.md。

新增生成步骤belly_relayout.py在simple_modules.py之后，最终几何只有config/geometry.json一个参数源。旧构造阶段是中间实现，不是并行设计真值。支撑从11件变13件，新增反力轴与电源平托板。不会仅为减少零件而恢复大型封闭舱或细长悬臂支架。

原厂器件不缩放。打印件最终孔、实际舵盘夹紧与轮输出连接、轴承保持、PCB专用固定片尚待实物。组装顺序及拆卸前提在reports/组装与打印.md；新增拆出/工具检查见belly_relayout_validation.json，所有检查见validation.json。有限采样和假设质量不是连续证明或动态平衡认证。

当前只读对比基线为M1.8，位于revisions/V1.2-M1.8_before_belly_relayout。旧模型、参数和报告保留，不定义当前尺寸。完整交付包包含重现比较所需的5份基准文件。质量比较中两版未知电源板都按30g估算，避免把空白容量框按实心密度计重；至少±35%不确定。

本次新增两个近景：renders/belly_detail.png、renders/yaw_drive_detail.png。所有视图来自实际Blender网格，STL不使用爆炸坐标。未进行切片、打印、称重或实机平衡。
