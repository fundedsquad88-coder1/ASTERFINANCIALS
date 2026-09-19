package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class DepositRecord(val id:String,val network:String,val amount:Double,val txHash:String,val status:String,val confirmations:Int,val submittedAt:String,val verifiedAt:String?,val rejectionReason:String?)
data class WithdrawalRecord(val id:String,val network:String,val destinationAddress:String,val amount:Double,val feeAmount:Double,val netAmount:Double,val status:String,val requestedAt:String,val approvedAt:String?,val completedAt:String?,val txHash:String?,val rejectionReason:String?)

class FundingHistoryRepository(private val context:Context){
    private fun token()=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
    suspend fun deposits():Result<List<DepositRecord>>=get("/api/funding/deposits"){a->
        buildList{for(i in 0 until a.length()){val j=a.getJSONObject(i);add(DepositRecord(j.getString("id"),j.getString("network"),j.optDouble("amount",0.0),j.optString("txHash"),j.optString("status"),j.optInt("confirmations",0),j.optString("submittedAt"),j.optString("verifiedAt").takeIf{it.isNotBlank()&&it!="null"},j.optString("rejectionReason").takeIf{it.isNotBlank()&&it!="null"}))}}
    }
    suspend fun withdrawals():Result<List<WithdrawalRecord>>=get("/api/funding/withdrawals"){a->
        buildList{for(i in 0 until a.length()){val j=a.getJSONObject(i);add(WithdrawalRecord(j.getString("id"),j.optString("network"),j.optString("destinationAddress"),j.optDouble("amount",0.0),j.optDouble("feeAmount",0.0),j.optDouble("netAmount",0.0),j.optString("status"),j.optString("requestedAt"),j.optString("approvedAt").takeIf{it.isNotBlank()&&it!="null"},j.optString("completedAt").takeIf{it.isNotBlank()&&it!="null"},j.optString("txHash").takeIf{it.isNotBlank()&&it!="null"},j.optString("rejectionReason").takeIf{it.isNotBlank()&&it!="null"}))}}
    }
    private suspend fun <T> get(path:String,parse:(org.json.JSONArray)->T):Result<T>=withContext(Dispatchers.IO){
        try{
            val t=token()?:return@withContext Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val c=URL(AuthRepository.API_BASE_URL+path).openConnection() as HttpURLConnection
            c.requestMethod="GET";c.connectTimeout=12000;c.readTimeout=12000;c.setRequestProperty("Authorization","Bearer "+t)
            val code=c.responseCode;val body=(if(code in 200..299)c.inputStream else c.errorStream)?.bufferedReader()?.use{it.readText()}?:"";c.disconnect()
            if(code !in 200..299)return@withContext Result.failure(IllegalStateException(JSONObject(body.ifBlank{"{}"}).optString("message","Funding history unavailable.")))
            val key=if(path.contains("deposits"))"deposits" else "withdrawals"
            Result.success(parse(JSONObject(body).optJSONArray(key)?:org.json.JSONArray()))
        }catch(e:Exception){Result.failure(e)}
    }
}
