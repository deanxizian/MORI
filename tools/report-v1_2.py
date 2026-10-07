"""Summarize recorded local runs; never turn a host result into hardware evidence."""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
from git_metadata import project_git

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/v1_2'
RUNS = [
    ('contracts_generate', '协议生成一致性'),
    ('typescript', 'TypeScript核心4项'),
    ('python_release', 'Python协议/模拟/后端/记忆/音频'),
    ('native', 'V1运动与音频C核心'),
    ('motion_final_sources', 'V1.2运动C核心2430断言；ASan/UBSan'),
    ('unitree_reference_final', '41组合成命令对照官方C；并非实物报文'),
    ('eyes_360', '360×360双眼240帧主机渲染'),
    ('legacy_host', '旧台架C：163+2211+22+10断言及回归'),
    ('legacy_python', '旧软件24项Python'),
    ('format_release', '网页/TS格式'),
    ('web_release', 'Vue类型检查与生产构建'),
    ('browser_release', '桌面/手机尺寸Chromium端到端2项'),
    ('stm32_final_sources', 'STM32F413禁驱启动镜像'),
    ('interaction_final', 'ESP32-S3微雪依赖/板级API/双眼固件'),
    ('legacy_firmware', '旧ESP32台架固件保留构建'),
    ('command_replay', '6帧SIMULATED命令回放'),
    ('replay_s288', '2帧SIMULATED S288离线回放'),
    ('dynamics_v1_2', '8类ASSUMED动力学工况'),
]

checks = []
for name, description in RUNS:
    directory = OUT / 'runs' / name
    command = json.loads((directory / 'command.json').read_text())
    digest = hashlib.sha256((directory / 'output.log').read_bytes()).hexdigest()
    if digest != command['log_sha256']:
        raise SystemExit('log hash mismatch: ' + name)
    checks.append({'id': name, 'description': description, 'source': 'HOST',
                   'status': command['status'], 'command_record': str((directory / 'command.json').relative_to(ROOT)),
                   'log': str((directory / 'output.log').relative_to(ROOT)), **command})

