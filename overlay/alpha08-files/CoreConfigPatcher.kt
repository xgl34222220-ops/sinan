package io.github.xgl34222220.sinan.core

import org.json.JSONObject
import java.io.File

object CoreConfigPatcher {
    fun patch(
        core: ProxyCore,
        mode: TransparentMode,
        configFile: File,
        webUiDir: File,
    ): String {
        if (!configFile.exists()) return "配置文件不存在：${configFile.name}"
        val original = configFile.readText()
        val updated = when (core) {
            ProxyCore.MIHOMO -> patchMihomo(original, mode, webUiDir)
            ProxyCore.SING_BOX -> patchSingBox(original, webUiDir)
            else -> original
        }
        if (updated != original) configFile.writeText(updated)
        return "${core.displayName} 配置已同步为 ${mode.displayName} 模式"
    }

    private fun patchMihomo(
        content: String,
        mode: TransparentMode,
        webUiDir: File,
    ): String {
        var text = content.replace("\r\n", "\n")
        text = putYamlScalar(text, "external-controller", "127.0.0.1:9090")
        text = putYamlScalar(text, "external-ui", quoteYaml(webUiDir.absolutePath))
        text = putYamlScalar(text, "tproxy-port", "9898")
        text = putYamlScalar(text, "redir-port", "9797")
        val tunEnabled = mode == TransparentMode.TUN || mode == TransparentMode.MIXED
        text = putMihomoTunEnabled(text, tunEnabled)
        return text.trimEnd() + "\n"
    }

    private fun patchSingBox(content: String, webUiDir: File): String {
        return runCatching {
            val root = JSONObject(content)
            val experimental = root.optJSONObject("experimental") ?: JSONObject().also {
                root.put("experimental", it)
            }
            val clashApi = experimental.optJSONObject("clash_api") ?: JSONObject().also {
                experimental.put("clash_api", it)
            }
            clashApi.put("external_controller", "127.0.0.1:9090")
            clashApi.put("external_ui", webUiDir.absolutePath)
            root.toString(2) + "\n"
        }.getOrDefault(content)
    }

    private fun putYamlScalar(content: String, key: String, value: String): String {
        val pattern = Regex("(?m)^\\s*${Regex.escape(key)}\\s*:.*$")
        return if (pattern.containsMatchIn(content)) {
            content.replace(pattern, "$key: $value")
        } else {
            content.trimEnd() + "\n$key: $value\n"
        }
    }

    private fun putMihomoTunEnabled(content: String, enabled: Boolean): String {
        val lines = content.lines().toMutableList()
        val tunIndex = lines.indexOfFirst { it.trim() == "tun:" }
        if (tunIndex < 0) {
            return content.trimEnd() + "\ntun:\n  enable: $enabled\n  stack: mixed\n  auto-route: false\n"
        }
        val tunIndent = lines[tunIndex].takeWhile(Char::isWhitespace).length
        var insertAt = tunIndex + 1
        var enableIndex = -1
        while (insertAt < lines.size) {
            val line = lines[insertAt]
            if (line.trim().isEmpty()) {
                insertAt++
                continue
            }
            val indent = line.takeWhile(Char::isWhitespace).length
            if (indent <= tunIndent) break
            if (line.trimStart().startsWith("enable:")) enableIndex = insertAt
            insertAt++
        }
        if (enableIndex >= 0) {
            val indent = lines[enableIndex].takeWhile(Char::isWhitespace)
            lines[enableIndex] = "${indent}enable: $enabled"
        } else {
            lines.add(tunIndex + 1, "${" ".repeat(tunIndent + 2)}enable: $enabled")
        }
        return lines.joinToString("\n")
    }

    private fun quoteYaml(value: String): String = "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""
}
