package io.github.xgl34222220.sinan.core

enum class ProxyCore(
    val id: String,
    val displayName: String,
    val binaryName: String,
    val defaultConfigName: String,
    val configAsset: String,
    val releaseRepository: String,
    val supportsClashApi: Boolean,
    val supportsWebUi: Boolean,
) {
    MIHOMO(
        id = "mihomo",
        displayName = "Mihomo",
        binaryName = "mihomo",
        defaultConfigName = "config.yaml",
        configAsset = "box/mihomo/config.yaml",
        releaseRepository = "MetaCubeX/mihomo",
        supportsClashApi = true,
        supportsWebUi = true,
    ),
    SING_BOX(
        id = "sing-box",
        displayName = "sing-box",
        binaryName = "sing-box",
        defaultConfigName = "config.json",
        configAsset = "box/sing-box/config.json",
        releaseRepository = "SagerNet/sing-box",
        supportsClashApi = true,
        supportsWebUi = true,
    ),
    XRAY(
        id = "xray",
        displayName = "Xray",
        binaryName = "xray",
        defaultConfigName = "config.json",
        configAsset = "box/xray/config.json",
        releaseRepository = "XTLS/Xray-core",
        supportsClashApi = false,
        supportsWebUi = false,
    ),
    V2FLY(
        id = "v2fly",
        displayName = "V2Fly",
        binaryName = "v2fly",
        defaultConfigName = "config.json",
        configAsset = "box/v2fly/config.json",
        releaseRepository = "v2fly/v2ray-core",
        supportsClashApi = false,
        supportsWebUi = false,
    ),
    HYSTERIA(
        id = "hysteria",
        displayName = "Hysteria 2",
        binaryName = "hysteria",
        defaultConfigName = "config.yaml",
        configAsset = "box/hysteria/config.yaml",
        releaseRepository = "apernet/hysteria",
        supportsClashApi = false,
        supportsWebUi = false,
    );

    fun versionCommand(binaryPath: String): String = when (this) {
        MIHOMO -> "$binaryPath -v"
        SING_BOX -> "$binaryPath version"
        XRAY -> "$binaryPath version"
        V2FLY -> "$binaryPath version"
        HYSTERIA -> "$binaryPath version"
    }

    fun acceptsAsset(name: String): Boolean {
        val lower = name.lowercase()
        return when (this) {
            MIHOMO -> lower.contains("android-arm64-v8") && lower.endsWith(".gz")
            SING_BOX -> lower.contains("android-arm64") && (lower.endsWith(".tar.gz") || lower.endsWith(".tgz"))
            XRAY -> lower.contains("android-arm64") && lower.endsWith(".zip") && !lower.contains("sdk")
            V2FLY -> lower.contains("android-arm64") && lower.endsWith(".zip")
            HYSTERIA -> lower.contains("android-arm64") && !lower.endsWith(".sha256") && !lower.endsWith(".txt")
        }
    }

    fun binaryEntryMatches(name: String): Boolean {
        val leaf = name.substringAfterLast('/').lowercase()
        return when (this) {
            MIHOMO -> leaf == "mihomo" || leaf.startsWith("mihomo-")
            SING_BOX -> leaf == "sing-box"
            XRAY -> leaf == "xray"
            V2FLY -> leaf == "v2ray" || leaf == "v2fly"
            HYSTERIA -> leaf == "hysteria" || leaf.startsWith("hysteria-android")
        }
    }

    companion object {
        fun fromId(value: String?): ProxyCore = entries.firstOrNull {
            it.id.equals(value?.trim(), ignoreCase = true) ||
                it.binaryName.equals(value?.trim(), ignoreCase = true)
        } ?: MIHOMO
    }
}

enum class TransparentMode(
    val id: String,
    val displayName: String,
    val summary: String,
) {
    TPROXY("tproxy", "TPROXY", "TCP / UDP 透明代理，推荐 Root 设备使用"),
    REDIRECT("redirect", "REDIRECT", "仅重定向 TCP，兼容性较高"),
    TUN("tun", "TUN", "由代理核心创建虚拟网卡"),
    MIXED("mixed", "MIXED", "同时启用 TUN 与防火墙透明转发"),
    ENHANCE("enhance", "ENHANCE", "增强模式，使用 eBPF 匹配与透明转发"),
    ;

    companion object {
        fun fromId(value: String?): TransparentMode = entries.firstOrNull {
            it.id.equals(value?.trim(), ignoreCase = true)
        } ?: TPROXY
    }
}
