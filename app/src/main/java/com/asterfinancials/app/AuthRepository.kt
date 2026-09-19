package com.asterfinancials.app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.security.KeyStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AsterUser(val id:String,val email:String,val fullName:String)

class AuthRepository(private val context:Context){
    companion object {
        // Replace with the deployed HTTPS Aster API URL before production release.
        const val API_BASE_URL = "https://api.asterfinancials.com"
        private const val PREFS = "aster_auth"
        private const val TOKEN = "access_token"
        private const val USER_ID = "user_id"
        private const val USER_EMAIL = "user_email"
        private const val USER_NAME = "user_name"
        private const val REFRESH = "refresh_token"
        private const val KEY_ALIAS = "aster_auth_key"
    }

    fun currentUser():AsterUser?{
        val p=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        val id=p.getString(USER_ID,null)?:return null
        val email=p.getString(USER_EMAIL,null)?:return null
        val name=p.getString(USER_NAME,null)?:return null
        if(p.getString(TOKEN,null).isNullOrBlank() && secureGet(REFRESH).isNullOrBlank())return null
        return AsterUser(id,email,name)
    }

    fun logout(){
        val refresh=secureGet(REFRESH)
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().clear().apply()
        if(!refresh.isNullOrBlank()) kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            try{
                val con=URL(API_BASE_URL+"/api/auth/logout").openConnection() as HttpURLConnection
                con.requestMethod="POST"; con.doOutput=true; con.setRequestProperty("Content-Type","application/json")
                con.outputStream.use{it.write(JSONObject().put("refreshToken",refresh).toString().toByteArray())}; con.responseCode; con.disconnect()
            }catch(_:Exception){}
        }
    }

    suspend fun register(fullName:String,email:String,password:String):Result<AsterUser>{
        return request("/api/auth/register",JSONObject().apply{
            put("fullName",fullName)
            put("email",email)
            put("password",password)
        })
    }

    suspend fun login(email:String,password:String):Result<AsterUser>{
        return request("/api/auth/login",JSONObject().apply{
            put("email",email)
            put("password",password)
        })
    }

    suspend fun forgotPassword(email:String):Result<Boolean>{
        return withContext(Dispatchers.IO){
            try{
                val con=URL(API_BASE_URL+"/api/auth/forgot-password").openConnection() as HttpURLConnection
                con.requestMethod="POST"
                con.connectTimeout=12000
                con.readTimeout=12000
                con.doOutput=true
                con.setRequestProperty("Content-Type","application/json")
                con.outputStream.use{it.write(JSONObject().put("email",email).toString().toByteArray())}
                val ok=con.responseCode in 200..299
                con.disconnect()
                if(ok) Result.success(true) else Result.failure(IllegalStateException("Could not process the request."))
            }catch(e:Exception){Result.failure(e)}
        }
    }

    suspend fun refresh():Result<AsterUser>{
        val refresh=secureGet(REFRESH)?:return Result.failure(IllegalStateException("SESSION_EXPIRED"))
        return request("/api/auth/refresh",JSONObject().put("refreshToken",refresh))
    }

    private suspend fun request(path:String,body:JSONObject):Result<AsterUser>{
        return withContext(Dispatchers.IO){
            try{
                val con=URL(API_BASE_URL+path).openConnection() as HttpURLConnection
                con.requestMethod="POST"
                con.connectTimeout=12000
                con.readTimeout=12000
                con.doOutput=true
                con.setRequestProperty("Content-Type","application/json")
                con.setRequestProperty("Accept","application/json")
                con.outputStream.use{it.write(body.toString().toByteArray())}
                val code=con.responseCode
                val stream=if(code in 200..299) con.inputStream else con.errorStream
                val text=stream?.bufferedReader()?.use{it.readText()}?:""
                con.disconnect()
                val json=if(text.isBlank()) JSONObject() else JSONObject(text)
                if(code !in 200..299){
                    Result.failure(IllegalStateException(json.optString("message",json.optString("error","Request failed"))))
                }else{
                    val u=json.getJSONObject("user")
                    val user=AsterUser(u.getString("id"),u.getString("email"),u.getString("fullName"))
                    save(json.getString("accessToken"),json.optString("refreshToken",""),user)
                    Result.success(user)
                }
            }catch(e:Exception){
                Result.failure(e)
            }
        }
    }

    private fun save(token:String,refresh:String,user:AsterUser){
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit()
            .putString(TOKEN,token)
            .putString(USER_ID,user.id)
            .putString(USER_EMAIL,user.email)
            .putString(USER_NAME,user.fullName)
            .apply()
        if(refresh.isNotBlank()) securePut(REFRESH,refresh)
    private fun key():SecretKey{
        val ks=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        val existing=ks.getKey(KEY_ALIAS,null)
        if(existing is SecretKey)return existing
        val kg=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        kg.init(KeyGenParameterSpec.Builder(KEY_ALIAS,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        return kg.generateKey()
    }
    private fun securePut(name:String,value:String){
        val cipher=Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE,key())
        val iv=Base64.encodeToString(cipher.iv,Base64.NO_WRAP)
        val data=Base64.encodeToString(cipher.doFinal(value.toByteArray(Charsets.UTF_8)),Base64.NO_WRAP)
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(name,iv+"."+data).apply()
    }
    private fun secureGet(name:String):String?{
        return try{
            val raw=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(name,null) ?: return null
            val parts=raw.split(".")
            if(parts.size!=2)return null
            val cipher=Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(parts[0],Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(parts[1],Base64.NO_WRAP)),Charsets.UTF_8)
        }catch(_:Exception){null}
    }
}
}