package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CloudRealtimeOverviewApiTest {
    @Test
    fun parsesBothLotteriesFromOneOverview() {
        val parsed = parseCloudRealtimeOverview(
            body = """
                {
                  "lotteries": [
                    {
                      "key": "xyft",
                      "latest_period": "202608080101",
                      "numbers": [1,2,3,4,5,6,7,8,9,10],
                      "next_period": "202608080102",
                      "next_draw_at_epoch_ms": 20000,
                      "synced_at_epoch_ms": 15000
                    },
                    {
                      "key": "azxy10",
                      "latest_period": "202608080201",
                      "numbers": [10,9,8,7,6,5,4,3,2,1],
                      "next_period": "202608080202",
                      "next_draw_at_epoch_ms": 30000,
                      "synced_at_epoch_ms": 16000
                    }
                  ]
                }
            """.trimIndent(),
            fetchedAtEpochMs = 17_000L,
        )

        assertEquals(2, parsed.size)
        assertEquals("202608080101", parsed.getValue(LotteryType.XYFT).latestPeriod)
        assertEquals(listOf(1, 2, 3, 4, 5, 6, 7, 8, 9, 10), parsed.getValue(LotteryType.XYFT).numbers)
        assertEquals("202608080202", parsed.getValue(LotteryType.AZXY10).nextPeriod)
        assertEquals(30_000L, parsed.getValue(LotteryType.AZXY10).nextDrawAtEpochMs)
        assertEquals(17_000L, parsed.getValue(LotteryType.AZXY10).fetchedAtEpochMs)
    }

    @Test
    fun rejectsMalformedLotteryWithoutDroppingHealthyPeer() {
        val parsed = parseCloudRealtimeOverview(
            """
                {
                  "lotteries": [
                    {
                      "key": "xyft",
                      "latest_period": "101",
                      "numbers": [1,1,2,3,4,5,6,7,8,9],
                      "next_period": "102"
                    },
                    {
                      "key": "azxy10",
                      "latest_period": "201",
                      "numbers": [1,2,3,4,5,6,7,8,9,10],
                      "next_period": "202"
                    }
                  ]
                }
            """.trimIndent(),
        )

        assertFalse(parsed.containsKey(LotteryType.XYFT))
        assertTrue(parsed.containsKey(LotteryType.AZXY10))
    }
}
