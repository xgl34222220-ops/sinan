package com.tianji.probabilitylab.nativev4.data

/** Only server forecasts explicitly tagged as AI may enter Android's AI consensus lane. */
internal fun isCloudAiForecastSource(source: String): Boolean =
    source.trim().equals("ai", ignoreCase = true)
