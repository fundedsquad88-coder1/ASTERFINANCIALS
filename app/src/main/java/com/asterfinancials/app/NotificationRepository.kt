package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AsterNotification(val id:String,val category:String,val title:String,val body:String,val readAt:String?,val createdAt:String)

class NotificationRepository(private val context:Context){
    suspend fun list():Result<List<AsterNotification>>=request("/api/notifications","notifications")
    suspend fun read(id:String):Result<Boolean>=post("/api/notifications/$id/read")
    suspend fun readAll():Result<Boolean>=post("/api/notifications/read-all")
    private suspend fun request(path:String,key:String):Result<List<AsterNotification>>=withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)?:return@withContext Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val c=URL(AuthRepository.API_BASE_URL+path).openConnection() as HttpURLConnection
            c.requestMethod="GET";c.connectTimeout=12000;c.readTimeout=12000;c.setRequestProperty("Authorization","Bearer "+token)
            val code=c.responseCode;val body=(if(code in 200..299)c.inputStream else c.errorStream)?.bufferedReader()?.use{it.readText()}?:"";c.disconnect()
            if(code !in 200..299)return@withContext Result.failure(IllegalStateException("NOTIFICATIONS_UNAVAILABLE"))
            val arr=JSONObject(body).optJSONArray(key);val out=mutableListOf<AsterNotification>()
            if(arr!=null)for(i in 0 until arr.length()){val j=arr.getJSONObject(i);out.add(AsterNotification(j.optString("id"),j.optString("category"),j.optString("title"),j.optString("body"),j.optString("readAt").takeIf{it.isNotBlank()&&it!="null"},j.optString("createdAt")))}
            Result.success(out)
        }catch(e:Exception){Result.failure(e)}
    }
    private suspend fun post(path:String):Result<Boolean>=withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)?:return@withContext Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val c=URL(AuthRepository.API_BASE_URL+path).openConnection() as HttpURLConnection
            c.requestMethod="POST";c.connectTimeout=12000;c.readTimeout=12000;c.doOutput=true;c.setRequestProperty("Authorization","Bearer "+token);c.setRequestProperty("Content-Type","application/json")
            val code=c.responseCode;c.disconnect();if(code in 200..299)Result.success(true)else Result.failure(IllegalStateException("NOTIFICATION_UPDATE_FAILED"))
        }catch(e:Exception){Result.failure(e)}
    }
}
