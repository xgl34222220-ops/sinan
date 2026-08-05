package com.tianji.probabilitylab.nativev4.ui

/**
 * AI 共识在模型意见不足时允许不指定名次。界面回退到第一名展示，
 * 仅用于避免空值破坏布局，不会修改共识计算或冻结数据。
 */
internal fun positionNameV2(position: Int?): String = positionNameV2(position ?: 0)
