"""Publish the bounded endpoint investigation without modifying any solids."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = HERE.parents[3]
read = lambda name: json.loads((HERE / name).read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
body = read('central_body_escape_graph.json')
yaw = read('central_yaw_escape_graph.json')
radial = read('radial_endpoint_openings.json')
unions = read('central_route_unions.json')
assert body['status'] == 'BLOCKED' and yaw['status'] == 'PASS'
assert sha(ROOT / 'mechanical/mori_v1_2.blend') == unions['source_blend_sha256']
assert all(row['status'] == 'BLOCKED' for row in radial['results'])
upper_bound = yaw['widest_grid_path_clearance_bound_mm']

review = f'''# 中心通道两端：三维出口复核

本次延续 A8 的四根细线局部研究。**完整 H06 仍为 BLOCKED；主模型、PCB 和装配动画未修改。**

![上下出口复核](endpoint_review.png)

## 已查明什么

- 在零位检查了 {len(radial['results'])} 条径向直线：下端 36 条被 Yaw_Base 阻挡，上端 72 条被 Pitch_Yoke 阻挡。只排除了这些直线。
- 原始自由空间检查不能支持“中心间隙完全封死”的结论。随后三维图搜索确实找到了上端绕行。
- 下端按身体坐标系建立有限姿态障碍物并集，搜索起点 (6.8, 0, 150) mm；目标为距轴半径 ≥30 mm 或 Z≤136 mm。本次有限图内没有找到达到目标且满足间隙的路线。满足要求的 {body['reachable_with_wire_radius_and_project_gap']['node_count']} 个连通节点限于半径5.2–14.0 mm、Z148–160 mm。搜索框顶边也是限制，**不是所有可能路线均不存在的证明**。
- 上端按随 yaw 转动的坐标系搜索，从 (6.8, 0, 182) mm 连到 Z204 mm。单条折线路径对有限姿态障碍物的中心线距离下界为 {upper_bound:.6f} mm，大于线半径加0.3 mm间隙的0.6302 mm。计入线半径后，名义表面间隙下界约 {upper_bound - yaw['wire_od_max_mm']/2:.3f} mm。
- 上端路径包含急转角；没有完成6.9342 mm保守弯曲半径、四根线同时通过、固定点、装入与CAM端连接检查。**图搜索 PASS 只指单条折线的粗细间隙，不是可加工线束 PASS。**

## 方法与边界

源为当前 M1.47 的209实体及已声明验证代理。身体段障碍物并集包含相关固定件和13个yaw/130个组合姿态的相关活动件；上端采用yaw坐标系，包含相关固定yaw件、10个pitch姿态和13个反向yaw身体姿态。裁剪盒内实际包含26/125个相关实体实例。它们是有限姿态采样，不是完整连续扫掠。

圆柱坐标图步长为径向0.4 mm、角度5°、Z0.5 mm。每条接受边的最近面距离减去覆盖项，保守覆盖整条直边；已验证的外部起点与正距离连续边防止路线穿过实体。搜索结果没有为所有连续路径提供全局上界。图中半径–高度投影会叠合不同方位，不能当成二维连续孔道。

两个端部都只以方位0°为图搜索起点；没有把这一条上端折线冒充四根线的同时通路。此前四根线各33.2 mm的中心活动段检查仍有效，但该长度不能用于供应商下料。

## 下一项实际设计工作

需要先形成能连接身体与头部、满足弯曲和装入要求的完整候选，再确定固定点及逐线长度。当前证据不足以直接在Yaw_Base或Pitch_Yoke上开孔；涉及承重座或反力件的结构变化须形成可审查候选后确认。舵盘接口和其依赖的反力件尚未定型，也会影响最终走线。

官方端子/线材资料已补齐一部分；这处卡点包含尚未完成的机械路线设计，不能全部归因于缺资料或等待实物。

## 结果与复现

- [径向直线结果](radial_endpoint_openings.json)
- [原始自由空间检查](central_void_check.json)
- [有限姿态障碍物来源](central_route_unions.json)
- [下端搜索结果](central_body_escape_graph.json)
- [上端搜索结果](central_yaw_escape_graph.json)
- [交付核对](delivery.json)

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/build_central_route_unions.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python mechanical/studies/prearrival_finish/harness_A8/check_central_escape_graph.py -- --lower
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python mechanical/studies/prearrival_finish/harness_A8/check_central_escape_graph.py -- --upper
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/plot_endpoint_review.py
```

Blender5.2.2 LTS、构建d13f752e3b9c；主模型SHA256：`{unions['source_blend_sha256']}`。没有采购、制造发布或实物资格声明。
'''
(HERE / 'ENTRY_REVIEW.md').write_text(review)

path = HERE / 'README.md'
text = path.read_text()
start = '<!-- endpoint-review:start -->'
end = '<!-- endpoint-review:end -->'
block = f'''{start}
## 后续：三维出口已检查

![上下出口复核](endpoint_review.png)

108条径向直线均未通过，但三维搜索找到了上端折线路径；在有限头部姿态实体并集内，单线中心线距离下界为{upper_bound:.3f} mm。弯曲、四线同时通过和固定尚未完成。下端在本次有限图内未找到身体出口；这不是所有路线无解的证明。完整说明见[出口复核](ENTRY_REVIEW.md)。

当前卡点包含完整机械路线尚未设计完成，不能全部归为等资料或等实物。
{end}
'''
if start in text:
    text = re.sub(re.escape(start) + '.*?' + re.escape(end), block.strip(), text, flags=re.S)
else:
    text = text.replace('## 下一步与未解决项', block + '\n## 下一步与未解决项')
text = text.replace('1. 先检查中心通道两端是否能通过现有开口侧向进出，并保持所需弯曲半径；如果需要改变承重座/反力件，先做完整候选再交用户确认。',
                    '1. 依据出口复核，继续设计完整、可弯曲并可装入的进出路线；如需改变承重座/反力件，先做完整候选再交用户确认。')
path.write_text(text)

path = HERE / 'index.html'
text = path.read_text()
block = f'''<section id="endpoint-review"><h2>三维出口复核：上端有折线，下端尚未接出</h2>
<img src="endpoint_review.png" alt="有限姿态障碍物下的出口搜索：下端未连通，上端存在尚未处理弯曲的折线路径">
<p>108条径向直线没有通过。继续三维搜索后，上端找到单线折线通路，中心线间隙下界{upper_bound:.3f} mm；弯曲、四线同时通过和固定未完成。下端在本次有限图内未找到身体出口。</p>
<p class="note">这不是所有路线无解的证明。完整机械路线仍需要设计，不能把这一项归为只能等实物；也不能把折线或33.2 mm局部长度交给供应商下料。</p>
<p><a href="ENTRY_REVIEW.md">方法、范围和下一项工作</a> · <a href="central_body_escape_graph.json">下端结果</a> · <a href="central_yaw_escape_graph.json">上端结果</a> · <a href="central_route_unions.json">实体与姿态来源</a></p></section>'''
if 'id="endpoint-review"' in text:
    text = re.sub(r'<section id="endpoint-review">.*?</section>', block, text, flags=re.S)
else:
    text = text.replace('<h2>仍需完成</h2>', block + '\n<h2>仍需完成</h2>')
text = text.replace('核对两端侧向进出、转弯空间和实际装入；涉及结构改变时另提候选确认。',
                    '完成符合弯曲与装入要求的进出路线；涉及结构改变时另提完整候选确认。')
path.write_text(text)

path = PARENT / 'work_status.json'
data = json.loads(path.read_text())
detail = ('A8细线资料及4根UART各33.2mm局部活动段已检查。后续有限姿态出口搜索：上端存在单线折线路径，尚欠弯曲和四线同时通过；下端在本次有限图内未找到身体出口，并非所有路线无解。'
          '完整进出、实际固定、俯仰段、逐线加工长度与相机完整FPC仍未完成。14根固定线和两组外圈仅为独立候选；主模型未改。')
old = next(row['detail'] for row in data['remaining'] if row['id'] == 'harness')
for row in data['remaining']:
    if row['id'] == 'harness':
        row['detail'] = detail
        row['evidence'] = 'harness_A8/index.html#endpoint-review'
data['updated_utc'] = datetime.now(timezone.utc).isoformat()
data['A8_harness_research'].update(
    scope='Independent catalogue receipt, local wire curves and finite-pose endpoint graph investigation',
    endpoint_3d_review='harness_A8/ENTRY_REVIEW.md',
    lower_endpoint_finite_graph='BLOCKED', upper_endpoint_single_polyline_clearance='PASS',
    upper_endpoint_bend_and_four_wires='NOT_TESTED', complete_UART_harness='BLOCKED')
data['prearrival_wire_addendum'].update(
    UART_lower_endpoint_finite_graph='BLOCKED', UART_upper_endpoint_single_polyline='PASS',
    UART_endpoint_bends_and_simultaneous_wires='NOT_TESTED')
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
path = PARENT / 'index.html'
text = path.read_text().replace(old, detail)
section = '<section id="harness-A8-update"><h2>A8细线与中心通道出口</h2><p><a href="harness_A8/index.html#endpoint-review">端子资料、四线局部段及三维出口复核</a>：上端有单线折线路径，下端在本次有限图内未接出；完整弯曲、固定和下料长度仍未完成。主模型未修改。</p></section>'
text = re.sub(r'<section id="harness-A8-update">.*?</section>', section, text, flags=re.S)
path.write_text(text)
print('A8_ENDPOINT_REVIEW_PUBLISHED')
if (HERE/'CRIMP_REFERENCE.md').is_file():
    import runpy
    runpy.run_path(str(HERE/'publish_crimp_review.py'),run_name='__main__')
