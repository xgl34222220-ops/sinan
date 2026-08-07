plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.android.compose.screenshot")
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
val firebaseProjectId = providers.gradleProperty("TIANJI_FIREBASE_PROJECT_ID").orElse("")
val firebaseAppId = providers.gradleProperty("TIANJI_FIREBASE_APP_ID").orElse("")
val firebaseApiKey = providers.gradleProperty("TIANJI_FIREBASE_API_KEY").orElse("")
val firebaseSenderId = providers.gradleProperty("TIANJI_FIREBASE_SENDER_ID").orElse("")

android {
    namespace = "com.tianji.probabilitylab.nativev4"
    compileSdk = 36
    experimentalProperties["android.experimental.enableScreenshotTest"] = true

    defaultConfig {
        applicationId = "com.tianji.probabilitylab.nativev5"
        minSdk = 26
        targetSdk = 36
        versionCode = 69
        versionName = "6.4.0"

        buildConfigField("String", "TIANJI_CLOUD_BASE_URL", "\"${cloudBaseUrl.get()}\"")
        buildConfigField("String", "TIANJI_FIREBASE_PROJECT_ID", "\"${firebaseProjectId.get()}\"")
        buildConfigField("String", "TIANJI_FIREBASE_APP_ID", "\"${firebaseAppId.get()}\"")
        buildConfigField("String", "TIANJI_FIREBASE_API_KEY", "\"${firebaseApiKey.get()}\"")
        buildConfigField("String", "TIANJI_FIREBASE_SENDER_ID", "\"${firebaseSenderId.get()}\"")
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
            if (releaseSigningAvailable) signingConfig = signingConfigs.getByName("release")
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

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.06.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    val firebaseBom = platform("com.google.firebase:firebase-bom:34.16.0")
    implementation(firebaseBom)
    implementation("com.google.firebase:firebase-messaging")
    implementation("androidx.work:work-runtime-ktx:2.11.2")

    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.animation:animation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3.adaptive:adaptive:1.2.0")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.datastore:datastore-preferences:1.1.7")

    screenshotTestImplementation("com.android.tools.screenshot:screenshot-validation-api:0.0.1-alpha15")
    screenshotTestImplementation("androidx.compose.ui:ui-tooling")

    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260522")
}
