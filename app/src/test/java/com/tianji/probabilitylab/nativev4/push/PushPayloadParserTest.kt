package com.tianji.probabilitylab.nativev4.push

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class PushPayloadParserTest {
    @Test
    fun serverTitleAndTwoMissLevelArePreserved() {
        val alert = PushPayloadParser.fromRemoteData(
            mapOf(
                "alert_id" to "42",
                "schema_version" to "2",
                "event_type" to "miss_prealert",
                "severity" to "info",
                "streak" to "2",
                "threshold" to "3",
                "title" to "两期不中预警",
                "body" to "幸运飞艇 · DeepSeek 已连续两期未命中",
                "expires_at_epoch_ms" to (System.currentTimeMillis() + 60_000L).toString(),
            ),
        )

        requireNotNull(alert)
        assertEquals("两期不中预警", alert.title)
        assertEquals(PushProtocol.EVENT_MISS_PREALERT, alert.eventType)
        assertEquals(PushProtocol.SEVERITY_INFO, alert.severity)
        assertFalse(alert.isExpired)
    }

    @Test
    fun jsonPayloadReadsProtocolV2Metadata() {
        val alert = PushPayloadParser.fromJson(
            JSONObject(
                """
                {
                  "id": 7,
                  "title": "新一期云端 AI 预测",
                  "body": "目标期 123",
                  "event_type": "prediction_ready",
                  "severity": "info",
                  "schema_version": 2,
                  "collapse_key": "xyft:ai:model",
                  "data": {"latest_target_period": "123"}
                }
                """.trimIndent(),
            ),
        )

        requireNotNull(alert)
        assertEquals(2, alert.schemaVersion)
        assertEquals("123", alert.latestTargetPeriod)
        assertEquals("xyft:ai:model", alert.collapseKey)
    }
}
