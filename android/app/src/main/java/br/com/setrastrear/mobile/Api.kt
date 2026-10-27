package br.com.setrastrear.mobile
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.spec.GCMParameterSpec

class Vault(c:Context) {
 private val prefs=c.getSharedPreferences("private",Context.MODE_PRIVATE)
 private val key=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}.let { ks ->
  if(!ks.containsAlias("rmb")) KeyGenerator.getInstance("AES","AndroidKeyStore").apply{init(KeyGenParameterSpec.Builder("rmb",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes("GCM").setEncryptionPaddings("NoPadding").build());generateKey()}
  ks.getKey("rmb",null)
 }
 fun get():String {val v=prefs.getString("token",null)?:return "";return try {val parts=v.split(":");Cipher.getInstance("AES/GCM/NoPadding").run{init(Cipher.DECRYPT_MODE,key,GCMParameterSpec(128,Base64.decode(parts[0],0)));String(doFinal(Base64.decode(parts[1],0)))}}catch(e:Exception){""}}
 fun set(value:String){val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key);prefs.edit().putString("token",Base64.encodeToString(cipher.iv,2)+":"+Base64.encodeToString(cipher.doFinal(value.toByteArray()),2)).apply()}
 fun clear(){prefs.edit().remove("token").apply()}
}
class Api(private val c:Context){
 private val prefs=c.getSharedPreferences("settings",0)
 companion object { private val installLock=Any() }
 private fun baseUrl():String {
  val base=BuildConfig.SERVER_URL
  require(base.isNotEmpty()) { "Servidor não configurado nesta versão. Instale o APK fornecido pelo operador." }
  synchronized(installLock) {
   val previous=prefs.getString("token_origin",prefs.getString("url",""))
   if(previous!=base){Vault(c).clear();prefs.edit().putBoolean("active",false).apply()}
   prefs.edit().putString("token_origin",base).remove("url").apply()
  }
  return base
 }
 fun call(path:String,method:String="GET",data:JSONObject?=null):JSONObject {
  val base=baseUrl()
  require(base.startsWith("https://")){"Use uma URL HTTPS com certificado confiável"}
  val conn=URL(base+"/api"+path).openConnection() as HttpsURLConnection
  try {conn.requestMethod=method;conn.connectTimeout=15000;conn.readTimeout=15000;conn.setRequestProperty("Content-Type","application/json")
   val token=Vault(c).get();if(token.isNotEmpty())conn.setRequestProperty("Authorization","Bearer $token")
   if(data!=null){conn.doOutput=true;conn.outputStream.use{it.write(data.toString().toByteArray())}}
   val code=conn.responseCode
   if(code !in 200..299){val message=conn.errorStream?.bufferedReader()?.use{it.readText()}?:"HTTP $code";if(code==401){Vault(c).clear();prefs.edit().putBoolean("active",false).apply()};throw IllegalStateException(message)}
   return JSONObject(conn.inputStream.bufferedReader().use{it.readText()})
  } finally {conn.disconnect()}
 }
 fun install(){synchronized(installLock){baseUrl();if(Vault(c).get().isEmpty())Vault(c).set(call("/device/install","POST").getString("device_token"))}}
}
