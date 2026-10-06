# MORI V1.2 · 参数化机械预研

当前模型是 `mori_v1_2.blend`，图册 `index.html`，主报告 `../reports/mechanical_v1_2.md`。M1已完成，M2接口尚未冻结，M3为候选打印件；不是已适配实物的生产工程。V1.2采用120/160/95mm名义头/身/轮，实际正常高287mm，清晰腹部离地25mm，轮壳目标4mm。

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

MORI_V1_Assembly场景：CTRL_Yaw的Z为yaw、子级CTRL_Pitch的X为pitch。+X右、+Y前、+Z上。yaw正向左，pitch正向抬头；身体前倾另取-X。轮轴沿X且实际高度等于胎半径47.5mm。CAM、屏幕、相机属于pitch组，头机构分yaw/body组。

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

原厂PDF参考9.1mm深度与STEP9.35mm不同，三柱坐标有约0.06mm差异，最终安装孔和螺钉需先确认采购版本。LCD三柱后架和面罩模板是试配候选。相机窗口随安装位上移3mm；camera_kinematics.json已同步。

## M1.3 整体舱式结构

按用户进一步要求取消主要细长连接，改为三件连续承重体：身体整体舱体、含Yaw轴颈的杯形双轴承座、Pitch头部器件舱。电机座、轮轴承座、Yaw座、暂定板卡平台并入底盘；屏幕短压框直接连前隔板。另保留电池托盘和双电机共用短底盖。相同功能集合17件合为6件，详见reports/结构简化说明.md。

本次不是加外罩遮住杆架，monocoque_structure.py实际替换旧结构。完整管线包含与M1.2的同相机真实对比、整体电机舱的底部装入检查、全运动与线束采样。旧结构仅由保留函数在比较脚本内生成，未进入当前交付网格。

连续薄壁承重舱按95%有效填充估算，整机约1.26kg、Pitch约200g，至少±35%不确定度。整机略超1.0–1.2kg目标，需要按实物重算动力预算、优先对固定身体舱减重约60g（尚无误差余量）；未冻结减薄量或宣布载荷合格。三件主承重件和短维修件均需打印与循环验证。

P1的80×45电源板和完整装件尚未整合，旧44×16×10预留不代表新实板；当前板卡安装平台仍待后续回写。原M1.2在revisions/V1.2-M1.2_before_monocoque，可回退对照。
