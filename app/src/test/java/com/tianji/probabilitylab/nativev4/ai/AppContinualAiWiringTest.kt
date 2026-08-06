package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppContinualAiWiringTest {
    @Test
    fun appControllerRoutesFormalForecastsThroughContinualLearningGuard() {
        val source = File(
            "src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
        ).readText()

        assertTrue(source.contains("import com.tianji.probabilitylab.nativev4.ai.ContinualRemoteAiAnalyzer"))
        assertTrue(source.contains("private val remoteAiAnalyzer = ContinualRemoteAiAnalyzer(appContext)"))
        assertFalse(source.contains("private val remoteAiAnalyzer = RemoteAiAnalyzer(appContext)"))
    }
}
