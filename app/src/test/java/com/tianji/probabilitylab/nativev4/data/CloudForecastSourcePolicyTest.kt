package com.tianji.probabilitylab.nativev4.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CloudForecastSourcePolicyTest {
    @Test
    fun onlyExplicitAiSourceCanEnterAiConsensus() {
        assertTrue(isCloudAiForecastSource("ai"))
        assertTrue(isCloudAiForecastSource(" AI "))
        assertFalse(isCloudAiForecastSource("native"))
        assertFalse(isCloudAiForecastSource("cloud"))
        assertFalse(isCloudAiForecastSource(""))
    }
}
