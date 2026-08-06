# 天机 v6.1 稳定化架构

## 目标

v6.1 不继续无边界堆功能，优先统一 App、服务端和推送端的状态模型，建立可迁移、可观测、可回滚的长期结构。

## Push Protocol v2

统一字段：`schema_version`、`event_type`、`severity`、`event_key`、`collapse_key`、`deep_link`、`expires_at_epoch_ms`、`title` 和 `body`。

事件类型：

- `prediction_ready`
- `miss_prealert`
- `miss_alert`
- `miss_escalation`
- `hit_recovery`
- `service_warning`
- `system_notice`

兼容策略：

- v1 的 `prediction_miss_alert` 根据 `streak` 与 `threshold` 转成 v2；
- App 能继续读取旧历史；
- 数据库迁移补齐已有预警字段；
- FCM、轮询接口和本地历史共用同一解析器；
- 客户端直接显示服务端标题与正文，不再自行猜测预警等级。

## 投递链路

```text
预测或结算完成
  ├─ Telegram 事件物化
  ├─ 连续未命中事件物化
  └─ 统一镜像到 push_alerts
         ↓
  受限并发投递
         ├─ FCM
         └─ Telegram
         ↓
  sent / failed / retry
```

关键规则：

- 仅投递未过期事件；
- 同一 `alert_id + target` 幂等；
- 失败至少间隔 `TIANJI_PUSH_RETRY_SECONDS`；
- FCM 无效 Token 自动清空；
- 历史投递记录和失活设备由维护任务清理；
- “全部已读”使用设备 `read_through_alert_id`，不再为每条历史插入一行。

## Worker 超时

Python 无法安全终止正在执行的线程。v6.1 在周期超过 `TIANJI_WORKER_CYCLE_TIMEOUT_SECONDS` 后写入超时状态、输出结构化日志并结束 Worker 进程，由 Docker 自动拉起干净进程。

## 数据库迁移

`server/app/migrations.py` 维护单调递增版本：

- `schema_migrations` 记录已执行版本；
- 每次迁移在 `BEGIN IMMEDIATE` 事务中执行；
- 重复启动不会重复修改；
- v6.1 增加推送协议字段、已读游标和投递索引；
- 部署前仍应先生成 SQLite 一致性备份。

## Android

- FCM 与轮询共用 `PushPayloadParser`；
- `PushAlertStore` 使用 `after_id` 游标；
- 设备密钥由 Android Keystore AES/GCM 保护；
- 两个通知频道分别承载普通更新和风险预警；
- 相同 `collapse_key` 使用稳定通知 ID，升级预警更新原通知；
- 通知权限在用户打开预警中心时申请；
- 过期事件只进入历史，不弹系统通知。

## 后续模块边界

```text
presentation/
  forecast/
  archive/
  chat/
  settings/
  alerts/

domain/
  SyncLotteryUseCase
  RunAiForecastUseCase
  SettleForecastUseCase
  SyncPushEventsUseCase

data/
  LotteryRepository
  ForecastRepository
  AiRepository
  PushRepository

runtime/
  AiTaskManager
  ForegroundTaskManager
```

## 发布前回归

- Android 26、33、36；
- 前台、后台、划掉 App、断网恢复；
- FCM Token 刷新；
- 两期、三期、四期升级和恢复命中；
- 同一事件 FCM 与轮询重复到达；
- 360dp、412dp、600dp；
- 字体缩放 1.0、1.15、1.30；
- 深色、浅色、OLED、Monet；
- 旧数据库连续升级两次，第二次迁移必须为空；
- Worker 注入长任务并确认容器自动重启。
