package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.LotteryType

/**
 * Source-compatibility bridge for callers compiled against the former extension.
 * AppDatabase's member function takes precedence and performs the indexed SQL query.
 */
@Suppress("EXTENSION_SHADOWED_BY_MEMBER")
fun AppDatabase.hasAiForecast(
    lottery: LotteryType,
    profileId: String,
    targetPeriod: String,
): Boolean = this.hasAiForecast(lottery, profileId, targetPeriod)
