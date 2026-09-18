package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AccountSummary(val available:Double,val invested:Double,val total:Double)

class AccountRepository(private val context:Context){
    suspend fun summary():Result<AccountSummary> = withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                ?: return@withContext Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val con=URL(AuthRepository.API_BASE_URL+"/api/account/summary").openConnection() as HttpURLConnection
            con.requestMethod="GET"
            con.connectTimeout=12000
            con.readTimeout=12000
            con.setRequestProperty("Authorization","Bearer $token")
            val code=con.responseCode
            val stream=if(code in 200..299)con.inputStream else con.errorStream
            val body=stream?.bufferedReader()?.use{it.readText()}?:""
            con.disconnect()
            if(code !in 200..299)return@withContext Result.failure(IllegalStateException("ACCOUNT_UNAVAILABLE"))
            val j=JSONObject(body)
            Result.success(AccountSummary(j.optDouble("availableBalance",0.0),j.optDouble("investedBalance",0.0),j.optDouble("totalBalance",0.0)))
        }catch(e:Exception){Result.failure(e)}
    }
}
