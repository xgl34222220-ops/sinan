# 天机 · 开奖概率实验室

天机是一套由 **Android App、FastAPI 云端、SQLite 前向档案和 FCM / Telegram 推送**组成的开奖数据分析实验项目。所有预测都必须在目标期开奖前冻结，并在对应期号开奖后结算；随机开奖不可可靠预测，本项目不承诺准确率、收益或必中。

## 当前版本

- 当前正式版：**6.1.0**
- 发布策略：默认仅发布正式稳定版；只有明确测试需求时才使用 Alpha、Beta 或 RC
- Android：Kotlin、Jetpack Compose、Material 3、Monet、WorkManager
- 服务端：FastAPI、SQLite WAL、Docker Compose、Caddy HTTPS
- 构建：Java 17、Gradle 8.13、Android SDK 36
- 正式应用 ID：`com.tianji.probabilitylab.nativev5`

## v6.1 稳定化重点

- 推送升级到 **Push Protocol v2**：预测完成、两期预警、三期加强、后续升级和恢复命中使用统一事件字段。
- FCM 与 App 预警中心直接采用服务端标题和正文，不再把“两期预警”误显示为“三期不中”。
- App 改为 `after_id` 增量同步，系统通知分为普通更新和风险预警两个频道。
- 设备密钥迁移到 Android Keystore；旧明文密钥首次读取时自动迁移。
- 服务端引入可重复执行的数据库迁移、设备已读游标、事件过期时间和投递索引。
- FCM 改为受限并发投递；失败任务按时间窗口重试，无效 Token 自动清理。
- Worker 周期超时成为真正的硬边界：任务永久卡住时退出 Worker，由 Docker 拉起干净进程。
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

Android CI 执行单元测试、Lint、Debug APK 和 R8 Release APK 构建。服务端 CI 执行 Python 编译、单元测试、Docker Compose 校验和镜像构建。正式发布还会校验应用 ID、版本、签名和 Firebase 客户端配置。

> 天机用于统计实验、记录和真实前向验证。请理性使用，不要将任何候选结果理解为确定性结论。
