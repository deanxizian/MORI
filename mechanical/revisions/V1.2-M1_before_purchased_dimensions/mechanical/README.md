# MORI V1.2 · 参数化机械预研

当前模型是 `mori_v1_2.blend`，图册 `index.html`，主报告 `../reports/mechanical_v1_2.md`。M1已完成，M2接口尚未冻结，M3为候选打印件；不是已适配实物的生产工程。V1.2采用120/160/95mm名义头/身/轮，实际正常高287mm，清晰腹部离地25mm，轮壳目标4mm。

唯一共享几何输入 `../config/geometry.json`；机械限制包络/接口 `../contracts/mechanical_interfaces.json`。硬件拥有components.json，本次只读核对收尾时发现的V1.2-H0.1，不修改硬件真值。旧A4保存于revisions/V1-A4_before_V1_2，models/MORI_V1_A.blend仅为当前模型兼容链接。根目录旧params/scripts/models为旧版历史，不参与此管线。

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

DATUMS保留数学母球/原始截面/轴，B身体明确采用小幅卵形修形。DOCK是独立禁驱维护托架；KEEP_OUT为天线/插头预留，COUPONS为试样。每件带分类、数据状态、运动组和验证状态。原厂只证实部分字段时完整零件仍标ASSUMED，不能把它当MEASURED。LCD完整55×55矩形预留与当前头壳存在条件冲突；真实非矩形边界未知，圆形后部件只是构造模板，绝不表示整屏已适配。

较大的参数变化会要求重排支架和板卡；自动重建不是对所有参数组合的装配保证。所有改变必须重新验证。修改真实器件包络不能靠非等比缩放。

## 输出与限制

exports/stl只输出打印候选及试样，保留装配坐标。采购硬件和轮胎不在STL中。轮转接盘尚待原厂输出/锁紧细节，不能直接加工投产。平面面罩模板见exports/templates。实际逐件尺寸和状态在reports/bom.csv/json。

图册、渲染、爆炸图和STL来自同一套实际几何；爆炸偏移只用于画面。报告记录实体干涉、联合姿态、光学遮挡、轮胎间隙、取电池路径、单位回读、估算质量/惯量。有限采样、保守线束、全局壁厚/自交未测和未知器件安装孔都单列；待试打、台架、实机平衡和预算/续航验证。
