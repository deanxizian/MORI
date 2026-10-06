# MORI 实际检查记录

Blender 5.2.1 LTS；前方 -Y；单位 mm；装配帧 1。

PASS 22 / FAIL 0 / NOT_CHECKED 11。

**这是装配与结构预研，不是生产放行、自平衡或强度合格证。**

## PASS — environment
实际运行 Blender 检查，并核对参数文件与已保存模型摘要

```json
{
  "blender": "5.2.1 LTS",
  "python": "3.13.13 (main, Apr 25 2025, 12:39:20) [Clang 21.0.0 (clang-2100.0.123.102)]",
  "params_sha256": "15274cb22039a3964adc89a76167d62c7b770437e9ce0ab555dc3b1b62cd86d6",
  "current_params_sha256": "15274cb22039a3964adc89a76167d62c7b770437e9ce0ab555dc3b1b62cd86d6",
  "unit_scale": 0.0010000000474974513,
  "front": "-Y"
}
```

## NOT_CHECKED — reference_image_comparison
仅收到文字附件，没有参考图片；未进行图片对照

## PASS — true_spherical_mothers
头/身原始母球等半径、无非等比缩放

方法与范围：逐顶点到母球球心的欧氏距离；保留隐藏构造球。

```json
[
  {
    "name": "Head_Mother_Sphere",
    "diameter_mm": 100.0,
    "scale": [
      1.0,
      1.0,
      1.0
    ],
    "max_vertex_radius_error_mm": 5.249026192899464e-05
  },
  {
    "name": "Body_Mother_Sphere",
    "diameter_mm": 140.0,
    "scale": [
      1.0,
      1.0,
      1.0
    ],
    "max_vertex_radius_error_mm": 0.0001422747286738968
  }
]
```

## PASS — retained_spherical_surfaces
未截切外球面的一致性与网格弦差

方法与范围：筛选半径偏差 <0.12 mm 且法线与径向一致的外表面三角形；检查顶点及面重心，排除切面/孔。

```json
[
  {
    "part": "Head_Front_Shell",
    "outer_vertices_sampled": 2946,
    "outer_triangles_sampled": 5414,
    "max_vertex_radial_error_mm": 0.029692854818506476,
    "max_triangle_centroid_sag_mm": 0.03002557948502016
  },
  {
    "part": "Head_Rear_Shell",
    "outer_vertices_sampled": 3549,
    "outer_triangles_sampled": 6677,
    "max_vertex_radial_error_mm": 0.029931864133168062,
    "max_triangle_centroid_sag_mm": 0.03002545424005376
  },
  {
    "part": "Body_Upper_Shell",
    "outer_vertices_sampled": 2556,
    "outer_triangles_sampled": 4545,
    "max_vertex_radial_error_mm": 0.07439834040714288,
    "max_triangle_centroid_sag_mm": 0.04134283241093328
  },
  {
    "part": "Body_Lower_Shell",
    "outer_vertices_sampled": 4307,
    "outer_triangles_sampled": 7777,
    "max_vertex_radial_error_mm": 0.0817187195995217,
    "max_triangle_centroid_sag_mm": 0.041584050536116024
  }
]
```

## PASS — measured_dimensions
装配姿态从实际网格计算尺寸

方法与范围：网格全顶点极值；轮距=两个实际旋转中心间距，非图纸估读。

```json
{
  "overall_xyz_mm": [
    158.8000030517578,
    139.98513793945312,
    235.9926300048828
  ],
  "bounds_xyz_mm": [
    [
      -79.4000015258789,
      79.4000015258789
    ],
    [
      -69.99259185791016,
      69.99254608154297
    ],
    [
      0.0,
      235.9926300048828
    ]
  ],
  "body_cut_width_mm": 112.0,
  "head_mother_diameter_mm": 100.0,
  "body_mother_diameter_mm": 140.0,
  "tire_diameter_mm": 95.0,
  "track_center_to_center_mm": 138.0,
  "wheel_axle_z_mm": 47.5,
  "body_center_z_mm": 90.0,
  "axle_drop_mm": 42.5,
  "belly_ground_mm": 20.0
}
```

## PASS — body_front_proportion
侧截后的身体宽度仍大于头部母球直径

