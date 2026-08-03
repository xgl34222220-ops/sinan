package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiForecastPayloadExtractorTest {
    private val scores = (1..10).joinToString(",") { (it / 10.0).toString() }

    @Test
    fun extractsJsonSurroundedByProseAndFence() {
        val text = "分析完成。```json\n{\"position\":8,\"scores\":[$scores],\"uncertainty\":\"边界接近\"}\n```"
        val objects = AiForecastPayloadExtractor.balancedJsonObjects(text)

        assertEquals(1, objects.size)
        assertTrue(AiForecastPayloadExtractor.containsForecastCore(objects.single()))
    }

    @Test
    fun ignoresBracesInsideStrings() {
        val text = "{\"position\":8,\"scores\":[$scores],\"note\":\"保留 {核验} 内容\"}"
        val objects = AiForecastPayloadExtractor.balancedJsonObjects(text)

        assertEquals(1, objects.size)
        assertEquals(text, objects.single())
    }

    @Test
    fun salvagesCoreWhenOptionalExplanationWasTruncated() {
        val text = "{\"position\":8,\"scores\":[$scores],\"calculation_summary\":\"尚未写完"
        val recovered = AiForecastPayloadExtractor.salvageCoreJson(text)

        assertNotNull(recovered)
        assertTrue(recovered!!.contains("\"position\":8"))
        assertTrue(recovered.contains("\"scores\":["))
    }

    @Test
    fun rejectsIncompleteScoreArray() {
        val text = "{\"position\":8,\"scores\":[0.1,0.2,0.3]}"
        assertNull(AiForecastPayloadExtractor.salvageCoreJson(text))
    }

    @Test
    fun findsForecastAfterEarlierUnrelatedJson() {
        val text = "状态 {\"phase\":\"thinking\"} 最终 {\"position\":9,\"scores\":[$scores]}"
        val objects = AiForecastPayloadExtractor.balancedJsonObjects(text)

        assertEquals(2, objects.size)
        assertTrue(AiForecastPayloadExtractor.containsForecastCore(objects.last()))
    }
}
