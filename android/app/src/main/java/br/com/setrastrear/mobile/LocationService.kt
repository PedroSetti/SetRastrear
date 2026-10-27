package br.com.setrastrear.mobile
import android.app.*
import android.content.Intent
import android.location.*
import android.os.*
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date

class LocationService:Service(),LocationListener {
 private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
 private lateinit var manager:LocationManager
 private var latest:Location?=null
 override fun onBind(i:Intent?)=null
 override fun onCreate(){super.onCreate();manager=getSystemService(LOCATION_SERVICE)as LocationManager}
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
  val prefs=getSharedPreferences("settings",0)
  if(intent?.action=="STOP"){prefs.edit().putBoolean("active",false).apply();scope.launch{try{Api(this@LocationService).call("/device/settings","PATCH",JSONObject().put("enabled",false).put("interval",60))}catch(_:Exception){}};stopSelf();return START_NOT_STICKY}
  if(!prefs.getBoolean("active",false)){stopSelf();return START_NOT_STICKY}
  val nm=getSystemService(NOTIFICATION_SERVICE)as NotificationManager
  nm.createNotificationChannel(NotificationChannel("sharing","Compartilhamento de localização",NotificationManager.IMPORTANCE_LOW))
  val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE)
  val stop=PendingIntent.getService(this,1,Intent(this,LocationService::class.java).setAction("STOP"),PendingIntent.FLAG_IMMUTABLE)
  startForeground(1,NotificationCompat.Builder(this,"sharing").setSmallIcon(br.com.setrastrear.mobile.R.drawable.ic_rastrear).setContentTitle("Rastrear MB — compartilhamento de localização ativo").setContentText("Toque para gerenciar. Você pode pausar a qualquer momento.").setContentIntent(open).setOngoing(true).addAction(0,"Pausar",stop).build())
  try{for(provider in listOf(LocationManager.GPS_PROVIDER,LocationManager.NETWORK_PROVIDER))if(manager.isProviderEnabled(provider))manager.requestLocationUpdates(provider,5000,0f,this)}catch(_:SecurityException){stopSelf();return START_NOT_STICKY}
  scope.coroutineContext.cancelChildren()
  scope.launch {var last=0L
   while(isActive&&prefs.getBoolean("active",false)){
    try{val status=Api(this@LocationService).call("/device/status")
     if(!status.optBoolean("enabled")||!status.optBoolean("linked")){prefs.edit().putBoolean("active",false).apply();stopSelf();break}
     val interval=status.optInt("interval",60);val p=latest;val ts=System.currentTimeMillis()/1000
     if(p!=null&&SystemClock.elapsedRealtimeNanos()-p.elapsedRealtimeNanos<120_000_000_000L&&(status.optBoolean("requested")||(interval>0&&ts-last>=interval))){
      if(!prefs.getBoolean("active",false))break
      val battery=(getSystemService(BATTERY_SERVICE)as BatteryManager).getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
      val body=JSONObject().put("latitude",p.latitude).put("longitude",p.longitude).put("accuracy",p.accuracy).put("timestamp",p.time/1000)
      if(battery in 0..100)body.put("battery",battery)
      Api(this@LocationService).call("/device/location","POST",body);last=ts;prefs.edit().putString("last",DateFormat.getDateTimeInstance().format(Date())).apply()
     }
    }catch(_:Exception){if(Vault(this@LocationService).get().isEmpty()){prefs.edit().putBoolean("active",false).apply();stopSelf();break}}
    delay(5000)
   }
  }
  return START_NOT_STICKY
 }
 override fun onLocationChanged(location:Location){latest=location}
 override fun onDestroy(){manager.removeUpdates(this);scope.cancel();super.onDestroy()}
}
