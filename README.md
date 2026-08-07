# 天机 · 开奖概率实验室

天机是一套由 **Android App、FastAPI 云端、SQLite 前向档案和 FCM / Telegram 推送**组成的开奖数据分析实验项目。所有预测都必须在目标期开奖前冻结，并在对应期号开奖后结算；随机开奖不可可靠预测，本项目不承诺准确率、收益或必中。

## 当前版本

- 当前正式版：**6.2.0**
- 发布策略：默认仅发布正式稳定版；只有明确测试需求时才使用 Alpha、Beta 或 RC
- Android：Kotlin、Jetpack Compose、Material 3、Monet、WorkManager
- 服务端：FastAPI、SQLite WAL、Docker Compose、Caddy HTTPS
- 构建：Java 17、Gradle 8.13、Android SDK 36
- 正式应用 ID：`com.tianji.probabilitylab.nativev5`

## v6.2 UI / 体验重构重点

- 首页重排为“实时开奖 / 倒计时 → 本期预测 → AI 状态 → 深度分析”，减少重复卡片与视觉噪音。
- 手机继续使用悬浮液态 Dock，宽屏和平板自动切换侧边 Navigation Rail，并接入 Material 3 Adaptive。
- 通知中心改为按日期分组并收起高级筛选；档案页简化筛选与信息密度，设置页统一分组式信息层级。
- 统一浅色 / 深色 / OLED 系统栏表现、字号、触摸区域与组件圆角，提升可读性和无障碍体验。
- 删除当前彩种实时刷新的 Java 反射桥，改为 `AppController.refreshCurrentLottery()` 正式 API，避免 R8 下退化为全量刷新。
- 服务端管理台新增实时链路延迟卡片，直接展示开奖发现延迟、探测请求耗时、结算耗时、EMA 与历史最慢值。
- 服务端版本、Runtime Revision 与 Git Commit 统一展示，并加入受保护的手动 VPS 部署工作流。
- Android CI 新增 Compose Preview Screenshot 基线渲染，持续校验首页、导航、设置等关键界面的视觉回归。
- 保留 v6.1.4 的实时开奖快通道、异步 FCM / Telegram、当前彩种快速刷新与固定 `235780` 输出保护。
- 合并主线最新 AI 走势体系：读取最多 240 期真实数据，使用 24 / 60 / 120 / 240 窗口、前向验证和自身实战结果，由多路专家与最终 AI 裁判给出正式名次；本地 native 模型继续保持原逻辑。

## v6.1 稳定化基础

- 推送升级到 **Push Protocol v2**：预测完成、两期预警、三期加强、后续升级和恢复命中使用统一事件字段。
- FCM 与 App 预警中心直接采用服务端标题和正文，不再把“两期预警”误显示为“三期不中”。
- App 改为 `after_id` 增量同步，系统通知分为普通更新和风险预警两个频道。
- 设备密钥迁移到 Android Keystore；旧明文密钥首次读取时自动迁移。
- 服务端引入可重复执行的数据库迁移、设备已读游标、事件过期时间和投递索引。
- FCM 改为受限并发投递；失败任务按时间窗口重试，无效 Token 自动清理。
- Worker 周期超时成为真正的硬边界：任务永久卡住时退出 Worker，由 Docker 拉起干净进程。
- 服务端与 App 端统一启用按真实开奖结算的持续学习，并按彩种、模型和具体名次隔离权重。
- v6.1.3 将预测目标统一为固定 `235780`（内部为 2/3/5/7/8/10），只比较第 1～10 名哪个位置下一期更可能进入固定集合。
- v6.1.4 新增独立实时开奖快通道：开奖窗口约 2 秒探测，结算、历史补齐、AI 与推送不再串行阻塞最新开奖发现。
- v6.1.4 App 改为最新开奖优先、历史缓存复用和当前彩种自适应刷新；服务端与 App 的 `nextIssue` 语义统一。
- v6.1.4 推送收口为单一异步投递实现，FCM 与 Telegram 并行处理；管理台开奖卡片采用 3/8/30 秒自适应轻刷新。
- AI 推理前注入该 AI 自身的真实结算和滚动前向证据，不向远端 AI 泄露本机模型最终答案。
- AI 正式预测输出边界继续强制固定 `235780`，本地 native 动态预测保持原逻辑不受影响。
- README、App 版本和协议版本同步，避免发布信息继续漂移。

详细设计与回归范围：

- `docs/V6_1_STABILITY_ARCHITECTURE.md`
- `docs/UI_REGRESSION_MATRIX.md`
- `docs/FCM_SETUP.md`

## 云端与本地双保险

正常时，VPS 全天同步开奖、生成下一目标期的本机云端与可选 AI 预测，并在开奖后按准确目标期验证。Android 会读取云端冻结档案，与手机本地档案合并展示。

服务器关机或网络故障时：

- 手机仍可直连开奖接口；
- 用户自己的 API Key 仍可直连 DeepSeek、OpenAI 或兼容服务；
- 本机统计预测、SQLite 档案、持续学习和目标期验证继续可用；
- 云端请求采用短超时并降级，不阻塞首页。

## 一条命令部署

```bash
curl -fsSL https://raw.githubusercontent.com/xgl34222220-ops/tianji/main/deploy/install.sh | bash
```

常用命令：

```bash
cd /opt/tianji
docker compose ps
docker compose logs -f
docker compose up -d --build
deploy/backup.sh
```

健康检查与只读接口：

```text
GET /health
GET /health/live
GET /health/ready
GET /v1/lotteries
GET /v1/snapshot/{lottery}
GET /v1/forecasts/{lottery}
```

## FCM 与 Telegram

没有配置 FCM 时，App 仍通过 WorkManager 约每 15 分钟增量同步预警。即时推送需要同时配置 APK Firebase 参数和云端服务账号。

```bash
./tools/configure-fcm-release.sh /路径/google-services.json
sudo /opt/tianji/deploy/configure-fcm.sh /安全路径/firebase-service-account.json
```

服务端私密文件、Firebase 服务账号、`.env`、签名文件和数据库不得提交到仓库。

## 自动验证

Android CI 执行单元测试、Lint、Debug / Release APK 构建和 Compose Preview Screenshot 基线渲染。服务端 CI 执行 Python 编译、单元测试、Docker Compose 校验和镜像构建。正式发布还会校验应用 ID、版本、签名和 Firebase 客户端配置。

> 天机用于统计实验、记录和真实前向验证。请理性使用，不要将任何候选结果理解为确定性结论。