```json
{
  "cut_width_mm": 112,
  "head_mm": 100,
  "ratio": 1.12
}
```

## PASS — two_tire_ground_contacts
只有两个轮胎接地，其余零件不穿地

方法与范围：全部实际三角网格顶点最低值；平面 Z=0 的闭合实体接触。

```json
{
  "contacts": [
    "Tire_L",
    "Tire_R"
  ],
  "underground": []
}
```

## PASS — actual_wheel_shell_gap
轮胎、轮毂及轮毂盖到静止外壳的真实最小间隙

方法与范围：三角 BVH 最近点上界 + 侧面分离半空间下界相等，构成最小距离证据；不是单独用包围盒判碰。对轴对称转动保留同一 X 分离界。

```json
[
  {
    "part": "Tire_L",
    "measured_surface_distance_mm": 4.0,
    "separating_plane_lower_bound_mm": 4.0,
    "witness_shell_mm": [
      -56.0,
      0.0,
      84.0
    ],
    "witness_part_mm": [
      -60.0,
      2.2349802875922496e-15,
      84.0
    ]
  },
  {
    "part": "Wheel_Hub_L",
    "measured_surface_distance_mm": 5.0,
    "separating_plane_lower_bound_mm": 5.0,
    "witness_shell_mm": [
      -56.0,
      0.0,
      72.5
    ],
    "witness_part_mm": [
      -61.0,
      1.5308087642548068e-15,
      72.5
    ]
  },
  {
    "part": "Wheel_Cap_L",
    "measured_surface_distance_mm": 20.99999237060547,
    "separating_plane_lower_bound_mm": 20.99999237060547,
    "witness_shell_mm": [
      -56.0,
      0.0,
      72.5
    ],
    "witness_part_mm": [
      -76.99999237060547,
      2.86102294921875e-06,
      72.50000762939453
    ]
  },
  {
    "part": "Tire_R",
    "measured_surface_distance_mm": 4.0,
    "separating_plane_lower_bound_mm": 4.0,
    "witness_shell_mm": [
      56.0,
      0.0,
      84.0
    ],
    "witness_part_mm": [
      60.0,
      2.2349804993504864e-15,
      84.0
    ]
  },
  {
    "part": "Wheel_Hub_R",
    "measured_surface_distance_mm": 5.0,
    "separating_plane_lower_bound_mm": 5.0,
    "witness_shell_mm": [
      56.0,
      0.0,
      72.5
    ],
    "witness_part_mm": [
      61.0,
      1.5308086583756884e-15,
      72.5
    ]
  },
  {
    "part": "Wheel_Cap_R",
    "measured_surface_distance_mm": 21.0,
    "separating_plane_lower_bound_mm": 20.99999237060547,
    "witness_shell_mm": [
      56.0,
      0.0,
      72.5
    ],
    "witness_part_mm": [
      77.0,
      1.9073486328125e-06,
      72.5
    ]
  }
]
```

## PASS — head_body_static_gap
头壳下缘与身体顶部间隙

方法与范围：真实三角最近点 + Z 截平面分离下界。

```json
{
  "surface_gap_mm": 0.79998779296875,
  "body_witness_mm": [
    0.0,
    32.0,
    148.0
  ],
  "head_witness_mm": [
    -9.313225746154785e-08,
    32.0,
    148.79998779296875
  ]
}
```

## PASS — exactly_three_actuators
全机三个执行器

```json
[
  "drive_L",
  "drive_R",
  "head_yaw"
]
```

## PASS — static_interference_screen
内部/外部所有实体两两碰撞筛查；未列出的数值接触不自动豁免

方法与范围：实际闭合三角实体求交体积（含完全包含）+ BVH 表面接触。0.001 mm³ 数值体积阈值；预期接触仅容许报告所列极薄数值层或 <0.5 mm³ 网格弦差接触。

```json
{
  "volume_count": 0,
  "unresolved_count": 0,
  "expected_count": 71,
  "details": "interference_pairs.json"
}
```

## PASS — motor_envelope_installation
名义电机/编码器包络与外壳及支架筛查

方法与范围：已执行三角形碰撞检查；只证明当前包络，绝不表示供应商器件已适配。

```json
{
  "conflicts": [],
  "can_mm": [
    25,
    60
  ],
  "encoder_length_mm": 12
}
```

