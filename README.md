# 天机 · 开奖概率实验室

天机是一款面向历史开奖数据分析、候选预测和真实前向验证的 Android 应用。应用从开奖接口同步历史与目标期开奖数据，本机统计模型、可选 AI 和云端后台均以真实目标期冻结和结算。

## 当前版本

- 版本：5.7.1 AI 真独立与三专家正式版
- Android：原生 Kotlin + Jetpack Compose
- 服务端：FastAPI + SQLite WAL + Docker Compose + Caddy HTTPS
- 构建：Java 17、Gradle 8.13、Android SDK 36

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

Android 分支持续执行单元测试、Lint、Debug APK 和 R8 Release APK 构建；服务端分支执行 Python 编译、单元测试、Docker Compose 校验和镜像构建。

> 随机开奖不可可靠预测。本项目用于统计实验、记录和真实前向验证，不承诺准确率、收益或必中。
