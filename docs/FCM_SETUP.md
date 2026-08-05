# 天机 FCM 即时推送配置

天机的预警系统分为两部分：

1. Android APK 内的 Firebase 客户端配置，用于取得设备 FCM Token。
2. 天机云端服务的 Firebase 服务账号，用于通过 FCM HTTP v1 API 发送通知。

两部分必须来自同一个 Firebase Project。任意一部分缺失时，App 会继续使用约 15 分钟一次的后台同步兜底，但不会具备真正的即时推送。

## 1. 创建 Firebase Android App

在 Firebase Console 新建或选择一个项目，然后添加 Android 应用：

- Android 软件包名称：`com.tianji.probabilitylab.nativev5`
- 应用昵称：可填写 `天机 Android`
- SHA-1 / SHA-256：FCM 本身不强制要求，可暂时不填

注册完成后下载 `google-services.json`。

> 不要把包名填写成源码 namespace `com.tianji.probabilitylab.nativev4`。正式 APK 的 applicationId 是 `com.tianji.probabilitylab.nativev5`。

## 2. 写入 GitHub Actions Secrets

在已安装 GitHub CLI 的电脑或 Termux 中运行：

```bash
chmod +x tools/configure-fcm-release.sh
./tools/configure-fcm-release.sh /路径/google-services.json
```

脚本会验证包名，并安全写入以下 GitHub Actions Secrets：

- `TIANJI_FIREBASE_GOOGLE_SERVICES_JSON_B64`
- `TIANJI_FIREBASE_PROJECT_ID`
- `TIANJI_FIREBASE_APP_ID`
- `TIANJI_FIREBASE_API_KEY`
- `TIANJI_FIREBASE_SENDER_ID`

配置不会写入 Git 仓库。

## 3. 创建 Firebase 服务账号

在 Firebase Console 打开：

`项目设置 → 服务账号 → Firebase Admin SDK → 生成新的私钥`

下载得到服务账号 JSON。该文件包含私钥，禁止提交到 GitHub，也不要发送到公开聊天、网盘或截图中。

确认项目已启用 Firebase Cloud Messaging API（HTTP v1）。

## 4. 配置天机服务器

将服务账号 JSON 通过 SCP、SFTP 等方式放到服务器的临时安全目录，例如：

```bash
scp firebase-service-account.json root@服务器IP:/root/
```

登录服务器后运行：

```bash
chmod +x /opt/tianji/deploy/configure-fcm.sh
sudo /opt/tianji/deploy/configure-fcm.sh /root/firebase-service-account.json
rm -f /root/firebase-service-account.json
```

脚本会完成：

- 校验服务账号 JSON
- 写入 `/opt/tianji/.env`
- 设置 `TIANJI_FCM_PROJECT_ID`
- 设置 `TIANJI_FCM_SERVICE_ACCOUNT_B64`
- 重建 API 与 Worker 容器
- 实际请求 Google OAuth Token 验证服务账号有效性
- 执行天机服务健康检查

## 5. 验证

安装带 Firebase 配置构建出的正式 APK，允许通知权限，打开一次“预警中心”并刷新。

顶部应显示三个绿色状态：

- App 配置
- 云端账号
- 设备令牌

状态文字应变为：

`FCM 即时推送已连接，15 分钟后台检查作为兜底`

若某一项为黄色，App 会明确显示缺失的是 APK 客户端配置、云端服务账号还是设备令牌。

## 安全说明

- `google-services.json` 主要包含项目标识，但仍通过 GitHub Secret 注入，避免项目配置散落。
- Firebase 服务账号 JSON 是高敏感私钥，只允许保存在服务器受限环境变量中。
- `/opt/tianji/.env` 必须保持权限 `600`。
- 服务账号原始 JSON 完成配置后应立即删除。
- 正式发布工作流会拒绝在 Firebase 客户端参数为空时发布 APK。