## NOT_CHECKED — continuous_global_interference_proof
已做离散姿态的三角实体布尔体积求交；尚未完成所有内部零件在步长之间的连续构型空间证明

方法与范围：Manifold 3.5.3 实体交集；保留毫米三角近似与数值阈值。

## PASS — head_yaw_sweep
头部 ±60° 运动包络检查

方法与范围：每个角度转换同一套真实三角网格，BVH+内点筛查；包括转盘、外壳、线束预留和固定限位块。步间仍需连续核验。

```json
{
  "range_deg": [
    -60,
    60
  ],
  "step_deg": 5,
  "poses": 25,
  "volume_conflicts": [],
  "unresolved_contacts": []
}
```

## PASS — continuous_external_yaw_envelope
外部头壳/身体及转盘穿孔的连续角度包络

方法与范围：Z 截平分离与旋转不变的圆柱孔径界限；只覆盖这些外部接口，不代替全部内部连续运动证明。

```json
{
  "head_cut_z_mm": 148.8,
  "body_top_z_mm": 148.0,
  "axial_gap_mm": 0.8,
  "rotor_radial_hole_gap_mm": 2.1999999999999993
}
```

## PASS — wheel_360_sweep
左右车轮各完整旋转一周

方法与范围：真实轮胎/轮毂/盖三角网格，0…360°（含端点），与静止外壳的 BVH/内点检查。

```json
{
  "step_deg": 10,
  "poses_per_side": 37,
  "total_side_poses": 74,
  "conflicts": []
}
```

## PASS — body_pitch_plus_minus_15
绕轮轴前后倾斜 ±15° 的接地风险

方法与范围：X 轴=(0,0,47.5)；每 1° 变换全部实体网格顶点。仅几何包络；不代表安全运动角或自平衡验证。

```json
{
  "samples": [
    {
      "angle_deg": -15,
      "belly_lowest_z_mm": 18.561214447021484,
      "non_tire_lowest_z_mm": 14.799999237060547,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -14,
      "belly_lowest_z_mm": 18.737606048583984,
      "non_tire_lowest_z_mm": 14.804980278015137,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -13,
      "belly_lowest_z_mm": 18.922760009765625,
      "non_tire_lowest_z_mm": 14.815253257751465,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -12,
      "belly_lowest_z_mm": 19.077268600463867,
      "non_tire_lowest_z_mm": 14.802799224853516,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -11,
      "belly_lowest_z_mm": 19.219823837280273,
      "non_tire_lowest_z_mm": 14.800313949584961,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -10,
      "belly_lowest_z_mm": 19.370990753173828,
      "non_tire_lowest_z_mm": 14.807784080505371,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -9,
      "belly_lowest_z_mm": 19.480131149291992,
      "non_tire_lowest_z_mm": 14.811202049255371,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -8,
      "belly_lowest_z_mm": 19.588438034057617,
      "non_tire_lowest_z_mm": 14.801244735717773,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -7,
      "belly_lowest_z_mm": 19.7033634185791,
      "non_tire_lowest_z_mm": 14.801241874694824,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -6,
      "belly_lowest_z_mm": 19.7686767578125,
      "non_tire_lowest_z_mm": 14.811203002929688,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -5,
      "belly_lowest_z_mm": 19.842437744140625,
      "non_tire_lowest_z_mm": 14.807779312133789,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -4,
      "belly_lowest_z_mm": 19.91150665283203,
      "non_tire_lowest_z_mm": 14.800307273864746,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -3,
      "belly_lowest_z_mm": 19.9421329498291,
      "non_tire_lowest_z_mm": 14.802799224853516,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -2,
      "belly_lowest_z_mm": 19.981149673461914,
      "non_tire_lowest_z_mm": 14.815247535705566,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": -1,
      "belly_lowest_z_mm": 20.004186630249023,
      "non_tire_lowest_z_mm": 14.804978370666504,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 0,
      "belly_lowest_z_mm": 20.0,
      "non_tire_lowest_z_mm": 14.799999237060547,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 1,
      "belly_lowest_z_mm": 20.004186630249023,
      "non_tire_lowest_z_mm": 14.804978370666504,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 2,
      "belly_lowest_z_mm": 19.981149673461914,
      "non_tire_lowest_z_mm": 14.815247535705566,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 3,
      "belly_lowest_z_mm": 19.9421329498291,
      "non_tire_lowest_z_mm": 14.802799224853516,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 4,
      "belly_lowest_z_mm": 19.91150665283203,
      "non_tire_lowest_z_mm": 14.800307273864746,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 5,
      "belly_lowest_z_mm": 19.842437744140625,
      "non_tire_lowest_z_mm": 14.807779312133789,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 6,
      "belly_lowest_z_mm": 19.7686767578125,
      "non_tire_lowest_z_mm": 14.811203002929688,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 7,
      "belly_lowest_z_mm": 19.7033634185791,
      "non_tire_lowest_z_mm": 14.801241874694824,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 8,
      "belly_lowest_z_mm": 19.588436126708984,
      "non_tire_lowest_z_mm": 14.801244735717773,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 9,
      "belly_lowest_z_mm": 19.48012924194336,
      "non_tire_lowest_z_mm": 14.811202049255371,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 10,
      "belly_lowest_z_mm": 19.37099266052246,
      "non_tire_lowest_z_mm": 14.807784080505371,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 11,
      "belly_lowest_z_mm": 19.219825744628906,
      "non_tire_lowest_z_mm": 14.800313949584961,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 12,
      "belly_lowest_z_mm": 19.0772705078125,
      "non_tire_lowest_z_mm": 14.802799224853516,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 13,
      "belly_lowest_z_mm": 18.922761917114258,
      "non_tire_lowest_z_mm": 14.815253257751465,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 14,
      "belly_lowest_z_mm": 18.737607955932617,
      "non_tire_lowest_z_mm": 14.804980278015137,
      "lowest_part": "Wheel_Cap_L"
    },
    {
      "angle_deg": 15,
      "belly_lowest_z_mm": 18.56121826171875,
      "non_tire_lowest_z_mm": 14.799999237060547,
      "lowest_part": "Wheel_Cap_L"
    }
  ],
  "min_non_tire_z_mm": 14.799999237060547,
  "min_belly_z_mm": 18.561214447021484
}
```

