# 天机 v6.6.0

v6.6.0 将正式预测链路升级为 **Dynamic AI v2**。本版本重点不是增加“更激进”的号码，而是清理固定目标遗留逻辑，让服务端 AI、统计先验、真实结算学习和 Android 展示重新回到同一套动态前向预测语义。

## Dynamic AI v2

- 正式运行链路不再安装固定 `235780` 的运行时覆盖、结算改写或输出保护。
- 移除“AI 必须故意与本机预测不同”的旧规则；AI 与本机统计保持独立计算，但允许自然得出相同候选。
- 修复位置概率与号码概率均为 10 维时被错误混合的聚合串线问题。
- 匿名多 reviewer 继续分别评审位置排名与号码排名，输出动态 Top6 / Top7 候选。
- 新增按真实已结算样本执行的 walk-forward 统计校准，并将位置层与号码层的先验完全分离。
- AI reviewer 与统计先验依据 LogLoss、Brier、Top6 等真实结算成绩持续调权。
- 新学习状态使用 `ai_v2_position_X:*` 命名空间，阻断 legacy / fixed-target 权重继续影响 v2。
- 历史冻结预测保持不可回写，避免新算法污染旧期档案。

## 服务端同步上线

- v6.6.0 Release 成功后，Production 会同步部署同一 `main` 提交。
- 部署前要求服务器 Git 工作区干净，并使用 `git pull --ff-only`，拒绝覆盖未提交的生产修改。
- 重新构建并启动 Docker Compose 的 API / Worker 服务后执行 `/health` 检查；健康检查通过才视为部署完成。
- Android 与云端因此使用同一代 Dynamic AI v2 语义，避免 App 已更新而服务端仍运行旧 fixed-target 预测。

## 回归与发布保护

- 服务端回归覆盖动态候选、历史冻结、AI 前缀缓存、统计融合与持续学习契约。
- Android 正式构建继续执行 Unit Test、Lint、Release Build、签名证书连续性和 APK 完整性验证。
- 正式应用 ID 保持 `com.tianji.probabilitylab.nativev5`，可直接覆盖升级。

> 天机用于统计实验与真实前向验证。随机开奖不可可靠预测，本版本不承诺准确率、收益或必中。
