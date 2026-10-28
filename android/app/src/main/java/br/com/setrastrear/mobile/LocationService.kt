package br.com.setrastrear.mobile

import android.Manifest
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.location.*
import android.os.*
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date

/** Compartilhamento iniciado pelo titular, visível e sem prazo automático. */
class LocationService : Service(), LocationListener {
 private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
 private lateinit var manager: LocationManager
 private var loop: Job? = null
 @Volatile private var latest: Location? = null
 private val prefs by lazy { getSharedPreferences("settings", 0) }
 override fun onBind(intent: Intent?) = null
 override fun onCreate() { super.onCreate(); manager = getSystemService(LOCATION_SERVICE) as LocationManager }
 override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
  if (intent?.action == "STOP") {
   prefs.edit().putBoolean("active", false).putBoolean("pause_pending", true).commit()
   loop?.cancel()
   manager.removeUpdates(this)
   stopForeground(STOP_FOREGROUND_REMOVE)
   // Não cancelar esta requisição chamando stopSelf antes de concluí-la.
   scope.launch {
    try {
     Api(this@LocationService).call("/device/settings", "PATCH", JSONObject().put("enabled", false).put("interval", prefs.getInt("interval", 60)))
     prefs.edit().putBoolean("pause_pending", false).apply()
    } catch (_: Exception) { /* Pausa local imediata; sincronizar quando o app reconectar. */ }
    finally { stopSelfResult(startId) }
   }
   return START_NOT_STICKY
  }
  val permission = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
  if (!prefs.getBoolean("active", false) || !prefs.getBoolean("consent", false) || !permission || Vault(this).get().isEmpty()) {
   prefs.edit().putBoolean("active", false).apply(); stopSelf(); return START_NOT_STICKY
  }
  try {
   val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
   nm.createNotificationChannel(NotificationChannel("sharing", "Compartilhamento de localização", NotificationManager.IMPORTANCE_LOW))
   val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
   val stop = PendingIntent.getService(this, 1, Intent(this, LocationService::class.java).setAction("STOP"), PendingIntent.FLAG_IMMUTABLE)
   startForeground(1, NotificationCompat.Builder(this, "sharing").setSmallIcon(R.drawable.ic_rastrear)
    .setContentTitle("Rastrear MB — compartilhamento de localização ativo")
    .setContentText("Compartilhamento contínuo. Toque para gerenciar ou pausar.")
    .setContentIntent(open).setOngoing(true).addAction(0, "Pausar", stop).build())
   if (loop?.isActive == true) return START_STICKY
   requestProviders()
  } catch (_: SecurityException) {
   prefs.edit().putBoolean("active", false).apply(); stopSelf(); return START_NOT_STICKY
  }
  loop = scope.launch {
   var last = 0L
   var retry = 5000L
   while (isActive && prefs.getBoolean("active", false)) {
    prefs.edit().putLong("service_heartbeat", SystemClock.elapsedRealtime()).apply()
    try {
     val status = Api(this@LocationService).call("/device/status")
     ensureActive()
     if (!status.optBoolean("enabled") || !status.optBoolean("linked")) {
      prefs.edit().putBoolean("active", false).apply(); stopSelf(); break
     }
     val interval = status.optInt("interval", 60)
     prefs.edit().putInt("interval", interval).apply()
     val p = latest
     val ts = System.currentTimeMillis() / 1000
     if (p != null && SystemClock.elapsedRealtimeNanos() - p.elapsedRealtimeNanos < 120_000_000_000L &&
      (status.optBoolean("requested") || (interval > 0 && ts - last >= interval))) {
      ensureActive()
      if (!prefs.getBoolean("active", false)) break
      val battery = (getSystemService(BATTERY_SERVICE) as BatteryManager).getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
      val body = JSONObject().put("latitude", p.latitude).put("longitude", p.longitude).put("accuracy", p.accuracy).put("timestamp", p.time / 1000)
      if (battery in 0..100) body.put("battery", battery)
      Api(this@LocationService).call("/device/location", "POST", body)
      last = ts
      prefs.edit().putString("last", DateFormat.getDateTimeInstance().format(Date())).apply()
     }
     retry = 5000L
     prefs.edit().remove("sharing_error").apply()
    } catch (e: CancellationException) { throw e
    } catch (_: Exception) {
     if (Vault(this@LocationService).get().isEmpty()) {
      prefs.edit().putBoolean("active", false).apply(); stopSelf(); break
     }
     // Uma falha de internet/servidor não revoga a decisão do titular.
     prefs.edit().putString("sharing_error", "Sem conexão; nova tentativa automática").apply()
     retry = (retry * 2).coerceAtMost(60000L)
    }
    delay(retry)
   }
  }
  return START_STICKY
 }
 @Suppress("MissingPermission")
 private fun requestProviders() {
  manager.removeUpdates(this)
  val precise = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
  val providers = if (precise) listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER) else listOf(LocationManager.NETWORK_PROVIDER)
  for (provider in providers)
   if (manager.isProviderEnabled(provider)) manager.requestLocationUpdates(provider, 5000, 0f, this)
 }
 override fun onProviderEnabled(provider: String) {
  if (prefs.getBoolean("active", false)) try { requestProviders() } catch (_: SecurityException) { stopSelf() }
 }
 override fun onLocationChanged(location: Location) { latest = location }
 override fun onDestroy() {
  manager.removeUpdates(this); prefs.edit().remove("service_heartbeat").apply(); scope.cancel(); super.onDestroy()
 }
}
