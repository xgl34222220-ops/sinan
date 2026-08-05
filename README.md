# 天机 · 开奖概率实验室

天机是一款面向历史开奖数据分析、候选预测和真实前向验证的 Android 应用。应用从开奖接口同步历史与目标期开奖数据，本机统计模型、可选 AI 和云端后台均以真实目标期冻结和结算。

## 当前版本

- 版本：5.9.9 App UI 与 FCM 正式推送版
- Android：原生 Kotlin + Jetpack Compose
- 服务端：FastAPI + SQLite WAL + Docker Compose + Caddy HTTPS
- 构建：Java 17、Gradle 8.13、Android SDK 36
- 正式应用 ID：`com.tianji.probabilitylab.nativev5`

## 云端与本地双保险

正常时，VPS 全天同步开奖、生成下一目标期的本机云端与可选 AI 预测，并在开奖后按准确目标期验证。Android 会读取云端冻结档案，与手机本地档案合并展示。

服务器到期、关机或网络故障时，App 不会失效：

- 手机仍可直连开奖接口；
- 用户自己的 API Key 仍可直连 DeepSeek、OpenAI 或兼容服务；
- 本机统计预测、SQLite 档案、持续学习和目标期验证继续可用；
- 云端请求采用短超时并静默降级，不阻塞首页。

## 一条命令部署

先把 DuckDNS 指向 VPS IPv4，并确认 VPS 已启动。然后在 Debian 服务器的 root 终端执行：

```bash
curl -fsSL https://raw.githubusercontent.com/xgl34222220-ops/tianji/main/deploy/install.sh | bash
```

安装程序会：

- 安装 Docker Engine 和 Compose；
- 克隆或更新 `/opt/tianji`；
- 询问 DuckDNS 域名、AI 接口、模型和 API Key；
- 自动生成管理令牌并保护 `.env`；
- 启动 API、后台 Worker 和 Caddy；
- 自动申请 HTTPS，并创建每日 SQLite 一致性备份。

默认服务地址：

```text
https://tianji-xgl.duckdns.org
```

常用命令：

```bash
cd /opt/tianji
docker compose ps
docker compose logs -f
docker compose up -d --build
deploy/backup.sh
```

健康检查和只读接口：

```text
GET /health
GET /v1/lotteries
GET /v1/snapshot/{lottery}
GET /v1/forecasts/{lottery}
```

强制立即运行后台任务需要 `.env` 中的管理令牌：

```text
POST /v1/admin/run
Authorization: Bearer <TIANJI_API_TOKEN>
```

## FCM 即时推送

预警中心未配置 FCM 时仍会通过 Android WorkManager 约每 15 分钟同步一次。真正的即时推送需要同时配置 APK 客户端参数和云端 Firebase 服务账号。

完整步骤：

```text
docs/FCM_SETUP.md
```

辅助命令：

```bash
# 在电脑或 Termux 中，从 google-services.json 写入 GitHub Actions Secrets
./tools/configure-fcm-release.sh /路径/google-services.json

# 在天机服务器中配置 Firebase 服务账号并验证 OAuth
sudo /opt/tianji/deploy/configure-fcm.sh /安全路径/firebase-service-account.json
```

正式发布工作流会拒绝发布 Firebase 客户端参数为空的 APK。Firebase 服务账号 JSON、`.env`、签名文件和数据库不得提交到仓库。

## v5.9.9 主要变化

- 重做双彩种切换器以及“概览 / 概率 / 模型”“策略 / 验证”分段控件，所有选项始终显示完整底色和边框。
- 统一顶部标题栏、通知与刷新按钮、设置入口、底部导航和 AI 主按钮的视觉层级。
- 修复预警中心标题与系统状态栏重叠。
- 预警中心分别显示 App 配置、云端账号和设备令牌状态。
- 正式 Release 支持从受保护的 `google-services.json` Secret 自动解析客户端参数，并强制校验非空。
- 新增客户端 Secret 配置脚本、服务端服务账号配置脚本和完整 FCM 文档。

## v5.8.0 主要变化

- App 全面统一 MIUIx 玻璃层级，重做顶栏、彩种切换器、卡片、指标块、开奖球和悬浮底栏。
- 提升基础字号、点击区域和页面留白，减少过重阴影，改善长时间阅读体验。
- Monet 动态取色会同步影响页面、卡片、顶栏和底栏材质。
- 原英文分区标题统一改为中文。
- 云端旧英文分析在 App、公开接口与管理控制台读取时自动中文化，不改写数据库原记录。
- 新生成的云端 AI 分析与风险提示强制使用简体中文；返回不符合要求时使用中文兜底。
- 云端管理控制台重新设计桌面端和手机端布局，统一筛选、档案、模型、开奖任务和运维状态卡片。
- 保持预测算法、目标期结算、数据库结构、接口字段和后台调度逻辑不变。

## v5.7.1 主要变化

- 正式 AI 只接收真实原始开奖历史，不再注入本机选择名次、候选、概率矩阵或预计算统计。
- 独立对话不再默认使用本机模型选中的名次；只有主动选择“参考本机”或“反向审计”时才传入本机信息。
- 十个高度重叠的人设收敛为“大数据规律、走势分析、综合预测”三个专业角色。
- 旧人设 ID 自动迁移到最接近的新角色，历史会话继续可用。
- 保留 v5.7.0 云端持续运行、本地降级、管理后台、目标期校验和异步云端 AI 修复。

## v5.7.0 主要变化

- 新增完整云端后端、后台轮询、开奖同步、预测唯一冻结和自动结算。
- 新增确定性云端预测器；未配置外部 AI 时仍可持续运行。
- 新增可选 OpenAI 兼容/DeepSeek AI 后台分析。
- Android 自动合并云端预测档案，同时保留全部本地能力。
- 新增 Docker、Caddy 自动 HTTPS、每日备份、健康检查和服务端 CI。

## v5.6.1 时效自适应学习

- 长期学习权重改为弱先验，并按跨越期数和连续未中自动衰减。
- 每一期仍使用最新历史重新计算近期热度、短中窗变化、转移和稳定性。
- 多期补结算按真实目标期从旧到新学习，各模型、模式和对话人格相互隔离。

## 自动验证

Android 分支持续执行单元测试、Lint、Debug APK 和 R8 Release APK 构建；服务端分支执行 Python 编译、单元测试、Docker Compose 校验和镜像构建。正式发布还会校验升级签名、应用 ID、版本信息和 Firebase 客户端配置。

> 随机开奖不可可靠预测。本项目用于统计实验、记录和真实前向验证，不承诺准确率、收益或必中。