## PASS — chassis_screwdriver_access
卸下身体下壳后，四个承重框架螺钉的工具操作空间

方法与范围：实际圆柱工具包络 vs 三角实体；移除下壳的服务状态。未模拟手掌/完整手柄。

```json
{
  "tool_radius_mm": 2.5,
  "tool_length_mm": 45,
  "conflicts": []
}
```

## NOT_CHECKED — all_other_screw_and_insert_tools
头部需分离承重组件并打开后壳；其余嵌件热压头、完整螺丝刀手柄和装配力尚未统一验证

方法与范围：已建真实孔和退刀/沉孔；供应商螺钉长度、嵌件外径/深度未选型，不能证明全部工具可达。

```json
{
  "assumed_clearance_mm": 3.4,
  "assumed_insert_pilot_mm": 4
}
```

## PASS — battery_removal_path
电池、托架、绑带模块向下取出

方法与范围：每 3 mm 对真实网格做 BVH/内点检查；检查拆出轨迹，不要求穿过顶部小孔。

```json
{
  "travel_mm": 90,
  "step_mm": 3,
  "removed_parts": [
    "Body_Lower_Shell"
  ],
  "prerequisites": "Disconnect battery, loosen four hanger fixings",
  "conflicts": []
}
```

## NOT_CHECKED — complete_assembly_sequence
已设计可拆壳和分模块装配顺序；未完成全零件、螺钉、线束的连续装配路径证明

方法与范围：Battery path and four chassis tool paths executed; remaining sequences conditional on selected hardware.

```json
{
  "sequence_document": "reports/assembly_and_printing.md"
}
```

## NOT_CHECKED — all_part_wall_thickness_sampling
已执行法线射线筛查，尚不足以确认每个零件的全局最薄壁合格

方法与范围：每件最多约350个面，沿内法线射线量距；孔边/锐角近掠射值不能直接判作实体最小壁厚。

```json
{
  "parts": 19,
  "report": "wall_samples.json",
  "nominal_shell_mm": 2.4
}
```

## PASS — radial_shell_wall_thickness
未截切、非螺柱区域球壳的真实径向壁厚

