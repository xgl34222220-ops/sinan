package com.tianji.probabilitylab.nativev4.ai

import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.assertFalse
import org.junit.Test

class AiTaskRegistryTest {
    @Test
    fun queuedTaskDoesNotRunAfterCancellation() {
        val executor = ThreadPoolExecutor(
            1,
            1,
            60L,
            TimeUnit.SECONDS,
            LinkedBlockingQueue(),
        )
        val registry = AiTaskRegistry(executor)
        val blockerStarted = CountDownLatch(1)
        val releaseBlocker = CountDownLatch(1)
        val queuedRan = AtomicBoolean(false)

        try {
            registry.submit("blocker") {
                blockerStarted.countDown()
                releaseBlocker.await(2, TimeUnit.SECONDS)
            }
            blockerStarted.await(2, TimeUnit.SECONDS)
            registry.submit("queued") { queuedRan.set(true) }
            registry.cancel("queued")
            releaseBlocker.countDown()
            executor.shutdown()
            executor.awaitTermination(2, TimeUnit.SECONDS)

            assertFalse(queuedRan.get())
        } finally {
            releaseBlocker.countDown()
            registry.close()
        }
    }
}
