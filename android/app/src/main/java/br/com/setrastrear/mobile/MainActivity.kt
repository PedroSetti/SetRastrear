package br.com.setrastrear.mobile
import android.Manifest
import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.os.Bundle
import android.os.Build
import android.os.SystemClock
import android.provider.Settings
import android.net.Uri
import android.content.Intent
import android.content.ClipData
import android.content.ClipboardManager
import android.content.pm.PackageManager
import android.graphics.Bitmap
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import com.google.zxing.BarcodeFormat
import com.google.zxing.MultiFormatWriter

class MainActivity:ComponentActivity(){
 private val permission=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){ grants ->
  if(grants[Manifest.permission.ACCESS_FINE_LOCATION]==true||grants[Manifest.permission.ACCESS_COARSE_LOCATION]==true)startSharing()
 }
 private fun startSharing(){
  if(ContextCompat.checkSelfPermission(this,Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED)return
  val settings=getSharedPreferences("settings",0)
  if(Build.VERSION.SDK_INT>=33&&ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){settings.edit().putBoolean("active",false).putString("sharing_error","Ative as notificações do aplicativo para manter o compartilhamento visível.").apply();return}
  settings.edit().putBoolean("active",true).putBoolean("pause_pending",false).commit()
  try{ContextCompat.startForegroundService(this,Intent(this,LocationService::class.java))}
  catch(_:RuntimeException){settings.edit().putBoolean("active",false).putString("sharing_error","Não foi possível iniciar. Verifique as permissões e tente novamente com o aplicativo aberto.").apply()}
 }
 override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState)
  val prefs=getSharedPreferences("settings",0)
  if(Build.VERSION.SDK_INT>=30){
   val exit=(getSystemService(ACTIVITY_SERVICE)as ActivityManager).getHistoricalProcessExitReasons(packageName,0,1).firstOrNull()
   if(exit!=null&&exit.reason==ApplicationExitInfo.REASON_USER_REQUESTED&&exit.timestamp>prefs.getLong("processed_user_exit",0)){
    prefs.edit().putBoolean("active",false).putBoolean("pause_pending",true).putLong("processed_user_exit",exit.timestamp).commit()
   }
  }
  setContent{MaterialTheme(colorScheme=darkColorScheme()){Surface(Modifier.fillMaxSize()){
   var consent by remember{mutableStateOf(prefs.getBoolean("consent",false))}
   var status by remember{mutableStateOf<JSONObject?>(null)};var code by remember{mutableStateOf("")};var message by remember{mutableStateOf("")};var qr by remember{mutableStateOf<Bitmap?>(null)}
   var active by remember{mutableStateOf(prefs.getBoolean("active",false))};var busy by remember{mutableStateOf(false)}
   val scope=rememberCoroutineScope();val api=remember{Api(this)}
   fun action(block:suspend()->Unit){scope.launch{busy=true;try{block()}catch(e:Exception){message=e.message?:"Falha"}finally{busy=false}}}
   LaunchedEffect(consent){
    if(consent){
     var retryDelay=5000L
     while(isActive){
      try{
       status=withContext(Dispatchers.IO){
        api.install()
        if(prefs.getBoolean("pause_pending",false)){
         api.call("/device/settings","PATCH",JSONObject().put("enabled",false).put("interval",prefs.getInt("interval",60)))
         prefs.edit().putBoolean("pause_pending",false).apply()
        }
        api.call("/device/status")
       }
       active=prefs.getBoolean("active",false);message="Conectado ao servidor";retryDelay=5000L
      }catch(e:Exception){message="Sem conexão: ${e.message}. Tentando novamente automaticamente.";retryDelay=(retryDelay*2).coerceAtMost(60000L)}
      delay(retryDelay)
     }
    }
   }
   Column(Modifier.padding(24.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)){
    Text("◉ Rastrear MB",style=MaterialTheme.typography.headlineLarge);Text("SetRastrear • controle e transparência")
    Text("Este aplicativo permite compartilhar a localização deste dispositivo com uma conta Rastrear MB. A localização somente será compartilhada depois da autorização do usuário.")
    Text("A conexão com o servidor é configurada automaticamente. Você mantém o controle para autorizar, pausar e remover o vínculo.")
    if(!consent)Button(enabled=!busy,onClick={consent=true;prefs.edit().putBoolean("consent",true).apply()}){Text("CONCORDO E DESEJO CONTINUAR")}
    if(consent){
     Text("Vincular dispositivo",style=MaterialTheme.typography.titleLarge)
     Button(enabled=!busy&&status?.optBoolean("linked")!=true,onClick={action{val p=withContext(Dispatchers.IO){api.install();api.call("/device/pairing","POST")};code=p.getString("code");qr=null;message="Código sem expiração. Válido até uso, recusa ou geração de outro código."}}){Text("VINCULAR DISPOSITIVO / GERAR CÓDIGO")}
     if(code.isNotEmpty()){Text("Código deste dispositivo:\n$code",style=MaterialTheme.typography.titleMedium)
      Button(onClick={(getSystemService(CLIPBOARD_SERVICE)as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Código de pareamento",code))}){Text("COPIAR CÓDIGO")}
      Button(onClick={val matrix=MultiFormatWriter().encode(code,BarcodeFormat.QR_CODE,512,512);qr=Bitmap.createBitmap(512,512,Bitmap.Config.ARGB_8888).apply{for(x in 0..511)for(y in 0..511)setPixel(x,y,if(matrix[x,y])android.graphics.Color.BLACK else android.graphics.Color.WHITE)}}){Text("GERAR QR CODE")}
      qr?.let{Image(it.asImageBitmap(),"QR de pareamento",Modifier.size(240.dp))}
     }
     val pending=status?.optJSONObject("pending")
     if(pending!=null){Card{Column(Modifier.padding(16.dp)){Text(pending.optString("name")+" deseja vincular este dispositivo à conta Rastrear MB.")
      for(allow in listOf(false,true))Button(enabled=!busy,onClick={action{withContext(Dispatchers.IO){api.call("/devices/pair/confirm","POST",JSONObject().put("pairing_id",pending.getString("id")).put("authorize",allow))};status=withContext(Dispatchers.IO){api.call("/device/status")};code="";qr=null}}){Text(if(allow)"AUTORIZAR" else "RECUSAR")}
     }}}
     if(status?.optBoolean("linked")==true){Text("Conta vinculada: "+status?.optString("account"));Text("Compartilhamento: "+if(active)"ATIVADO" else "DESATIVADO")
      Text("Último envio: "+prefs.getString("last","Nenhum"))
      Text("Compartilhamento contínuo, sem prazo automático, inclusive com a tela bloqueada. Depende de bateria, internet, permissões e regras do Android.")
      if(active){val elapsed=SystemClock.elapsedRealtime()-prefs.getLong("service_heartbeat",0);if(elapsed !in 0..120000)Text("Verifique se a notificação está visível. Se o Android encerrou o serviço, toque em ATIVAR para retomar.")}
      var resumeAfterBoot by remember{mutableStateOf(prefs.getBoolean("resume_after_boot",false))}
      Row{Checkbox(resumeAfterBoot,onCheckedChange={resumeAfterBoot=it;prefs.edit().putBoolean("resume_after_boot",it).apply()});Text("Retomar após reiniciar, se o compartilhamento já estava ativo",modifier=Modifier.weight(1f))}
      if(resumeAfterBoot)Text("Opção adicional: nas permissões do Android, escolha Localização → Permitir o tempo todo. A retomada mostra a notificação e não ocorre depois de pausar ou forçar a parada.")
      Button(onClick={startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:$packageName")))}){Text("PERMISSÕES E BATERIA DO APLICATIVO")}
      Text("Para reduzir interrupções, nas configurações do Android escolha Bateria → Sem restrições, se disponível. Nenhuma configuração é alterada automaticamente.")
      prefs.getString("sharing_error",null)?.let{Text(it)}
      var interval by remember{mutableStateOf(60)}
      Text("Atualizações frequentes aumentam o consumo de bateria.")
      for((seconds,label) in listOf(5 to "Tempo real (melhor esforço, 5 s)",30 to "30 segundos",60 to "1 minuto",300 to "5 minutos",600 to "10 minutos",900 to "15 minutos",1800 to "30 minutos",0 to "Somente quando solicitado")){
       Row{RadioButton(interval==seconds,onClick={interval=seconds});Text(label,modifier=Modifier.padding(top=12.dp))}
      }
      Button(enabled=!busy,onClick={action{withContext(Dispatchers.IO){api.call("/device/settings","PATCH",JSONObject().put("enabled",true).put("interval",interval))};val perms=mutableListOf(Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION);if(Build.VERSION.SDK_INT>=33)perms.add(Manifest.permission.POST_NOTIFICATIONS);permission.launch(perms.toTypedArray())}}){Text("ATIVAR COMPARTILHAMENTO")}
      Button(enabled=!busy,onClick={prefs.edit().putBoolean("active",false).putBoolean("pause_pending",true).commit();stopService(Intent(this@MainActivity,LocationService::class.java));active=false;action{withContext(Dispatchers.IO){api.call("/device/settings","PATCH",JSONObject().put("enabled",false).put("interval",interval))};prefs.edit().putBoolean("pause_pending",false).apply();message="Compartilhamento pausado"}}){Text("PAUSAR COMPARTILHAMENTO")}
      Button(enabled=!busy,onClick={action{withContext(Dispatchers.IO){api.call("/device/link","DELETE")};stopService(Intent(this@MainActivity,LocationService::class.java));prefs.edit().putBoolean("active",false).apply();Vault(this@MainActivity).clear();status=null;active=false;message="Vínculo removido e credencial invalidada"}}){Text("REMOVER VÍNCULO E HISTÓRICO")}
     }
    }
    if(busy)LinearProgressIndicator();Text(message)
   }
  }}}
 }
}
