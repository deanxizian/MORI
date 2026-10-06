from pathlib import Path
import json,hashlib,zipfile,re
R=Path(__file__).resolve().parents[1];p=R/'handoff/软件调试任务提示词.md';s=p.read_text().replace('HW-SW-0.2','HW-SW-0.4').replace('HW-SW-0.3','HW-SW-0.4')
a=s.index('- 两轮主候选：') if '- 两轮主候选：' in s else s.index('- 两轮候选：');b=s.index('- 驱动：',a)
s=s[:a]+'''- 两轮主候选：Pololu #4863，25D MP 12V、精确减速比20.4086667:1（22³×23/(12×10³)）、48 CPR编码器。2S电压驱动，必须保留0.39Ω限流。当前实体体积+器件质量预算约1.0 kg；Pololu #5216小电机已撤回主推荐，不能沿用旧参数。
- 编码器：每电机转48计数，已经包含A/B双通道全部边沿x4；减速器输出979.616计数/转。暂定带传动1:1，每计数 π×0.095/979.616≈0.00030466 m。不得再乘4。PCNT两单元、每单元两通道；低速测速使用8帧时间窗口。
- 新编码器必须使用3.5–20V供电，选DEVKIT_5V供电（USB诊断时也可用）；A/B输出0～Vcc，不能直接接ESP32！每条A/B先过3.3V供电的SN74LVC14AD（输入容忍5.5V）。A/B同时反相不改变相序，实际方向仍必须实测。接线表的J4/J5是自定义XH6重压端子线序，不等于原厂六针排母线序。
'''+s[b:]
s=re.sub(r'(?:版本0\.[34]已更新电机计数常量，)*你仍需复现自己的版本。','版本0.4已更新电机计数常量，你仍需复现自己的版本。',s)
p.write_text(s)
files=[R/'pinmap.csv',R/'wiring.csv']
for folder in ['firmware','tests']:
 for f in (R/folder).rglob('*'):
  if f.is_file() and f.name!='sdkconfig.old' and f.suffix!='.pyc' and not any(x in f.relative_to(R).parts for x in ['build','managed_components','.DS_Store','__pycache__']):files.append(f)
m={}
with zipfile.ZipFile(R/'handoff/firmware_baseline.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(files):
  rel=str(f.relative_to(R));z.write(f,rel);m[rel]=hashlib.sha256(f.read_bytes()).hexdigest()
(R/'handoff/baseline_manifest.json').write_text(json.dumps({'version':'HW-SW-0.4','date':'2026-09-21','physical_validation':'NOT_TESTED','sha256':m},indent=2)+'\n')
(R/'handoff/CHANGELOG.md').write_text('''# HW-SW-0.4 — 2026-09-21

累积取代0.2/0.3：根据已提供的Blender体积重新估算质量，轮电机主选改为Pololu4863 25D MP12V 20.4086667:1。轮端x4计数从1204.44改为979.616。GPIO不变。编码器5V供电、A/B经SN74LVC14AD转为3.3V；不再使用小电机SH6线束。轮子仍是1:1皮带传动独立轴。USB调试前拔J12逻辑降压模块线束，J14保持连接使USB能供编码器5V；不再拔J14。母线吸能R14从24.3k改25.5k0.1%，GPIO与软件故障阈值不变。主机测试脚本改为位置相对，可在快照副本运行。其他软件接口和安全状态语义保持。

如果软件任务已经复制0.2/0.3，请按并行软件更新提示.md合并参数/接线说明，保留已完成的软件修改；重新构建并运行测试。ICR-001中把979.616改回1204.44的提案针对旧电机，当前4863不采用。不得把电机CPR与齿轮比硬编码在多个文件。
''')
print('Updated HW-SW-0.4 snapshot')
