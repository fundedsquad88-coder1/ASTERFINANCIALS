package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ActivityItem(
    val type:String,
    val amount:Double,
    val currency:String,
    val status:String,
    val createdAt:String
)

class ActivityRepository(private val context:Context){
    suspend fun list():Result<List<ActivityItem>> = withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                ?: return@withContext Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val con=URL(AuthRepository.API_BASE_URL+"/api/account/activity").openConnection() as HttpURLConnection
            con.requestMethod="GET"
            con.connectTimeout=12000
            con.readTimeout=12000
            con.setRequestProperty("Authorization","Bearer $token")
            val code=con.responseCode
            val stream=if(code in 200..299)con.inputStream else con.errorStream
            val body=stream?.bufferedReader()?.use{it.readText()}?:""
            con.disconnect()
            if(code !in 200..299)return@withContext Result.failure(IllegalStateException("ACTIVITY_UNAVAILABLE"))
            val arr=JSONObject(body).optJSONArray("activity")
            val out=mutableListOf<ActivityItem>()
            if(arr!=null)for(i in 0 until arr.length()){
                val j=arr.getJSONObject(i)
                out.add(ActivityItem(
                    j.optString("type"),
                    j.optDouble("amount",0.0),
                    j.optString("currency","USDT"),
                    j.optString("status"),
                    j.optString("createdAt")
                ))
            }
            Result.success(out)
        }catch(e:Exception){Result.failure(e)}
    }
}
