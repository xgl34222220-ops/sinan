package com.tianji.probabilitylab.nativev4.ai

/**
 * Extracts a usable forecast payload from streamed text without exposing or persisting chain of
 * thought. It first keeps complete JSON objects, then salvages the required position/scores core
 * when optional explanation text was truncated after the model had already produced the forecast.
 */
object AiForecastPayloadExtractor {
    private val positionRegex = Regex("\\\"position\\\"\\s*:\\s*(10|[1-9])")
    private val scoresStartRegex = Regex("\\\"scores\\\"\\s*:\\s*\\[")

    fun balancedJsonObjects(text: String): List<String> {
        if (text.isBlank()) return emptyList()
        val results = mutableListOf<String>()
        var start = -1
        var depth = 0
        var inString = false
        var escaped = false

        text.forEachIndexed { index, char ->
            if (inString) {
                when {
                    escaped -> escaped = false
                    char == '\\' -> escaped = true
                    char == '"' -> inString = false
                }
                return@forEachIndexed
            }
            when (char) {
                '"' -> inString = true
                '{' -> {
                    if (depth == 0) start = index
                    depth++
                }
                '}' -> if (depth > 0) {
                    depth--
                    if (depth == 0 && start >= 0) {
                        results += text.substring(start, index + 1)
                        start = -1
                    }
                }
            }
        }
        return results
    }

    fun containsForecastCore(text: String): Boolean = salvageCoreJson(text) != null

    fun salvageCoreJson(text: String): String? {
        if (text.isBlank()) return null
        val position = positionRegex.find(text)?.groupValues?.getOrNull(1)?.toIntOrNull()
            ?.takeIf { it in 1..10 } ?: return null
        val scoresMatch = scoresStartRegex.find(text) ?: return null
        val arrayStart = text.indexOf('[', scoresMatch.range.first)
        if (arrayStart < 0) return null
        val arrayEnd = findArrayEnd(text, arrayStart) ?: return null
        val rawScores = text.substring(arrayStart + 1, arrayEnd)
        val scores = rawScores.split(',').map { item -> item.trim().toDoubleOrNull() }
        if (scores.size != 10 || scores.any { it == null || !it.isFinite() || it < 0.0 }) return null
        return buildString {
            append("{\"position\":")
            append(position)
            append(",\"scores\":[")
            append(scores.joinToString(",") { requireNotNull(it).toString() })
            append("]}")
        }
    }

    private fun findArrayEnd(text: String, start: Int): Int? {
        var depth = 0
        var inString = false
        var escaped = false
        for (index in start until text.length) {
            val char = text[index]
            if (inString) {
                when {
                    escaped -> escaped = false
                    char == '\\' -> escaped = true
                    char == '"' -> inString = false
                }
                continue
            }
            when (char) {
                '"' -> inString = true
                '[' -> depth++
                ']' -> {
                    depth--
                    if (depth == 0) return index
                }
            }
        }
        return null
    }
}
