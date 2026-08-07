# 天机 v6.2.0

v6.2.0 是一次面向 UI、交互、实时链路可观测性和工程质量的完整体验重构，同时合并主线最新 AI 走势分析体系。

## Android UI / 体验

- 首页重排：实时开奖与倒计时成为第一视觉层级，本期预测与 AI 判断紧随其后，详细概率与模型信息下沉。
- 手机保留悬浮液态 Dock；宽屏和平板使用侧边 Navigation Rail，并接入 Material 3 Adaptive。
- 通知中心按日期分组，高级筛选默认收起；预测、预警、恢复等事件使用更清晰的层级与强调。
- 档案页减少横向筛选条和重复卡片，强化搜索、来源、结算状态和结果本身。
- 设置、Header、导航、卡片、字号和触摸面积统一为新的 v6.2 视觉规范。
- 浅色、深色、OLED 模式的系统栏图标与背景行为统一，改善 edge-to-edge 体验。
- 关键 Compose 页面加入 Preview Screenshot 基线，后续 UI 修改可持续检测视觉回归。

## Android 架构与刷新

- 删除依赖 Java 反射调用私有 `refreshLottery()` 的兼容桥。
- `AppController` 正式提供 `refreshCurrentLottery()`，实时推送和前台自适应刷新直接刷新当前彩种，避免 R8 处理后退化为全量刷新。
- 保留 v6.1.4 的最新开奖优先、历史缓存复用、当前彩种快速刷新与 FCM 到达后即时刷新。

## 服务端与管理台

- 管理台新增实时开奖链路卡片，直接展示：开奖发现延迟、探测请求耗时、写库/结算耗时、EMA 和历史最慢值。
- 开奖卡片继续按开奖窗口自适应快速刷新，不需要整页高频刷新。
- 服务端版本、Runtime Revision 与 Git Commit 统一展示，方便确认线上实际运行代码。
- 增加受保护的手动 VPS 部署 Workflow，可结合 GitHub Production Environment 审批使用，不会因为普通提交自动部署生产服务器。
- 保留 v6.1.4 独立 realtime worker、连接池、开奖窗口约 2 秒探测、异步结算/推送和慢任务分离架构。

## AI 与预测

- 正式 AI Top6 输出边界继续固定为 `235780`（内部 2/3/5/7/8/10），不改变该保护规则。
- 合并主线最新走势分析体系：读取最多 240 期真实开奖数据，使用 24 / 60 / 120 / 240 多窗口特征、前向验证和 AI 自身实战结算记录。
- 多路 AI 专家分别分析走势，由最终 AI 裁判给出正式名次。
- 不增加人工轮换、禁选、冷却或人为降权规则。
- 本地/native 动态预测继续保持原有逻辑，不被固定 AI Top6 规则覆盖。

## 推送与实时性

- 继续使用单一 Push Protocol v2 异步实现。
- FCM 与 Telegram 并行投递；Telegram 预警优先调度。
- App 收到相关 data-only FCM 后立即触发当前彩种刷新。
- 推送重试、冷却、失效 Token 清理和事件过期机制保持启用。

## 验证

发布前已通过：

- Android Debug / Release 单元测试
- Android Lint
- Debug APK 构建
- R8 Release APK 构建
- Compose Preview Screenshot 基线渲染
- UI / 版本 / Shell 契约检查
- 服务端 133 条单元测试
- Docker Compose 配置验证
- 服务端 Docker 镜像构建

正式 Release Workflow 还会再次校验升级签名证书、应用 ID、versionCode/versionName、Firebase 客户端配置和最终 APK 签名。
