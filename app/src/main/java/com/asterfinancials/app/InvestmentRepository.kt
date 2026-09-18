package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class Investment(val id:String,val category:String,val principal:Double,val currentValue:Double,val rate:Double,val compounding:Boolean,val status:String)

class InvestmentRepository(private val context:Context){
    suspend fun create(category:String,principal:String,rate:String,compounding:Boolean=true):Result<Investment> = withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                ?: return@withContext Result.failure(IllegalStateException("Please sign in first."))
            val con=URL(AuthRepository.API_BASE_URL+"/api/investments").openConnection() as HttpURLConnection
            con.requestMethod="POST"; con.connectTimeout=12000; con.readTimeout=12000; con.doOutput=true
            con.setRequestProperty("Content-Type","application/json"); con.setRequestProperty("Authorization","Bearer $token")
            val body=JSONObject().apply{put("category",category);put("principal",principal);put("projectionRate",rate.toDoubleOrNull()?:0.0);put("compounding",compounding)}
            con.outputStream.use{it.write(body.toString().toByteArray())}
            val code=con.responseCode
            val stream=if(code in 200..299)con.inputStream else con.errorStream
            val text=stream?.bufferedReader()?.use{it.readText()}?:""
            con.disconnect()
            val j=JSONObject(text.ifBlank{"{}"})
            if(code !in 200..299) return@withContext Result.failure(IllegalStateException(j.optString("message",j.optString("error","Investment could not be activated."))))
            val o=j.getJSONObject("investment")
            Result.success(Investment(o.getString("id"),o.getString("category"),o.getDouble("principal"),o.getDouble("currentValue"),o.optDouble("projectionRate",0.0),o.optBoolean("compounding",true),o.getString("status")))
        }catch(e:Exception){Result.failure(e)}
    }
}
