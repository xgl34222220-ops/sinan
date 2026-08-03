from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, changes: list[tuple[str, str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    for old, new, label in changes:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"{path} / {label}: expected 1 match, found {count}")
        text = text.replace(old, new, 1)
    target.write_text(text, encoding="utf-8")


patch(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt",
    [
        (
            '        val token = Regex("第\\s*([一二三四五六七八九十0-9]{1,2})\\s*名")',
            '        val token = Regex("""第\\s*([一二三四五六七八九十0-9]{1,2})\\s*名""")',
            "Kotlin regex raw string",
        ),
    ],
)

patch(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt",
    [
        (
            "                        readTimeoutMs = 30_000,",
            "                        readTimeoutMs = 8_000,",
            "same-conversation finalization deadline",
        ),
        (
            "                readTimeoutMs = if (config.analysisMode == AiAnalysisMode.DEEP) 60_000 else 45_000,",
            "                readTimeoutMs = if (config.analysisMode == AiAnalysisMode.DEEP) 40_000 else 30_000,",
            "formal hard deadline values",
        ),
        (
            "                readTimeoutMs = 45_000,\n                executionNote = \"${config.analysisMode.label} · 限时参数兼容回退\"",
            "                readTimeoutMs = 30_000,\n                executionNote = \"${config.analysisMode.label} · 限时参数兼容回退\"",
            "protocol fallback deadline",
        ),
        (
            "                                readChatStream(reader, started, onProgress)",
            "                                readChatStream(\n                                    reader = reader,\n                                    startedAtMs = started,\n                                    hardDeadlineMs = readTimeoutMs.toLong(),\n                                    onProgress = onProgress,\n                                )",
            "stream deadline call",
        ),
        (
            "        startedAtMs: Long,\n        onProgress: (String, Long) -> Unit,",
            "        startedAtMs: Long,\n        hardDeadlineMs: Long,\n        onProgress: (String, Long) -> Unit,",
            "stream deadline signature",
        ),
        (
            "        var firstContentMs = -1L\n",
            "        var firstContentMs = -1L\n        var hardDeadlineReached = false\n",
            "deadline state",
        ),
        (
            "            reader.forEachLine { rawLine ->\n                val line = rawLine.trim()",
            "            reader.forEachLine { rawLine ->\n                if (System.currentTimeMillis() - startedAtMs >= hardDeadlineMs) {\n                    throw ForecastHardDeadlineException()\n                }\n                val line = rawLine.trim()",
            "deadline check",
        ),
        (
            "        } catch (_: ForecastCoreReadyException) {\n            finishReason = \"tianji_core_ready\"\n        } catch (cause: IOException) {",
            "        } catch (_: ForecastCoreReadyException) {\n            finishReason = \"tianji_core_ready\"\n        } catch (_: ForecastHardDeadlineException) {\n            hardDeadlineReached = true\n            finishReason = \"tianji_hard_deadline\"\n            onProgress(\n                \"正式预测达到总时长上限，正在抢救已接收内容\",\n                System.currentTimeMillis() - startedAtMs,\n            )\n        } catch (cause: IOException) {",
            "deadline catch",
        ),
        (
            "                put(\"_tianji_stream_finished_ms\", System.currentTimeMillis() - startedAtMs)\n            }",
            "                put(\"_tianji_stream_finished_ms\", System.currentTimeMillis() - startedAtMs)\n                put(\"_tianji_hard_deadline\", hardDeadlineReached)\n            }",
            "deadline metadata",
        ),
        (
            "        streamFailure?.let { failure ->",
            "        if (hardDeadlineReached && content.isEmpty() && reasoning.isEmpty()) {\n            error(\"正式预测达到总时长上限，模型尚未生成可补全内容\")\n        }\n\n        streamFailure?.let { failure ->",
            "empty deadline failure",
        ),
        (
            "    private class ForecastCoreReadyException : RuntimeException()\n",
            "    private class ForecastCoreReadyException : RuntimeException()\n    private class ForecastHardDeadlineException : RuntimeException()\n",
            "deadline exception",
        ),
    ],
)

# Avoid a nested interpolation that is hard to read and fragile across Kotlin versions.
patch(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    [
        (
            '                    audit.meanEstimatedCost?.let { append(" · 均价 $${"%.5f".format(Locale.US, it)}") }',
            '                    audit.meanEstimatedCost?.let { cost ->\n                        append(" · 均价 $")\n                        append("%.5f".format(Locale.US, cost))\n                    }',
            "cost display",
        ),
    ],
)

patch(
    "RELEASE_NOTES_v5.5.9.md",
    [
        (
            "- 60 期模式最长等待 45 秒，120 期模式最长等待 60 秒；持续返回推理字符也不能绕过总时长截止。",
            "- 60 期模式主请求最多约 30 秒，120 期模式主请求最多约 40 秒；只有部分内容时沿同一会话最多再用约 8 秒补齐，持续返回推理字符也不能绕过总时长截止。",
            "release deadline note",
        ),
    ],
)

for temporary in [
    ROOT / "tools/fix_v559_followup.py",
    ROOT / ".github/workflows/fix-v559-followup.yml",
]:
    if temporary.exists():
        temporary.unlink()
