package com.asterfinancials.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class DepositRecord(
    val id:String,val network:String,val amount:Double,val txHash:String,val status:String,
    val confirmations:Int,val submittedAt:String,val verifiedAt:String?,val rejectionReason:String?
)
data class WithdrawalRecord(
    val id:String,val network:String,val destinationAddress:String,val amount:Double,val feeAmount:Double,
    val netAmount:Double,val status:String,val requestedAt:String,val approvedAt:String?,
    val completedAt:String?,val txHash:String?,val rejectionReason:String?
)

class FundingHistoryRepository(private val context:Context){
    suspend fun deposits():Result<List<DepositRecord>> = withContext(Dispatchers.IO){
        request("/api/funding/deposits","deposits"){arr->
            val out=mutableListOf<DepositRecord>()
            for(i in 0 until arr.length()){
                val j=arr.getJSONObject(i)
                out.add(DepositRecord(
                    j.optString("id"),j.optString("network"),j.optDouble("amount",0.0),j.optString("txHash"),
                    j.optString("status"),j.optInt("confirmations",0),j.optString("submittedAt"),
                    j.optString("verifiedAt").takeIf{it.isNotBlank()&&it!="null"},
                    j.optString("rejectionReason").takeIf{it.isNotBlank()&&it!="null"}
                ))
            }
            out
        }
    }

    suspend fun withdrawals():Result<List<WithdrawalRecord>> = withContext(Dispatchers.IO){
        request("/api/funding/withdrawals","withdrawals"){arr->
            val out=mutableListOf<WithdrawalRecord>()
            for(i in 0 until arr.length()){
                val j=arr.getJSONObject(i)
                out.add(WithdrawalRecord(
                    j.optString("id"),j.optString("network"),j.optString("destinationAddress"),
                    j.optDouble("amount",0.0),j.optDouble("feeAmount",0.0),j.optDouble("netAmount",0.0),
                    j.optString("status"),j.optString("requestedAt"),
                    j.optString("approvedAt").takeIf{it.isNotBlank()&&it!="null"},
                    j.optString("completedAt").takeIf{it.isNotBlank()&&it!="null"},
                    j.optString("txHash").takeIf{it.isNotBlank()&&it!="null"},
                    j.optString("rejectionReason").takeIf{it.isNotBlank()&&it!="null"}
                ))
            }
            out
        }
    }

    private suspend fun <T> request(path:String,key:String,parse:(JSONArray)->T):Result<T>{
        return try{
            val token=context.getSharedPreferences("aster_auth",Context.MODE_PRIVATE).getString("access_token",null)
                ?: return Result.failure(IllegalStateException("SIGN_IN_REQUIRED"))
            val con=URL(AuthRepository.API_BASE_URL+path).openConnection() as HttpURLConnection
            con.requestMethod="GET"; con.connectTimeout=12000; con.readTimeout=12000
            con.setRequestProperty("Authorization","Bearer "+token)
            val code=con.responseCode
            val body=(if(code in 200..299)con.inputStream else con.errorStream)?.bufferedReader()?.use{it.readText()}?:""
            con.disconnect()
            if(code !in 200..299) return Result.failure(IllegalStateException(JSONObject(body.ifBlank{"{}"}).optString("message","Funding history unavailable.")))
            Result.success(parse(JSONObject(body).optJSONArray(key)?:JSONArray()))
        }catch(e:Exception){Result.failure(e)}
    }
}
