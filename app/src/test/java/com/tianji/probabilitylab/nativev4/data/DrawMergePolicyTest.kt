package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Test

class DrawMergePolicyTest {
    @Test(expected = IllegalArgumentException::class)
    fun conflictingSamePeriodIsRejected() {
        DrawMergePolicy.merge(
            listOf(
                Draw(LotteryType.AZXY10, "100", (1..10).toList()),
                Draw(LotteryType.AZXY10, "100", (2..10).toList() + 1),
            ),
        )
    }

    @Test
    fun identicalDuplicateIsDeduplicated() {
        val draw = Draw(LotteryType.AZXY10, "100", (1..10).toList())
        val merged = DrawMergePolicy.merge(listOf(draw, draw.copy(source = "latest")))
        assertEquals(1, merged.size)
        assertEquals("latest", merged.single().source)
    }
}