方法与范围：每 10° 球面方向径向射线，依次求外/内表面交点；筛除孔、切面、螺柱；容差 ±0.12 mm，另有完整最薄壁未验证项。

```json
{
  "nominal_mm": 2.4,
  "parts": [
    {
      "part": "Head_Front_Shell",
      "samples": 172,
      "min_mm": 2.397865553390404,
      "max_mm": 2.400169964573539
    },
    {
      "part": "Head_Rear_Shell",
      "samples": 233,
      "min_mm": 2.398250324792491,
      "max_mm": 2.400090595363337
    },
    {
      "part": "Body_Upper_Shell",
      "samples": 167,
      "min_mm": 2.3983518852336383,
      "max_mm": 2.400352831574807
    },
    {
      "part": "Body_Lower_Shell",
      "samples": 231,
      "min_mm": 2.3981928250144153,
      "max_mm": 2.4003696673528245
    }
  ]
}
```

## NOT_CHECKED — global_min_wall_and_self_intersection
未完成全部局部最薄壁证明及稳健全三角自交认证；导出前的闭合/法线/退化检查不能替代此项

方法与范围：Shell nominal 2.4 mm; optical bezel and trial recesses have separately documented thin regions. Require slicer inspection.

## PASS — stl_actual_export_geometry
重新读取实际导出 STL，检查闭合、非流形边、法线、退化面与尺寸

方法与范围：二进制 STL 回读，坐标焊接至 1e-5 mm，边关联计数、绕序、正体积、法向、退化三角，尺寸误差 <0.01 mm。输出数字单位 mm，无 1000 倍缩放。

```json
{
  "candidate_count": 23,
  "delivered_count": 23,
  "quarantined": [],
  "details": "export_manifest.json",
  "reread": [
    {
      "id": "Battery_Tray",
      "vertices": 914,
      "triangles": 1840,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 11133.923553556253,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Body_Lower_Shell",
      "vertices": 9745,
      "triangles": 19510,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 71822.0419313782,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Body_Upper_Shell",
      "vertices": 7702,
      "triangles": 15412,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 69331.70073424571,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Cable_Guide_-1",
      "vertices": 200,
      "triangles": 400,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 278.7100183169045,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Cable_Guide_1",
      "vertices": 200,
      "triangles": 400,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 278.71237055460574,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Controller_Mount",
      "vertices": 1544,
      "triangles": 3100,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 2473.847927729253,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Coupon_Clearance",
      "vertices": 1160,
      "triangles": 2340,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 3416.7875946261606,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Coupon_Fit_Peg",
      "vertices": 16,
      "triangles": 28,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 808.8000179926554,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Coupon_Fit_Slots",
      "vertices": 40,
      "triangles": 92,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 2812.16002380848,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Coupon_Insert",
      "vertices": 968,
      "triangles": 1952,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 4913.2935203963825,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Display_Mount_Frame",
      "vertices": 1387,
      "triangles": 2786,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 2781.692783028235,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Driver_Mount",
      "vertices": 1544,
      "triangles": 3100,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 1440.2953437964206,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Head_Bearing_Carrier",
      "vertices": 1536,
      "triangles": 3088,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 11674.356117765044,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Head_Front_Shell",
      "vertices": 7854,
      "triangles": 15708,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 26130.98569579816,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Head_Rear_Shell",
      "vertices": 8647,
      "triangles": 17298,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 36497.04178535958,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Head_Turntable",
      "vertices": 1484,
      "triangles": 2984,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 11277.939094128755,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Imu_Mount",
      "vertices": 776,
      "triangles": 1564,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 627.6461603641537,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Load_Frame",
      "vertices": 5163,
      "triangles": 10394,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 49004.47569080709,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Motor_Mount_L",
      "vertices": 1150,
      "triangles": 2304,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 5069.932246049243,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Motor_Mount_R",
      "vertices": 1150,
      "triangles": 2304,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 5069.918552478148,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Servo_Mount",
      "vertices": 940,
      "triangles": 1896,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 873.6763963103314,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Wheel_Cap_L",
      "vertices": 768,
      "triangles": 1532,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 8034.351966182408,
      "inconsistent_stl_normals": 0
    },
    {
      "id": "Wheel_Cap_R",
      "vertices": 768,
      "triangles": 1532,
      "boundary_edges": 0,
      "nonmanifold_edges": 0,
      "inconsistent_edges": 0,
      "degenerate_triangles": 0,
      "signed_volume_mm3": 8034.420928498241,
      "inconsistent_stl_normals": 0
    }
  ]
}
```

