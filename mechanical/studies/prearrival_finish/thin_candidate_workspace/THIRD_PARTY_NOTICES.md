# MORI V1 第三方通知

> V1.2新增STM32、Unitree/FTServo协议参考与微雪组件见 [THIRD_PARTY_V1_2.md](software/THIRD_PARTY_V1_2.md)。下文保留原V1依赖版本；不是当前camera组件版本。

这些说明记录本次软件参考、复制与链接来源，未替用户授予模型、声音、形象或商标权利。
所有参考 commit / 每个归档文件 SHA256 在 `refs/sources.lock.json`；所有归档标为参考资料，不参与编译。

| 本工程文件 | 来源文件 | 使用方式 / 许可 |
|---|---|---|
| apps/console/src/eyes/reference-face.ts | jeremy-prt/bloub src/bot/face.ts | 未修改副本 / MIT, ©2026 Jérémy Perret |
| apps/console/src/eyes/math.ts | jeremy-prt/bloub src/bot/math.ts | 未修改副本 / 同上 |
| apps/console/src/eyes/engine.ts | 上述投影与liveliness函数；MORI状态/裁切/切换新增 | 适配 / 同上，保留完整 LICENSE.bloub |
| firmware/interaction/core/eyes.c | bloub face.ts/math.ts 的投影、noise、RNG与blink | C移植 / 同上，文件头及 docs/licenses/bloub-MIT.txt |
| backend/mori/xiaozhi.py | 78/xiaozhi-esp32 docs/websocket.md | 按协议独立适配，未复制Application；源仓库MIT |
| firmware/motion/components/mori_v1/* | MORI新增；参考StackChan限位与生命周期概念 | 不含StackChan/hover源代码；不继承其整套控制参数 |
| apps/mobile/ios/*、android/* 原生模板 | @capacitor/cli7.2.0 | 生成模板，MIT；MORI另加UIScene/权限配置 |

运行依赖：Vue/Vite/TypeScript/Capacitor/Vitest/Playwright及传递依赖许可由包本身保存，版本和完整性由
pnpm-lock.yaml锁定。后端 FastAPI/Starlette/Uvicorn/httpx/PyAV/numpy/OpenCV/TencentSDK及其传递依赖
记录在 reports/v1/python_dependency_licenses.json 与 requirements.lock。PyAV源码为BSD，轮子内FFmpeg
及各编解码依赖须按随包LICENSE核验再分发；后端开发可使用，商业打包状态未声称已审完。
OpenCV内Haar模型为检测候选，不存储身份模板，也不宣称人脸身份识别已授权或实现。

固件链接 LVGL9.2.2(MIT)、esp32-camera2.0.16(Apache-2.0)、ESP-SR2.2.0(Espressif MIT，限Espressif产品)
及锁文件中的组件。完整声明留在managed_components，额外快照在docs/licenses。
原 motion 驱动继续沿用既有HW交接源与原通知；硬件快照本身未改。

rig_omni 缺少顶层明确许可，因此只阅读/分析控制路径，**没有复制**其中Hover控制代码到运行工程。
StackChan-BSP(MIT)、stack-chan(Apache-2.0)、xiaozhi-server(MIT)、ESP-WHO(Espressif MIT)是锁定参考，
未把它们的主循环混合到本工程。各参考目录的不同子模块可能有独立许可，不把仓库许可一概套给每个第三方文件。

bloub代码MIT不代表Grok/xAI角色商业形象许可。当前皮肤用于开发对照，MORI提供可替换皮肤接口；
对外商业版本应切换为有权使用的MORI原创设计。离线“你好，莫里”训练模型、声音API、腾讯云服务费用/权利
尚需单独确认；不模仿指定真人，不把网页订阅当API授权。
