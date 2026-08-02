package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.LotteryType

/** Lightweight compatibility query used before a billable AI call is submitted. */
fun AppDatabase.hasAiForecast(
    lottery: LotteryType,
    profileId: String,
    targetPeriod: String,
): Boolean = loadAiForecasts(lottery, limit = 200).any { record ->
    record.profileId == profileId && record.targetPeriod == targetPeriod
}
