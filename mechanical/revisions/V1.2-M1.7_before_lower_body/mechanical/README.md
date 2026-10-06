# MORI V1.2 · 参数化机械预研

当前模型是 `mori_v1_2.blend`，图册 `index.html`，主报告 `../reports/mechanical_v1_2.md`。M1已完成，M2接口尚未冻结，M3为候选打印件；不是已适配实物的生产工程。当前M1.7采用120/160/105mm名义头/身/轮，实际正常高287mm，清晰腹部离地25mm，轮壳目标4mm。

唯一共享几何输入 `../config/geometry.json`；机械限制包络/接口 `../contracts/mechanical_interfaces.json`。硬件拥有components.json，本次只读核对V1.2-H0.2-P1，机械任务未修改该文件；新原厂尺寸用ADR-MECH-013交接，不修改硬件真值。旧A4保存于revisions/V1-A4_before_V1_2，models/MORI_V1_A.blend仅为当前模型兼容链接。根目录旧params/scripts/models为旧版历史，不参与此管线。

## 重新生成

本机已实际执行：Blender5.2.1LTS，Blender Python3.13.13，Manifold3.5.3。1坐标单位=1mm，scene scale_length0.001；STL按mm导入。

```bash
cd /Users/dean/Documents/MORI
python3 mechanical/scripts/run_all.py
```

可用MORI_BLENDER指定Blender可执行文件。`--core`仅生成build/validate/render/export，不刷新汇总和图册。脚本只重建有mori_owner标签的项目对象，外来对象保留；重复生成验证实际运行两次。比较脚本仅临时切换配置的A/B选择，不保存另一份权威参数。

当前vendor二进制适配macOS ARM64/CPython3.13；其他平台须使用Blender自带Python安装manifold3d==3.5.3到scripts/vendor。普通Python可选安装Pillow用于接触表；单张Blender图无需Pillow。完整管线末尾的图册合成在本机用已装Pillow的Python环境运行。

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

原厂PDF参考9.1mm深度与STEP9.35mm不同，三柱坐标有约0.06mm差异，最终安装孔和螺钉需先确认采购版本。LCD三柱后架和面罩模板是试配候选。M1.1曾将相机窗口上移3mm；最新窗口位置及圆屏居中以M1.7共享参数和camera_kinematics.json为准。

## 分件基础（M1.4引入）

M1.4已引入的分件方式：身体采用平顶板、两块平侧板、浅电机底托与可拆Yaw座；头部使用开放U托、浅屏幕框、平面俯仰U托和短转台。保留电池托盘及短底盖。这组支撑由6个复杂总成拆为11个简单组件，删除包围墙、前隔板、深杯壁和旧电源/USB专用高架。

simple_modules.py生成实际几何。16处新增连接统一采用试配M2×12螺钉和M2螺母；规定装配阶段的工具杆路径与4种模块拆出路径已纳入validate_modules.py。详细先后顺序、需先拆哪些件和检查边界见reports/结构简化说明.md与module_service_checks.json。

全部候选打印件的作用与方向提示见reports/打印件审查.md。尚未实际切片、试打或验证强度。质量与惯量从当前网格及附件假设计算，至少±35%不确定度；参看mass_budget.json及目标检查，不能把几何通过当作动力验收。

P1完整电源与充电模块仍未布局，橙色旧占位不能代表新实板。删除其旧高架后最终固定片仍待选型与尺寸回写。原M1.3在revisions/V1.2-M1.3_before_simple_modules；旧版不定义当前参数。

## M1.5 — 降低平板

M1.5已引入的身体低平板方案继续保留。中间板整体下移7mm，舵机落在Z127的平面；取消中央贯穿孔和下挂托槽。两侧板缩短7mm，原Yaw承重座向下延伸7mm，侧口开到板面；主控/IMU预留与壳内固定座跟随。11个支撑打印件数量不变。电池到板底名义竖向余量8mm。检查见reports/lowered_deck_check.json、module_service_checks.json与validation.json。

底面接触不代表舵机已经锁固：安装耳紧固、防转、实物电池线束、P1全部电源板和打印强度仍待阶段B。模型、候选STL与真实渲染由同一套脚本生成，未打印或进行平衡验证。对比基线由config/geometry.json中的comparison_baseline指向只读M1.4归档，完整包包含重现对比所需文件。

## M1.6 — 头内平板支架

M1.6已引入的方案：Pitch_Cradle改为平直侧板/后板、直切角及短固定耳，取消球面裁切形成的高圆弧边。矩形CAM背板、转轴孔和麦克风通道保留；外壳和原厂圆屏的形状分别保留。实际单件图为renders/head_support.png，前后对比为renders/structure_comparison.jpg。

记录见reports/flat_head_check.json和结构简化说明.md。最终头壳/板卡紧固、材料和实物强度仍未验证。完整包含只读M1.5比较模型，不以历史参数定义当前尺寸。

## M1.7 — 轮胎加大、摄像头独立、圆屏居中

轮胎105×18mm（原95×18），轮轴52.5mm（原47.5），轮驱和独立轴承同步上移5mm。轮窝由相同半径、轴高和4mm目标间隙生成；腹部离地25mm，外部头身基准保留。短底托顶面Z81、侧板42mm；电池及托盘升高3mm，板下名义余量5mm，尚未验证真实插头/线束。

圆屏原厂总成刚性上移6.2mm，有效显示区45.68mm和60mm外围黑面罩的圆心都对齐头球正前方中心。相机在上方白壳独立开8mm孔，平片窗口7.7mm；瞳孔在pitch局部坐标[0,44,41]mm。相机小板、镜头和FPC仍是待尺寸核对的包络；没有把LCD或CAM实板缩放。

同视角前后图：renders/appearance_comparison.jpg；单独头部图：renders/face_detail.png。检查：reports/wheels_camera_change.json、display_center_alignment.json和face_body_clearance.json，以及完整validation.json。外参和装配坐标自动重新导出；软件需接收0.0525m轮半径和新相机外参，机械任务没有擅改控制/电气文件。

当前对比基线为config/geometry.json指向的M1.6只读模型。完整版本包包含重现对比所需三个基线文件。M1.5/M1.6段落属于历史变更说明，不定义当前尺寸。候选打印、动力和实机平衡尚未通过实物验证。
