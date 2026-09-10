import java.util.Properties

plugins { id("com.android.application") }

val sharedSigningPath = providers.environmentVariable("TINYAGENT_SIGNING_PROPERTIES").orNull
val sharedSigning = Properties().apply {
    if (sharedSigningPath != null) file(sharedSigningPath).inputStream().use { load(it) }
}
val releaseSigningPath = providers.environmentVariable("TINYAGENT_RELEASE_SIGNING_PROPERTIES").orNull
val releaseSigning = Properties().apply {
    if (releaseSigningPath != null) file(releaseSigningPath).inputStream().use { load(it) }
}

val bootstrapAssets = tasks.register<Sync>("bootstrapAssets") {
    from("../third_party/libadb/LICENSES") { into("licenses/libadb") }
    from("../third_party/libadb/PROVENANCE.md") { into("licenses/libadb") }
    from("../scripts") {
        include("prepare-development.sh", "prepare-self-build.sh", "prepare-android-sdk-fedora.py", "configure-android-sdk-fedora.py")
        into("bootstrap")
    }
    into(layout.buildDirectory.dir("generated/bootstrap-assets"))
}

android {
    namespace = "io.github.gplaider.tinyagent"
    compileSdk = 36
    defaultConfig {
        applicationId = "io.github.gplaider.tinyagent"
        minSdk = 30
        targetSdk = 36
        versionCode = 3
        versionName = "0.1.0-preview.4"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    sourceSets.getByName("main").assets.srcDir("../preroot")
    sourceSets.getByName("main").assets.srcDir("../harness")
    sourceSets.getByName("main").assets.srcDir(bootstrapAssets)
    sourceSets.getByName("main").java.srcDir("../third_party/libadb/src")
    androidResources { noCompress += "bin" }
    packaging { jniLibs { useLegacyPackaging = true; keepDebugSymbols += "**/*.so" } }
    if (sharedSigningPath != null) {
        signingConfigs.getByName("debug") {
            storeFile = file(sharedSigning.getProperty("storeFile") ?: error("Missing signing storeFile"))
            storePassword = sharedSigning.getProperty("storePassword") ?: error("Missing storePassword")
            keyAlias = sharedSigning.getProperty("keyAlias") ?: error("Missing keyAlias")
            keyPassword = sharedSigning.getProperty("keyPassword") ?: error("Missing keyPassword")
        }
    }
    if (releaseSigningPath != null) {
        signingConfigs.create("production") {
            storeFile = file(releaseSigning.getProperty("storeFile") ?: error("Missing release storeFile"))
            storePassword = releaseSigning.getProperty("storePassword") ?: error("Missing release storePassword")
            keyAlias = releaseSigning.getProperty("keyAlias") ?: error("Missing release keyAlias")
            keyPassword = releaseSigning.getProperty("keyPassword") ?: error("Missing release keyPassword")
        }
    }
    buildTypes {
        getByName("debug") { applicationIdSuffix = ".debug" }
        getByName("release") {
            isMinifyEnabled = false
            if (releaseSigningPath != null) signingConfig = signingConfigs.getByName("production")
        }
    }
}

tasks.named("preBuild") { dependsOn(bootstrapAssets) }

dependencies {
    implementation("androidx.core:core:1.16.0")
    implementation("dev.mobile:dadb:1.2.10")
    implementation("androidx.annotation:annotation:1.9.1")
    implementation("org.bouncycastle:bcprov-jdk15to18:1.84")
    implementation("org.bouncycastle:bctls-jdk15to18:1.84")
    implementation("org.bouncycastle:bcpkix-jdk15to18:1.84")
}