## PASS — stl_self_intersection_risk_screen
实际 STL 的非邻接三角自交风险筛查，并在回读实体上再次抽样壁厚

方法与范围：实际导出字节回读；BVH 自交筛查排除共顶点邻面。出现候选相交需再定位；采样厚度仍不等于全局最小壁厚证明。

```json
{
  "candidate_count": 23,
  "nonadjacent_overlap_pairs": 0,
  "report": "stl_surface_risk.json"
}
```

## NOT_CHECKED — snap_fit
本轮采用螺钉/嵌件候选接口，没有设计或宣称已验证卡扣；已提供配合孔、嵌件孔和间隙小样

## NOT_CHECKED — cable_dynamic_bend_pinch
4 mm 线束、14 mm 穿轴孔、服务环与导向通道已建模；真实线缆动态弯曲、夹线和疲劳未验证

```json
{
  "required_bend_radius_mm": null,
  "head_limit_deg": 60
}
```

## NOT_CHECKED — hardware_interfaces_and_power
电机/轴承/屏幕/电池/PCB/接插件均待选型；2S 只是布局概念，USB-C 不代表任意电池可直接充电

## NOT_CHECKED — mass_com_actuator_load_balance
没有真实质量、重心、力矩、轴强度、控制器与实物数据；不承诺断电自立、稳定行驶或摔倒自起

## NOT_CHECKED — slicing_and_test_print
未运行切片器/未实际试打；0.3 mm 单边间隙仅为本轮起点，须按材料与打印机校正

## PASS — same_geometry_all_views
渲染来源与同一几何一致性

方法与范围：各视图使用同一场景的相同部件网格摘要，仅变更相机、可见性和装配/爆炸帧；参数摘要与当前模型匹配。

```json
{
  "views": [
    "front",
    "side",
    "rear",
    "top",
    "bottom",
    "exploded",
    "internal",
    "engineering",
    "engineering_gap_detail",
    "45_assembled"
  ],
  "records": 10,
  "report": "render_run.json"
}
```

## PASS — repeatable_owned_only_rebuild
同一 Blender 进程重建两次，验证对象不堆积且保留无关对象

