# MORI Gateway

本地 `.venv/bin/python -m backend.run`，只监听127.0.0.1:8765。模拟设备同协议运行。
生产从同域HTTPS加载控制台，默认使用该域API；手机填写经过认证的HTTPS域。HTTP只容许本机回环开发。
WebSocket第一条消息携带独立可撤销凭证，后续每消息验权；查询串不放token。Origin允许列表独立配置。
配对碼在服务端600秒内单次有效，5次错误后需重启重新生成。当前CLI/code流程仅为开发绑定；实机物理按钮配网仍未绑定硬件。

设备命令在 `/ws` 或 `/api/command` 走 MORI/2。`/xiaozhi/v1` 是独立小智v1 Opus适配，使用Authorization header，
支持hello/listen/abort、16kHz单声道60ms输入和24kHz输出；拒绝MCP/未知工具。Token须有interaction权限。
MORI动作仍走本机租约；不会因语音/图像文字给予任意运动授权。

## 腾讯云配置与部署

当前未提供服务器访问资料，**没有登录、部署或改防火墙**。先在用户已授权的服务器手动运行 `tools/probe-server.sh`。
起步评估配置为2核、2GB RAM、10GB可用盘，仅是轻量适配/SQLite估算，不是承载多人/视频的性能承诺，不要求GPU。

1. 构建网页 `pnpm build`；复制 `.env.example` 为 `.env`，权限600，设置真实域名与Origin。
2. 默认MORI_PROVIDER=mock。明确启用腾讯云时填服务端SecretId/Key、地域、模型、音色、月调用上限。
   空预算禁止真实服务调用；没有自动充值。预算已持久化，重启不会重置当月计数；失败调用也先占额度，价格未知记NULL，须对账实际账单。
3. 服务器已确认资源/域名/端口后才运行 `docker compose -f backend/compose.yaml up --build -d`。
   容器镜像tag+digest锁定，Caddy提供HTTPS/WSS，gateway只在Compose内部暴露端口。
4. `/health`检查、持久卷mori-data、独立撤销凭证、Caddy证书卷均有配置。Compose本机未运行（无Docker），部署仍NOT_TESTED。

ASR / Hunyuan LLM / TTS各自SDK适配；按需VLM单独HTTPS接口，不能把某一网页会员当API。
默认自然普通话、简洁友好，音色可配置，不模仿具体真人。所有服务异常应呈现REJECTED/错误，不回退成虚假的真实支持。
目前半双工，设备级AEC、离线唤醒漏检/误触发、真实打断、嘈杂环境与时延待测；Mock不计入云成功率。

## 记忆与恢复

SQLite迁移v1 + FTS5 + 中文字面检索，用户/设备双重作用域。类别含事实、偏好、摘要、推断；推断不能自动升级为事实。
必须明确确认、来源ID非空；纠正保留冲突记录；关闭后不读取/新增，仍可删除/导出。
删除重建索引、清正文/冲突/结果缓存，VACUUM，并追加独立删除清单。数据库正文没有独立摘要缓存可残留。
原始录音/视频不写磁盘；用户上传或前端导出文件由用户管理。

```sh
.venv/bin/python -m backend.backup backup --data .state --backups .state/backups
.venv/bin/python -m backend.backup prune --backups .state/backups
# 先停止gateway，删除清单必须独立保留，再恢复指定快照：
.venv/bin/python -m backend.backup restore --data .state --snapshot .state/backups/具体快照.sqlite --gateway-stopped
```

备份保留7天，`prune`由管理员安排执行；本任务没有创建定时任务或远程自动化。恢复必须重放当前删除清单，
不能用旧快照复活已经删除的事实。凭证库不从旧备份恢复，避免复活撤销凭证。恢复/重启/隔离/冲突/删除有实际测试。

日志含命令ID、设备单调时钟、结果码与性能，不输出服务密钥或原始音视频。当前个人原型不包含账户社交、支付或自动回充。
