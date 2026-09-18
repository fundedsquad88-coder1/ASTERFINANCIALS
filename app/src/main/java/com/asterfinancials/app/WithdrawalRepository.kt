package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class WithdrawalRepository(private val context:Context){
    suspend fun request(network:String,address:String,amount:String,investmentId:String?=null):Result<String> =
        withContext(Dispatchers.IO){
            try{
                val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                    ?: return@withContext Result.failure(IllegalStateException("Please sign in first."))
                val con=URL(AuthRepository.API_BASE_URL+"/api/funding/withdrawals").openConnection() as HttpURLConnection
                con.requestMethod="POST"; con.connectTimeout=12000; con.readTimeout=12000; con.doOutput=true
                con.setRequestProperty("Content-Type","application/json")
                con.setRequestProperty("Authorization","Bearer $token")
                val body=JSONObject().apply{
                    put("network",network);put("destinationAddress",address);put("amount",amount)
                    if(!investmentId.isNullOrBlank())put("investmentId",investmentId)
                }
                con.outputStream.use{it.write(body.toString().toByteArray())}
                val code=con.responseCode
                val stream=if(code in 200..299)con.inputStream else con.errorStream
                val text=stream?.bufferedReader()?.use{it.readText()}?:""
                con.disconnect()
                val json=JSONObject(text.ifBlank{"{}"})
                if(code !in 200..299) Result.failure(IllegalStateException(json.optString("message",json.optString("error","Withdrawal could not be requested."))))
                else Result.success("Withdrawal request submitted — pending review.")
            }catch(e:Exception){Result.failure(e)}
        }
}
