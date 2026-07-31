# 司南 · 独立 Root 透明代理

司南是一个不依赖 Magisk / KernelSU 模块的 Android Root 透明代理控制器。
应用把 `boxctl`、`boxbpf`、数据库与 Mihomo 配置放在应用私有目录，通过 `su`
管理透明代理规则与 Mihomo 进程。

## 0.4 UI 重构

- 按参考图重做首页、面板、工具和设置四个主页面。
- 首页提供运行状态、启动/停止/重载/重启、网络延迟测试和核心管理。
- 面板通过 Mihomo REST API 读取真实代理组、当前节点和延迟，并支持切换节点。
- 工具页统一进入配置编辑、应用分流、日志、WebUI 与核心更新。
- 支持浅色/深色主题，统一大圆角卡片与悬浮底栏视觉。

## 自动构建

推送到 `main` 后，GitHub Actions 会自动构建可安装的 Debug APK，并作为构建产物上传。

## 架构限制

当前内置后端仅提供 `arm64-v8a`，要求 Android 10 或更高版本和可用 Root 授权。

## 上游

内置后端来自 GPL-3.0-or-later 项目：

- https://github.com/boxproxy/boxproxy
- 对应源码提交：`4ee996199151cce57bfbce673a127253686607da`
