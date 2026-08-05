# 天机（Tianji）

天机是一个面向真实开奖数据的 Android 原生概率实验室，包含双彩种同步、本机模型、独立 AI 分析、预测冻结、目标期结算、前向档案、管理后台和预测预警。

> 本项目仅用于统计实验、模型验证和软件工程研究，不承诺盈利或必中。

## 核心能力

- 同步幸运飞艇与澳洲幸运10真实历史开奖。
- 本机多模型训练、时间切分验证和概率输出。
- 多个 AI 配置独立分析，再形成共识记录。
- 开奖前冻结预测，开奖后严格按目标期结算。
- 保存本机、云端本地、云端 AI 和 AI 共识档案。
- 支持连续三期 Top 6 未命中预警及升级提醒。
- Android App 支持亮色、暗色、OLED、Monet 和彩种跟随配色。
- 云端提供管理控制台、自动同步、备份与更新脚本。

## Android

正式应用 ID：

```text
com.tianji.probabilitylab.nativev5
```

本地构建：

```bash
gradle :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

正式签名和 Firebase 客户端参数均通过受保护环境变量或 GitHub Actions Secrets 注入。

## FCM 即时推送

预警中心即使未配置 FCM，也会通过 Android WorkManager 约每 15 分钟同步一次。要启用真正的即时通知，需要同时配置：

- Android APK Firebase 客户端参数
- 云端 Firebase 服务账号

完整步骤见：

```text
docs/FCM_SETUP.md
```

辅助脚本：

```bash
# 在电脑或 Termux 中设置 GitHub Actions Secrets
./tools/configure-fcm-release.sh /路径/google-services.json

# 在天机服务器设置 Firebase 服务账号
sudo /opt/tianji/deploy/configure-fcm.sh /安全路径/firebase-service-account.json
```

## 云端部署

首次安装：

```bash
curl -fsSL https://raw.githubusercontent.com/xgl34222220-ops/tianji/main/deploy/install.sh | sudo bash
```

更新：

```bash
sudo /opt/tianji/deploy/update.sh
```

默认地址：

```text
https://tianji-xgl.duckdns.org
```

服务端配置保存在 `/opt/tianji/.env`，数据库保存在 `/opt/tianji/data`。不要提交 `.env`、Firebase 服务账号 JSON、签名文件或数据库。

## 验证

Android CI 执行：

- Debug 与 Release 单元测试
- Android Lint
- Debug 与 Release APK 构建
- 部署脚本 Shell 语法检查
- 正式发布工作流 YAML 语法检查

服务端 CI 执行：

- Python 编译
- 全部服务端单元测试
- Docker Compose 配置验证
- 后端镜像构建

正式 Release 还会验证：

- 升级签名证书与上一正式版一致
- 应用 ID、版本号与版本代码正确
- Firebase 客户端配置四项均非空
- APK v2 / v3 签名有效
- APK SHA-256 摘要

## 目录

```text
app/        Android 原生应用
server/     FastAPI 云端服务
deploy/     安装、更新、备份及 FCM 配置脚本
tools/      本地配置辅助工具
docs/       配置文档
```

## License

请在发布或分发前补充适合项目的开源许可证，并确认第三方接口、图标、字体和依赖的授权范围。
