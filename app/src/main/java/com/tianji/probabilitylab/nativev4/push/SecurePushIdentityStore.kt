package com.tianji.probabilitylab.nativev4.push

import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

internal class SecurePushIdentityStore(
    private val preferences: SharedPreferences,
) {
    @Volatile
    private var cachedSecret: String? = null

    fun deviceSecret(): String = cachedSecret ?: synchronized(this) {
        cachedSecret ?: loadOrCreateSecret().also { cachedSecret = it }
    }

    private fun loadOrCreateSecret(): String {
        decrypt(preferences.getString(KEY_ENCRYPTED_SECRET, null))?.let { return it }
        val legacy = preferences.getString(KEY_LEGACY_SECRET, null)?.takeIf { it.length >= 24 }
        val secret = legacy ?: randomSecret()
        val editor = preferences.edit()
        val encrypted = encrypt(secret)
        if (encrypted != null) {
            editor.putString(KEY_ENCRYPTED_SECRET, encrypted).remove(KEY_LEGACY_SECRET)
        } else {
            editor.putString(KEY_LEGACY_SECRET, secret)
        }
        editor.apply()
        return secret
    }

    private fun randomSecret(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString(separator = "") { value ->
            "%02x".format(value.toInt() and 0xff)
        }
    }

    private fun encrypt(value: String): String? = runCatching {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        listOf(
            Base64.encodeToString(cipher.iv, Base64.NO_WRAP),
            Base64.encodeToString(encrypted, Base64.NO_WRAP),
        ).joinToString(":")
    }.getOrNull()

    private fun decrypt(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        return runCatching {
            val parts = raw.split(":", limit = 2)
            require(parts.size == 2)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                secretKey(),
                GCMParameterSpec(GCM_TAG_BITS, Base64.decode(parts[0], Base64.NO_WRAP)),
            )
            String(
                cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)),
                Charsets.UTF_8,
            ).takeIf { it.length >= 24 }
        }.getOrNull()
    }

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setRandomizedEncryptionRequired(true)
                    .build(),
            )
            generateKey()
        }
    }

    companion object {
        private const val KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "tianji_push_identity_v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val GCM_TAG_BITS = 128
        private const val KEY_ENCRYPTED_SECRET = "device_secret_encrypted_v1"
        private const val KEY_LEGACY_SECRET = "device_secret"
    }
}
