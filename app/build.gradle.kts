plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseStoreFile = providers.environmentVariable("TIANJI_KEYSTORE_FILE").orNull
val releaseStorePassword = providers.environmentVariable("TIANJI_KEYSTORE_PASSWORD").orNull
val releaseKeyAlias = providers.environmentVariable("TIANJI_KEY_ALIAS").orNull
val releaseKeyPassword = providers.environmentVariable("TIANJI_KEY_PASSWORD").orNull
val releaseSigningAvailable = listOf(
    releaseStoreFile,
    releaseStorePassword,
    releaseKeyAlias,
    releaseKeyPassword,
).all { !it.isNullOrBlank() }
val cloudBaseUrl = providers.gradleProperty("TIANJI_CLOUD_BASE_URL")
    .orElse("https://tianji-xgl.duckdns.org")

android {
    namespace = "com.tianji.probabilitylab.nativev4"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.tianji.probabilitylab.nativev6"
        minSdk = 26
        targetSdk = 36
        versionCode = 41
        versionName = "5.8.0"

        buildConfigField("String", "TIANJI_CLOUD_BASE_URL", "\"${cloudBaseUrl.get()}\"")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true
    }

    signingConfigs {
        if (releaseSigningAvailable) {
            create("release") {
                storeFile = file(requireNotNull(releaseStoreFile))
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
                enableV1Signing = true
                enableV2Signing = true
                enableV3Signing = true
                enableV4Signing = true
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            if (releaseSigningAvailable) {
                signingConfig = signingConfigs.getByName("release")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }

    lint {
        disable += setOf("OldTargetApi", "GradleDependency")
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}
