package com.tianji.probabilitylab.nativev4.ai

import java.util.concurrent.Callable
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.FutureTask
import java.util.concurrent.ThreadPoolExecutor

/**
 * Tracks both queued and running work for every AI profile.
 *
 * HttpURLConnection cancellation only stops requests that already started. This registry also
 * cancels FutureTasks that are still waiting in the executor queue, preventing stale or billable
 * work after refresh, lottery switches, profile deletion, and manual cancellation.
 */
class AiTaskRegistry(private val executor: ThreadPoolExecutor) {
    private val tasks = ConcurrentHashMap<String, MutableSet<FutureTask<Unit>>>()

    fun submit(profileId: String, block: () -> Unit) {
        lateinit var task: FutureTask<Unit>
        task = FutureTask(
            Callable {
                try {
                    if (Thread.currentThread().isInterrupted) throw InterruptedException("AI 任务已取消")
                    block()
                    Unit
                } finally {
                    tasks[profileId]?.let { set ->
                        set.remove(task)
                        if (set.isEmpty()) tasks.remove(profileId, set)
                    }
                }
            },
        )
        tasks.computeIfAbsent(profileId) { ConcurrentHashMap.newKeySet() }.add(task)
        executor.execute(task)
    }

    fun cancel(profileId: String? = null) {
        val selected = if (profileId == null) {
            tasks.values.flatMap { it.toList() }
        } else {
            tasks.remove(profileId)?.toList().orEmpty()
        }
        selected.forEach { task -> task.cancel(true) }
        if (profileId == null) tasks.clear()
        executor.purge()
    }

    fun close() {
        cancel()
        executor.shutdownNow()
    }
}
