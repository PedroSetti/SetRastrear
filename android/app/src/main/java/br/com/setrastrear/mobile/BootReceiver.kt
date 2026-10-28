package br.com.setrastrear.mobile

import android.Manifest
import android.content.*
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/** Só retoma após opção expressa do titular e permissão Android apropriada. */
class BootReceiver : BroadcastReceiver() {
 override fun onReceive(context: Context, intent: Intent) {
  if (intent.action !in listOf(Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED)) return
  val prefs = context.getSharedPreferences("settings", 0)
  if (!prefs.getBoolean("resume_after_boot", false) || !prefs.getBoolean("active", false) ||
   !prefs.getBoolean("consent", false) || Vault(context).get().isEmpty()) return
  val foreground = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
  val background = Build.VERSION.SDK_INT < 29 || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED
  val notifications = Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
  if (!foreground || !background || !notifications) {
   prefs.edit().putString("sharing_error", "Abra o aplicativo e autorize a localização para retomar").apply()
   return
  }
  try { ContextCompat.startForegroundService(context, Intent(context, LocationService::class.java)) }
  catch (_: RuntimeException) { prefs.edit().putString("sharing_error", "O Android impediu a retomada. Abra o aplicativo e ative o compartilhamento.").apply() }
 }
}
