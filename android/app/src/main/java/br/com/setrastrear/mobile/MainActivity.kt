package br.com.setrastrear.mobile
import android.Manifest
import android.os.Bundle
import android.os.Build
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
 private fun startSharing(){if(ContextCompat.checkSelfPermission(this,Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED)return;getSharedPreferences("settings",0).edit().putBoolean("active",true).apply();ContextCompat.startForegroundService(this,Intent(this,LocationService::class.java))}
 override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState)
  val prefs=getSharedPreferences("settings",0)
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
       status=withContext(Dispatchers.IO){api.install();api.call("/device/status")}
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
      var interval by remember{mutableStateOf(60)}
      Text("Atualizações frequentes aumentam o consumo de bateria.")
      for((seconds,label) in listOf(5 to "Tempo real (melhor esforço, 5 s)",30 to "30 segundos",60 to "1 minuto",300 to "5 minutos",600 to "10 minutos",900 to "15 minutos",1800 to "30 minutos",0 to "Somente quando solicitado")){
       Row{RadioButton(interval==seconds,onClick={interval=seconds});Text(label,modifier=Modifier.padding(top=12.dp))}
      }
      Button(enabled=!busy,onClick={action{withContext(Dispatchers.IO){api.call("/device/settings","PATCH",JSONObject().put("enabled",true).put("interval",interval))};val perms=mutableListOf(Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION);if(Build.VERSION.SDK_INT>=33)perms.add(Manifest.permission.POST_NOTIFICATIONS);permission.launch(perms.toTypedArray())}}){Text("ATIVAR COMPARTILHAMENTO")}
      Button(enabled=!busy,onClick={prefs.edit().putBoolean("active",false).apply();stopService(Intent(this@MainActivity,LocationService::class.java));active=false;action{withContext(Dispatchers.IO){api.call("/device/settings","PATCH",JSONObject().put("enabled",false).put("interval",interval))};message="Compartilhamento pausado"}}){Text("PAUSAR COMPARTILHAMENTO")}
      Button(enabled=!busy,onClick={action{withContext(Dispatchers.IO){api.call("/device/link","DELETE")};stopService(Intent(this@MainActivity,LocationService::class.java));prefs.edit().putBoolean("active",false).apply();Vault(this@MainActivity).clear();status=null;active=false;message="Vínculo removido e credencial invalidada"}}){Text("REMOVER VÍNCULO E HISTÓRICO")}
     }
    }
    if(busy)LinearProgressIndicator();Text(message)
   }
  }}}
 }
}
