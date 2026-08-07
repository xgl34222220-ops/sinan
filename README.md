# 天机 · 开奖概率实验室

天机是一套由 **Android App、FastAPI 云端、SQLite 前向档案和 FCM / Telegram 推送**组成的开奖数据分析实验项目。所有预测都必须在目标期开奖前冻结，并在对应期号开奖后结算；随机开奖不可可靠预测，本项目不承诺准确率、收益或必中。

## 当前版本

- 当前正式版：**6.6.0**
- 发布策略：默认仅发布正式稳定版；只有明确测试需求时才使用 Alpha、Beta 或 RC
- Android：Kotlin、Jetpack Compose、Material 3、Monet、WorkManager
- 服务端：FastAPI、SQLite WAL、Docker Compose、Caddy HTTPS
- 构建：Java 17、Gradle 8.13、Android SDK 36
- 正式应用 ID：`com.tianji.probabilitylab.nativev5`

## v6.6 Dynamic AI v2

- 正式服务端 AI 预测全面切换到 Dynamic AI v2，不再使用固定 `235780` 运行时覆盖、结算改写或输出保护。
- 移除“AI 必须故意与本机预测不同”的旧约束；AI 与本机统计独立计算，结果一致时允许自然一致。
- 修复名次概率与号码概率都为 10 维时被误判为同一向量类型、导致聚合串线的问题。
- AI 继续采用匿名多 reviewer 评审，并分别对“位置排名”和“号码排名”生成动态 Top6 / Top7 候选。
- 加入按真实已结算样本进行的 walk-forward 统计校准，位置层和号码层均有独立前向先验。
- AI reviewer 与统计先验根据 LogLoss、Brier、Top6 等真实结算指标持续调权，不再依赖固定目标的历史权重。
- 新学习状态隔离到 `ai_v2_position_X:*`，旧 fixed-target / legacy 权重不会继续污染 v2。
- 服务端回归测试覆盖动态候选、冻结历史预测、AI 前缀缓存和持续学习契约。
- v6.6.0 Release 成功后，Production 服务端会同步部署同一 `main` 提交并重建 `api + worker`，通过 `/health` 后才视为上线完成。

## v6.5 UI Final Polish

- 首页继续以“实时开奖 / 倒计时 → 本期预测 → AI 判断 → 概率 / 模型详情”为主层级，正常同步状态进一步降噪，异常时才展开详细来源提示。
- AI 联合判断新增“高度一致 / 主判断明确 / 存在分歧”与票数分布，可直接看到主要位置的模型支持度。
- 手机悬浮 Dock 使用滑动 Liquid 选中胶囊；Header 刷新改为自然旋转反馈，按压与触觉反馈继续保留。
- 通知中心在 FCM 正常时收起重复连接状态，仅在降级或异常时重点提示，并提供筛选计数与快速清除。
- 档案页增加今天 / 昨天 / 日期分组、Sticky 搜索筛选、渐进加载；工程 Hash 默认不再占用普通卡片空间。
- 设置入口加入轻量语义色；设置与 AI 对话采用最低可读字体比例托底，不再对系统大字体做二次乘法放大。
- 服务端管理台继续把系统健康与实时开奖链路放在首要位置，异常彩种优先展示，并区分开奖发现、探测请求与写库结算耗时。
- 控制台手机端统一状态、延迟、趋势和底栏文字的可读下限，并用统一视觉 token 收口圆角、间距和字号漂移。
- Android CI 补充 360dp 小屏、浅色首页、档案、推送降级和设置语义配色截图回归；服务端 CI 继续保护控制台与实时链路契约。
- 保留 v6.1.4 以来的实时开奖快通道、异步 FCM / Telegram 与当前彩种快速刷新；服务端固定 `235780` 输出保护已由后续 Dynamic AI v2 退役，本地 native 动态预测逻辑保持独立。

## v6.1 稳定化基础

- 推送升级到 **Push Protocol v2**：预测完成、两期预警、三期加强、后续升级和恢复命中使用统一事件字段。
- FCM 与 App 预警中心直接采用服务端标题和正文，不再把“两期预警”误显示为“三期不中”。
- App 改为 `after_id` 增量同步，系统通知分为普通更新和风险预警两个频道。
- 设备密钥迁移到 Android Keystore；旧明文密钥首次读取时自动迁移。
- 服务端引入可重复执行的数据库迁移、设备已读游标、事件过期时间和投递索引。
- FCM 改为受限并发投递；失败任务按时间窗口重试，无效 Token 自动清理。
- Worker 周期超时成为真正的硬边界：任务永久卡住时退出 Worker，由 Docker 拉起干净进程。
- 服务端与 App 端统一启用按真实开奖结算的持续学习，并按彩种、模型和具体名次隔离权重。
- v6.1.3 曾将预测目标统一为固定 `235780`（内部为 2/3/5/7/8/10），只比较第 1～10 名哪个位置下一期更可能进入固定集合；该方案现已作为历史实现保留，不再接入正式服务端 AI 运行链路。
- v6.1.4 新增独立实时开奖快通道：开奖窗口约 2 秒探测，结算、历史补齐、AI 与推送不再串行阻塞最新开奖发现。
- v6.1.4 App 改为最新开奖优先、历史缓存复用和当前彩种自适应刷新；服务端与 App 的 `nextIssue` 语义统一。
- v6.1.4 推送收口为单一异步投递实现，FCM 与 Telegram 并行处理；管理台开奖卡片采用 3/8/30 秒自适应轻刷新。
- AI 推理前注入该 AI 自身的真实结算和滚动前向证据，不向远端 AI 泄露本机模型最终答案。
- 早期正式预测输出边界曾强制固定 `235780`；Dynamic AI v2 已改回动态 Top6 / Top7，并以匿名 AI 评审和独立前向统计先验按真实结算成绩持续调权。
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
