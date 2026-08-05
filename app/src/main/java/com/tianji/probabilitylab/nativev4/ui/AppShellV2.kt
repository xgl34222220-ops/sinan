package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoGraph
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.ui.graphics.vector.ImageVector

enum class MainDestination(
    val label: String,
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
) {
    HOME("预测", "天机预测", "开奖、冻结结果与 AI 共识", Icons.Rounded.Home),
    STRATEGY("策略", "策略与验证", "前向证据、模型表现与风险闸门", Icons.Rounded.AutoGraph),
    ARCHIVE("档案", "预测档案", "开奖前冻结，开奖后按目标期结算", Icons.Rounded.History),
    SETTINGS("设置", "设置", "模型、数据、外观与应用信息", Icons.Rounded.Settings),
}
