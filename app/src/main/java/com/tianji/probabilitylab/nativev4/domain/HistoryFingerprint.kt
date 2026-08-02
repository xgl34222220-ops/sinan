package com.tianji.probabilitylab.nativev4.domain

import com.tianji.probabilitylab.nativev4.model.Draw
import java.security.MessageDigest

/** Content-addresses the complete model history so corrected records invalidate cached forecasts. */
object HistoryFingerprint {
    fun of(draws: List<Draw>): String {
        val canonical = draws.joinToString("\n") { draw ->
            listOf(
                draw.lottery.apiKey,
                draw.period,
                draw.numbers.joinToString(","),
                draw.drawTime,
                draw.source,
            ).joinToString("|")
        }
        return MessageDigest.getInstance("SHA-256")
            .digest(canonical.toByteArray(Charsets.UTF_8))
            .joinToString("") { byte -> "%02x".format(byte) }
    }
}
