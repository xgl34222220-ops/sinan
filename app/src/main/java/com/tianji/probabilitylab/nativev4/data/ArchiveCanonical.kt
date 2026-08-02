package com.tianji.probabilitylab.nativev4.data

/** Length-prefixed encoding avoids field-boundary collisions in archive hash input. */
object ArchiveCanonical {
    const val NATIVE_VERSION = "native-archive-v2"
    const val AI_VERSION = "ai-archive-v2"
    const val CONSENSUS_VERSION = "consensus-archive-v2"

    fun encode(type: String, vararg fields: Any?): String = buildString {
        appendField(type)
        fields.forEach { value -> appendField(value?.toString().orEmpty()) }
    }

    private fun StringBuilder.appendField(value: String) {
        append(value.length)
        append(':')
        append(value)
    }
}
