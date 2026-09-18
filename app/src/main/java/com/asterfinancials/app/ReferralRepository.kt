package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ReferralSummary(val code:String?,val invited:Int,val earned:Double,val paidRewards:Int,val rate:Double)

class ReferralRepository(private val context:Context){
    suspend fun summary():Result<ReferralSummary> = withContext(Dispatchers.IO){
        try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                ?: return@withContext Result.failure(IllegalStateException("Please sign in first."))
            val con=URL(AuthRepository.API_BASE_URL+"/api/referrals/summary").openConnection() as HttpURLConnection
            con.requestMethod="GET";con.connectTimeout=12000;con.readTimeout=12000
            con.setRequestProperty("Authorization","Bearer $token")
            val code=con.responseCode
            val body=(if(code in 200..299)con.inputStream else con.errorStream)?.bufferedReader()?.use{it.readText()}?:""
            con.disconnect()
            if(code !in 200..299)return@withContext Result.failure(IllegalStateException("Referral data unavailable."))
            val j=JSONObject(body)
            Result.success(ReferralSummary(j.optString("referralCode",null),j.optInt("invited",0),j.optDouble("earned",0.0),j.optInt("paidRewards",0),j.optDouble("rate",0.15)))
        }catch(e:Exception){Result.failure(e)}
    }
}
