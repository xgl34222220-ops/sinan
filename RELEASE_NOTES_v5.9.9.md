# 天机 v5.9.9

本版本完成 App 端视觉统一，并将预测预警从“具备 FCM 代码但可能空配置”升级为可诊断、可验证、正式发布时强制启用的即时推送方案。预测算法、开奖源、冻结结果和目标期结算规则保持不变。

## App 全面视觉优化

- 重做“幸运飞艇 / 澳洲幸运10”切换器，两侧始终显示完整等宽圆角按钮，不再出现只有选中一半有框的问题。
- 重做“概览 / 概率 / 模型”和“策略 / 验证”分段控件，每个选项均有完整底色、边框和明确点击区域。
- 选中状态增加强调描边、轻阴影、短指示条和柔和缩放动画。
- 顶部标题栏、通知按钮、刷新按钮、设置入口卡片和底部导航统一视觉层级。
- 增强底部 AI 主按钮的渐变、光晕和运行状态表现。
- 保留系统 Monet、彩种跟随、亮色、暗色和 OLED 模式。

## 预警中心修复与优化

- 修复预警中心标题与系统状态栏重叠的问题。
- 新增 App 配置、云端账号、设备令牌三项独立状态显示。
- 可准确区分以下情况：
  - APK 未注入 Firebase 客户端配置
  - 云端未配置 Firebase 服务账号
  - 客户端已配置但尚未取得设备令牌
  - FCM 即时推送已完整连接
- FCM 未就绪时继续保留约 15 分钟后台同步兜底。

## FCM 正式发布保障

- 正式构建支持直接从受保护的 `google-services.json` GitHub Secret 自动解析 Firebase 参数。
- 发布工作流会校验 Android 包名必须为 `com.tianji.probabilitylab.nativev5`。
- Firebase Project ID、App ID、API Key 或 Sender ID 任一为空时，正式发布会立即失败，不再发布缺少即时推送配置的 APK。
- Release 附件新增 `FIREBASE_CONFIG.txt`，用于确认正式 APK 已注入 FCM 客户端配置，不包含私钥。
- 保留原有四项 Firebase Secret 的兼容读取方式。

## 安全配置工具

- 新增 `tools/configure-fcm-release.sh`：从 `google-services.json` 校验包名并安全写入 GitHub Actions Secrets。
- 新增 `deploy/configure-fcm.sh`：在服务器写入 Firebase 服务账号、重建容器并实际验证 OAuth Token。
- 新增完整文档 `docs/FCM_SETUP.md`。
- Firebase 服务账号私钥始终仅保存在服务器环境变量中，不写入 Git 仓库。
- 新增本地 Firebase、签名文件忽略规则，防止误提交。

## 验证要求

正式版发布前必须同时满足：

- Android Debug / Release 单元测试通过。
- Android Lint 通过。
- Debug / Release APK 构建通过。
- 服务端全部单元测试通过。
- 部署脚本 Shell 语法检查通过。
- Firebase 客户端四项配置非空。
- 正式 APK 与 v5.9.8 使用相同升级签名证书。