```json
{
  "status": "PASS",
  "runs": [
    {
      "iteration": 1,
      "tagged_objects": 112,
      "part_count": 96,
      "candidate_count": 23,
      "owned_names": [
        "MORI__Battery_Hanger_0",
        "MORI__Battery_Hanger_1",
        "MORI__Battery_Hanger_2",
        "MORI__Battery_Hanger_3",
        "MORI__Battery_PLACEHOLDER",
        "MORI__Battery_Strap",
        "MORI__Battery_Tray",
        "MORI__Belt_L_ENVELOPE",
        "MORI__Belt_R_ENVELOPE",
        "MORI__Black_Bezel",
        "MORI__Bms_PLACEHOLDER",
        "MORI__Body_Insert_0",
        "MORI__Body_Insert_1",
        "MORI__Body_Insert_2",
        "MORI__Body_Insert_3",
        "MORI__Body_Lower_Shell",
        "MORI__Body_Mother_Sphere",
        "MORI__Body_Screw_0",
        "MORI__Body_Screw_1",
        "MORI__Body_Screw_2",
        "MORI__Body_Screw_3",
        "MORI__Body_Upper_Shell",
        "MORI__Cable_Guide_-1",
        "MORI__Cable_Guide_1",
        "MORI__Camera_45",
        "MORI__Charger_Regulator_PLACEHOLDER",
        "MORI__Controller_Mount",
        "MORI__Controller_PLACEHOLDER",
        "MORI__Coupon_Clearance",
        "MORI__Coupon_Fit_Peg",
        "MORI__Coupon_Fit_Slots",
        "MORI__Coupon_Insert",
        "MORI__Display_Connector_PLACEHOLDER",
        "MORI__Display_Module_PLACEHOLDER",
        "MORI__Display_Mount_Frame",
        "MORI__Display_PCB_PLACEHOLDER",
        "MORI__Driver_Mount",
        "MORI__Driver_PLACEHOLDER",
        "MORI__Encoder_L_PLACEHOLDER",
        "MORI__Encoder_R_PLACEHOLDER",
        "MORI__Eye_L",
        "MORI__Eye_R",
        "MORI__Face_Protector",
        "MORI__Fill",
        "MORI__Frame_Insert_0",
        "MORI__Frame_Insert_1",
        "MORI__Frame_Insert_2",
        "MORI__Frame_Insert_3",
        "MORI__Frame_Screw_0",
        "MORI__Frame_Screw_1",
        "MORI__Frame_Screw_2",
        "MORI__Frame_Screw_3",
        "MORI__Head_Bearing_Ball_00",
        "MORI__Head_Bearing_Ball_01",
        "MORI__Head_Bearing_Ball_02",
        "MORI__Head_Bearing_Ball_03",
        "MORI__Head_Bearing_Ball_04",
        "MORI__Head_Bearing_Ball_05",
        "MORI__Head_Bearing_Ball_06",
        "MORI__Head_Bearing_Ball_07",
        "MORI__Head_Bearing_Ball_08",
        "MORI__Head_Bearing_Ball_09",
        "MORI__Head_Bearing_Carrier",
        "MORI__Head_Bearing_Inner_Race",
        "MORI__Head_Bearing_Outer_Race",
        "MORI__Head_Cable_Service_Loop",
        "MORI__Head_Front_Shell",
        "MORI__Head_Gear_Pitch",
        "MORI__Head_Mother_Sphere",
        "MORI__Head_Pivot",
        "MORI__Head_Rear_Shell",
        "MORI__Head_Servo_PLACEHOLDER",
        "MORI__Head_Turntable",
        "MORI__Head_Wire_Through_Bore",
        "MORI__Imu_Mount",
        "MORI__Imu_PLACEHOLDER",
        "MORI__Independent_Axle_L",
        "MORI__Independent_Axle_R",
        "MORI__Key",
        "MORI__Load_Frame",
        "MORI__Motor_L_PLACEHOLDER",
        "MORI__Motor_Mount_L",
        "MORI__Motor_Mount_R",
        "MORI__Motor_Output_L",
        "MORI__Motor_Output_R",
        "MORI__Motor_R_PLACEHOLDER",
        "MORI__Pulley_L_Axle",
        "MORI__Pulley_L_Motor",
        "MORI__Pulley_R_Axle",
        "MORI__Pulley_R_Motor",
        "MORI__Rim",
        "MORI__Servo_Gear_Pitch",
        "MORI__Servo_Mount",
        "MORI__Servo_Output",
        "MORI__Studio_Ground",
        "MORI__Switch_PLACEHOLDER",
        "MORI__Tire_L",
        "MORI__Tire_R",
        "MORI__Usb_PLACEHOLDER",
        "MORI__Wheel_Bearing_L_Inner",
        "MORI__Wheel_Bearing_L_Outer",
        "MORI__Wheel_Bearing_R_Inner",
        "MORI__Wheel_Bearing_R_Outer",
        "MORI__Wheel_Cap_L",
        "MORI__Wheel_Cap_R",
        "MORI__Wheel_Hub_L",
        "MORI__Wheel_Hub_R",
        "MORI__Wheel_L_Pivot",
        "MORI__Wheel_R_Pivot",
        "MORI__Yaw_Stop_Fixed_-1",
        "MORI__Yaw_Stop_Fixed_1",
        "MORI__Yaw_Stop_Flag"
      ],
      "unrelated_preserved": true
    },
    {
      "iteration": 2,
      "tagged_objects": 112,
      "part_count": 96,
      "candidate_count": 23,
      "owned_names": [
        "MORI__Battery_Hanger_0",
        "MORI__Battery_Hanger_1",
        "MORI__Battery_Hanger_2",
        "MORI__Battery_Hanger_3",
        "MORI__Battery_PLACEHOLDER",
        "MORI__Battery_Strap",
        "MORI__Battery_Tray",
        "MORI__Belt_L_ENVELOPE",
        "MORI__Belt_R_ENVELOPE",
        "MORI__Black_Bezel",
        "MORI__Bms_PLACEHOLDER",
        "MORI__Body_Insert_0",
        "MORI__Body_Insert_1",
        "MORI__Body_Insert_2",
        "MORI__Body_Insert_3",
        "MORI__Body_Lower_Shell",
        "MORI__Body_Mother_Sphere",
        "MORI__Body_Screw_0",
        "MORI__Body_Screw_1",
        "MORI__Body_Screw_2",
        "MORI__Body_Screw_3",
        "MORI__Body_Upper_Shell",
        "MORI__Cable_Guide_-1",
        "MORI__Cable_Guide_1",
        "MORI__Camera_45",
        "MORI__Charger_Regulator_PLACEHOLDER",
        "MORI__Controller_Mount",
        "MORI__Controller_PLACEHOLDER",
        "MORI__Coupon_Clearance",
        "MORI__Coupon_Fit_Peg",
        "MORI__Coupon_Fit_Slots",
        "MORI__Coupon_Insert",
        "MORI__Display_Connector_PLACEHOLDER",
        "MORI__Display_Module_PLACEHOLDER",
        "MORI__Display_Mount_Frame",
        "MORI__Display_PCB_PLACEHOLDER",
        "MORI__Driver_Mount",
        "MORI__Driver_PLACEHOLDER",
        "MORI__Encoder_L_PLACEHOLDER",
        "MORI__Encoder_R_PLACEHOLDER",
        "MORI__Eye_L",
        "MORI__Eye_R",
        "MORI__Face_Protector",
        "MORI__Fill",
        "MORI__Frame_Insert_0",
        "MORI__Frame_Insert_1",
        "MORI__Frame_Insert_2",
        "MORI__Frame_Insert_3",
        "MORI__Frame_Screw_0",
        "MORI__Frame_Screw_1",
        "MORI__Frame_Screw_2",
        "MORI__Frame_Screw_3",
        "MORI__Head_Bearing_Ball_00",
        "MORI__Head_Bearing_Ball_01",
        "MORI__Head_Bearing_Ball_02",
        "MORI__Head_Bearing_Ball_03",
        "MORI__Head_Bearing_Ball_04",
        "MORI__Head_Bearing_Ball_05",
        "MORI__Head_Bearing_Ball_06",
        "MORI__Head_Bearing_Ball_07",
        "MORI__Head_Bearing_Ball_08",
        "MORI__Head_Bearing_Ball_09",
        "MORI__Head_Bearing_Carrier",
        "MORI__Head_Bearing_Inner_Race",
        "MORI__Head_Bearing_Outer_Race",
        "MORI__Head_Cable_Service_Loop",
        "MORI__Head_Front_Shell",
        "MORI__Head_Gear_Pitch",
        "MORI__Head_Mother_Sphere",
        "MORI__Head_Pivot",
        "MORI__Head_Rear_Shell",
        "MORI__Head_Servo_PLACEHOLDER",
        "MORI__Head_Turntable",
        "MORI__Head_Wire_Through_Bore",
        "MORI__Imu_Mount",
        "MORI__Imu_PLACEHOLDER",
        "MORI__Independent_Axle_L",
        "MORI__Independent_Axle_R",
        "MORI__Key",
        "MORI__Load_Frame",
        "MORI__Motor_L_PLACEHOLDER",
        "MORI__Motor_Mount_L",
        "MORI__Motor_Mount_R",
        "MORI__Motor_Output_L",
        "MORI__Motor_Output_R",
        "MORI__Motor_R_PLACEHOLDER",
        "MORI__Pulley_L_Axle",
        "MORI__Pulley_L_Motor",
        "MORI__Pulley_R_Axle",
        "MORI__Pulley_R_Motor",
        "MORI__Rim",
        "MORI__Servo_Gear_Pitch",
        "MORI__Servo_Mount",
        "MORI__Servo_Output",
        "MORI__Studio_Ground",
        "MORI__Switch_PLACEHOLDER",
        "MORI__Tire_L",
        "MORI__Tire_R",
        "MORI__Usb_PLACEHOLDER",
        "MORI__Wheel_Bearing_L_Inner",
        "MORI__Wheel_Bearing_L_Outer",
        "MORI__Wheel_Bearing_R_In
… 完整记录见 validation.json。
```
