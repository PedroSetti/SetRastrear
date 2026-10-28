import java.net.URI
plugins { id("com.android.application"); id("org.jetbrains.kotlin.android"); id("org.jetbrains.kotlin.plugin.compose") }
// A URL é configuração pública; não inclua tokens ou senhas.
val serverUrl = providers.environmentVariable("RMB_SERVER_URL").orElse(providers.gradleProperty("RMB_SERVER_URL")).orElse("").get().trimEnd('/')
if (serverUrl.isNotEmpty()) {
 val endpoint = URI(serverUrl)
 require(endpoint.scheme == "https" && endpoint.host != null && endpoint.userInfo == null && endpoint.query == null && endpoint.fragment == null && endpoint.path.isNullOrEmpty()) { "RMB_SERVER_URL deve ser uma origem HTTPS sem caminho, senha ou token" }
}
if (gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) }) {
 require(serverUrl.isNotEmpty()) { "Defina RMB_SERVER_URL para gerar um release conectado ao servidor definitivo" }
}
android {
 namespace = "br.com.setrastrear.mobile"
 compileSdk = 35
 defaultConfig { applicationId = "br.com.setrastrear.mobile"; minSdk = 26; targetSdk = 35; versionCode = 4; versionName = "1.2.0"; buildConfigField("String", "SERVER_URL", "\"$serverUrl\"") }
 buildFeatures { compose = true; buildConfig = true }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
 signingConfigs {
  if (System.getenv("RMB_KEYSTORE") != null) create("production") {
   storeFile = file(System.getenv("RMB_KEYSTORE")); storePassword = System.getenv("RMB_STORE_PASSWORD")
   keyAlias = System.getenv("RMB_KEY_ALIAS"); keyPassword = System.getenv("RMB_KEY_PASSWORD")
  }
 }
 buildTypes {
  getByName("release") { if (System.getenv("RMB_KEYSTORE") != null) signingConfig = signingConfigs.getByName("production") }
  create("qa") { initWith(getByName("debug")); applicationIdSuffix = ".qa"; matchingFallbacks += "debug" }
 }
}
dependencies {
 implementation(platform("androidx.compose:compose-bom:2024.10.01"))
 implementation("androidx.activity:activity-compose:1.9.3")
 implementation("androidx.compose.material3:material3")
 implementation("androidx.compose.ui:ui")
 implementation("androidx.core:core-ktx:1.15.0")
 implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
 implementation("com.google.zxing:core:3.5.3")
}