profile = json.loads((ROOT / 'contracts/software_profile.json').read_text())
python_count = int(re.search(r'(\d+) passed', (OUT / 'runs/python_release/output.log').read_text()).group(1))
eyes = json.loads((OUT / 'runs/eyes_360/output.log').read_text())
matrix = [
    ('共享契约、身份/租约/权限、CRC/截断/超长/重复/乱序/重启', 'PASS', 'HOST / SIMULATION', 'PASS', 'NOT_TESTED', 'C/TS/Python及37项原回归+6项动力学扩展；不代表UART物理层'),
    ('STOP_MOTION、失联撤目标、故障锁存、人工ACK/复位', 'PASS', 'HOST / SIMULATION', 'PASS', 'NOT_TESTED', '健康STOP继续平衡；FAULT请求外部禁驱，接受倒下'),
    ('S288编码/CRC/单位/齿比/镜像/回绕、TC释放和有界轮询', 'PASS', 'HOST', 'PASS', 'NOT_TESTED', '官方C合成向量差分；真实抓包、6Mbps时钟及停止语义未测'),
    ('SCS反馈、标定、有限轨迹、联合可达域接口', 'PASS', 'HOST', 'PASS', 'NOT_TESTED', '机械签字的region/零点/比例/方向尚未提供；负载温度阈值待定'),
    ('ICM身份/SI解码/安装矩阵与时序统计', 'PASS', 'HOST', 'PASS', 'NOT_TESTED', 'SPI初始化/量程滤波/DRDY调度及板接线尚未接通'),
    ('新STM32固件构建与板级接通', 'BLOCKED', 'HOST', 'PASS', 'BLOCKED', '可构建安全启动镜像；DMA/SPI端口、实时调度、命令桥和外部禁驱待释放板契约后接入'),
    ('微雪/ST77916/codec/CH32/OV3660依赖与适配器构建', 'PASS', 'HOST', 'PASS', 'BLOCKED', '物理门全关；FPC、初始化序列、音频槽/时钟/参考路由未释放'),
    ('黑底双眼确定性、圆形裁切、过渡和360分辨率', 'PASS', 'HOST', 'PASS', 'NOT_TESTED', '主机耗时不是ESP帧率；屏幕实际输出尚未测试'),
    ('供电能力/头部惯量/延迟/饱和/死区/噪声/轮滑模型', 'PASS', 'SIMULATION', 'PASS', 'NOT_TESTED', 'ASSUMED加速度输入；不能当S288扭矩辨识、实机参数或续航证据'),
    ('网页绑定、遥控、表情、记忆、语音mock和相机模式', 'PASS', 'HOST / SIMULATION', 'PASS', 'NOT_TESTED', '桌面及手机尺寸Chromium；非实体手机、非实机机器人'),
    ('SQLite跨重启/作用域/纠正/删除/备份恢复', 'PASS', 'HOST', 'PASS', 'NOT_APPLICABLE', '临时测试数据库；没有清空用户数据库或上传用户记忆'),
    ('语音适配、Opus/有界队列、播放时钟/打断确认', 'PASS', 'HOST / SIMULATION', 'PASS', 'NOT_TESTED', '有源码/主机链路；mock不是中文ASR/TTS成功'),
    ('自定义中文唤醒、物理AEC、噪声下误唤醒/漏检', 'BLOCKED', 'HARDWARE', 'NOT_TESTED', 'NOT_TESTED', '模型/许可/真实麦克风与播放参考/声学测试缺失'),
    ('像素输入、头部坐标、选定目标/丢失/陈旧/多目标停走', 'PASS', 'HOST / SIMULATION', 'PASS', 'NOT_TESTED', '确定像素夹具及输入管线；设备视觉算力/曝光/人体泛化未验证'),
    ('主动短距离/底盘跟随/有限巡游及取消', 'PASS', 'SIMULATION', 'PASS', 'BLOCKED', '本地有界状态机已运行；真实自主移动未解锁'),
    ('Compose、TLS/WSS配置、云服务适配、凭证与用量', 'PASS', 'HOST', 'PASS', 'NOT_TESTED', '配置/认证/预算核心经过测试；没有Docker引擎/授权腾讯云地址，容器与远程部署未运行'),
    ('相机+显示+音频+Wi-Fi/温升功耗并发', 'BLOCKED', 'HARDWARE', 'NOT_TESTED', 'NOT_TESTED', '没有设备实测；不能用依赖编译替代压力测试'),
    ('受保护平衡、受控地面移动、60分钟混合续航', 'BLOCKED', 'HARDWARE', 'NOT_TESTED', 'NOT_TESTED', '没有实机，不能声称已经自平衡站立'),
    ('App工程/移动端构建', 'NOT_APPLICABLE', 'HOST', 'NOT_APPLICABLE', 'NOT_APPLICABLE', '用户要求只做网页，保留已有工程，当前暂停'),
    ('远端CI runner实际执行', 'NOT_TESTED', 'REMOTE_CI', 'NOT_TESTED', 'NOT_APPLICABLE', '工作流文件不代表已执行；此生成器未查询远端运行证据'),
]
fields = ['feature', 'implementation_status', 'source', 'unit_simulation_status', 'hardware_status', 'boundary']
blockers = [
    '运动实际板型、GPIO/DMA/USART/SPI/DRDY、时钟容差、物理禁驱和急停链仍NOT_FOR_WIRING。',
    'S288 IDs/轮符号/外部传动比、允许扭矩/热、timeout/mode0/零扭矩真实行为；官方字段差异需抓包核对。',
    '3S成品电池/回灌钳位/供电测量与保护阈值；12.6V满充假设没有回灌余量。旧2S阈值不继承。',
    '头部零点/方向/联合范围/负载温度门、IMU安装和滤波、质量重心、相机内外参和曝光延迟。',
    'CAM33700/LCD35079 FPC接触面/16–18脚/初始化序列，音频PCM槽/时钟/AEC参考、实体按钮接线。',
    '提供授权设备与台架条件后，按断电→禁驱限流→单模块→悬空单轮→双轮回灌急停→辨识→保护平衡→受控移动推进。',
]
report = {
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'software_version': profile['software_version'], 'parameter_version': profile['parameter_version'],
    'scope': 'V1.2软件基线；web only；本机模拟/主机验证，非整机验收',
    'local_checks_status': 'PASS' if all(c['status'] == 'PASS' and c['exit_code'] == 0 for c in checks) else 'FAIL',
    'hardware_status': 'NOT_TESTED', 'physical_release': False,
    'project_git': project_git(ROOT),
    'counts': {'python': python_count, 'motion_assertions': 2430, 'unitree_synthetic_vectors': 41, 'typescript_tests': 4, 'browser_tests': 2, 'legacy_python': 24, 'legacy_c_assertions': 2406},
    'eyes_host_benchmark': eyes, 'matrix': [dict(zip(fields, row)) for row in matrix],
    'runs': checks, 'hardware_and_integration_blockers': blockers,
    'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['MORI_SPEC_V1_2.md', 'software/inputs/v1_2/03_CODEX_SOFTWARE.md']},
    'milestones': {
        'S1': {'status': 'PASS', 'source': 'HOST / SIMULATION', 'detail': '协议、模拟、双眼及本地网页链路'},
        'S2': {'status': 'BLOCKED', 'build': 'PASS', 'detail': '两域可构建；物理端口及台架运行未接通，不能标完整S2通过'},
        'S3': {'status': 'BLOCKED', 'local_backend_memory_mock': 'PASS', 'detail': '真实中文语音/自定义唤醒/云部署未验证；App NOT_APPLICABLE'},
        'S4': {'status': 'PASS', 'source': 'SIMULATION', 'hardware': 'BLOCKED', 'detail': '像素输入及有界行为路径通过；不等于真实人跟随'},
        'S5': {'status': 'NOT_TESTED', 'source': 'HARDWARE'},
    },
}
(OUT / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
lines = [
    '# MORI V1.2 软件验收记录', '',
    f"软件 {profile['software_version']}；参数 {profile['parameter_version']}；记录 {report['recorded_utc']}。",
    '', f"**本地软件检查 {report['local_checks_status']}；实机 NOT_TESTED；实机使能 BLOCKED。尚不能声称机器人可自平衡站立。** App 按用户要求暂停。", '',
    '用户附件作为V1.2需求；保留更晚的网页限定。机械/电气真源由并行任务维护，读取V1.2-H0.1/V1.2-M1后合并软件契约，不改硬件/机械/params。未提供的模板/交接/REFERENCES未冒称已读。', '',
    '## 实际通过的检查', '',
    f'- V1.2运动核心2430条ASan/UBSan断言；41组官方C合成协议差分；Python {python_count}项；TS 4项；浏览器2项。',
    '- 旧台架2406条C断言、4个命名回归及24项Python仍通过；原固件构建保留。数量来自各自日志，不把断言数当独立测试数。',
    '- STM32F413、微雪ESP32-S3两个目标实际编译成功；前者仅安全启动镜像，无已接通的物理控制调度。后者已编译ST77916/codec/CH32/相机API，物理门保持关闭。',
    f"- 360×360主机240帧：p50 {eyes['p50_us']} µs，p95 {eyes['p95_us']} µs，p99 {eyes['p99_us']} µs，最大 {eyes['max_us']} µs；帧缓冲 {eyes['framebuffer_bytes']} B。仅HOST，不是ESP实测。", '',
    '## 功能与证据矩阵', '',
    '| 功能 | 实现 | 验证来源 | 单元/仿真 | 实物 | 限制 |',
    '|---|---|---|---|---|---|',
]
lines += ['| ' + ' | '.join(row) + ' |' for row in matrix]
lines += ['', '## 可运行命令与真实日志', '', '从工程根目录执行。启动与依赖安装见 [README_SOFTWARE_V1_2.md](../../README_SOFTWARE_V1_2.md)。每条记录包含实际argv、cwd、UTC、耗时、退出码和日志SHA256。所有本轮最终选用记录退出码0；早期FAIL日志仍保留，未抹掉。', '', '| 检查 | 结果 | 记录 | 输出 |', '|---|---|---|---|']
lines += [f"| {c['description']} | {c['status']} | [命令](runs/{c['id']}/command.json) | [日志](runs/{c['id']}/output.log) |" for c in checks]
lines += ['', '```sh', '.venv/bin/python -m backend.run', 'bash tools/node-env.sh dev', '# 浏览器打开 http://127.0.0.1:5173 ，用 .state/pairing.txt 配对', '.venv/bin/python tools/verify-v1_2.py', 'bash tools/build-firmware.sh motion', 'bash tools/build-firmware.sh interaction', '```', '',
    '## 修复与保留的失败证据', '',
    '- S288 Kp/Kd采用有符号16位范围，先复现超界被误接收再修复：regression_gain_signed_before → motion_final_sources。',
    '- 头轨迹到点速度跳变超出加速度界限：regression_head_accel_before → regression_head_accel_after，并保留1000步中断/到点验证。',
    '- /health旧版本：regression_version_before → python_release；首帧HTTP409浏览器错误：regression_camera_pending_before/browser_final → python_release/browser_release。修复为相机开启时HTTP204等待首帧；没有忽略控制台错误。',
    '- STM32首次链接/头文件配置问题已修复并实际重编译，stm32_first/stm32_flash_fix等日志为历史失败，最终以stm32_final_sources为准。早期浏览器服务未启动的FAIL也保留。',
    '- 第三方警告：Starlette/anyio弃用别名、官方CRC头unused静态函数、Playwright终端颜色环境提示。最终网页JS错误和console error/warning均为0；没有为消除警告升级未审查依赖。', '',
    '## 仍需硬件与实物证据', '',
]
lines += ['- ' + item for item in blockers]
lines += ['', '新3S数值保护路径尚待测量适配；新运动核心目前接收power_ok/low_battery等HAL健康输入。旧ADC/NTC/nFAULT故障注入的PASS只属于旧台架，不应冒充新S288硬件已验证。新STM32尚需板端口、DRDY/滤波、实际调度和物理命令桥接入，详细列在[软件入口](../../README_SOFTWARE_V1_2.md)和[调试手册](../../docs/debug_manual_v1_2.md)。', '',
    '## 版本、许可与追溯', '',
    '实际环境见 [environment.json](environment.json)；源/固件/日志哈希见 [file_manifest.json](file_manifest.json)。当前生成器记录实际 Git HEAD 与工作区状态，见 acceptance.json 的 project_git；历史运行日志仍保留各自日期和输入，不等于本次全部重测。第三方仓库使用锁定commit。Arm14.2.Rel1下载摘要与校验见arm_toolchain.json/arm_download.json。',
    'ESP-IDF维持5.5.2、LVGL9.2.2、ESP-SR2.2.0；camera2.0.16→2.1.4为明确兼容变更，新增ST77916 1.0.1、codec1.5.4、CH32 1.0.1。升级前lock/config已归档。许可与逐文件来源见 [THIRD_PARTY_V1_2.md](../../software/THIRD_PARTY_V1_2.md)，宇树参考不改标MIT。', '',
    '阶段：S1 PASS；S2构建PASS/板级运行BLOCKED；S3本地后端和记忆PASS/真实语音与部署未验证；S4 SIMULATION PASS/实机BLOCKED；S5 NOT_TESTED。远端CI未运行，App NOT_APPLICABLE。', '',
    '网页验收、尺寸、交互范围和截图见 [design/qa.md](design/qa.md)。所有实机实时性最大值、电流/温度、旋转、负载、自由平衡和60分钟混合续航均NOT_TESTED；没有串口连接、烧录或云部署。', '',
]
(OUT / 'acceptance.md').write_text('\n'.join(lines))
print(json.dumps({'local_checks': report['local_checks_status'], 'python_tests': python_count, 'recorded_runs': len(checks), 'hardware': 'NOT_TESTED'}, ensure_ascii=False))
if report['local_checks_status'] != 'PASS':
    raise SystemExit(1)
