# V1.2 网页验收

结果：HOST / PASS；机器人、实体手机、iOS/Android App / NOT_TESTED 或当前范围 NOT_APPLICABLE。

地址 http://127.0.0.1:5173/，标题 MORI · 控制台，页眉 MORI V1.2 / DEVELOPMENT。后端 /health 返回1.2.0-dev.1和SIMULATED；没有实机解锁。

项目Playwright测试在独立临时MORI-SIMULATED-e2e数据目录与18765端口运行；用户服务8765的SQLite记忆未作为清理对象。浏览器测试命令、退出码0与日志见 ../runs/browser_release/。另经Codex内置浏览器确认交付页显示V1.2、未知测量NOT_TESTED与驱动禁止。

| 检查 | 结果 | 证据 |
|---|---|---|
| 1440×1050桌面与390×844手机尺寸 | PASS | desktop-qa.json / mobile-chromium-qa.json |
| 844×390横向窗口、横向溢出 | PASS | 同一端到端测试中旋转后核验 |
| 非空页面、V1.2身份、无Vite错误遮罩 | PASS | 浏览器断言及截图 |
| JS异常、console error/warning | PASS，均0条 | 两个qa.json；终端颜色提示不是页面错误 |
| 配对、取得控制权、明确模拟解锁、100mm动作完成、STOP不禁驱 | PASS | 两个浏览器用例 |
| pointerup/失焦停止续租 | PASS | 两个浏览器用例；依旧仅SIMULATED |
| 相机TRACKING首帧等待、选定目标、跟随、多目标撤销 | PASS | 首帧204修复后无控制台错误 |
| 记忆新增/纠正/删除、mock对话、模拟严重故障 | PASS | 临时数据目录中的端到端用例 |
| 真机浏览器权限拒绝、实体手机后台及iOS Safari | NOT_TESTED | 当前仅本机Chromium不同尺寸 |
| 实际相机帧/真实中文声学链路/机器人运动 | NOT_TESTED | 不能用网页动画证明 |

截图已经目视检查：[桌面](desktop-console.png)、[手机尺寸](mobile-chromium-console.png)。保留既有控制台结构、黑底双眼和状态区，未改造成营销页面。新显示目标为360×360，但屏幕实际帧时/物理亮区仍未验收。

已知边界：页面显示模拟数据和实机锁定；未绑定时不会自动发运动命令，连接恢复不会重放动作。限流预览与云/浏览器时间不能冒充设备采样时间。无实机配网签字；当前一次性配对面向本机开发服务。
