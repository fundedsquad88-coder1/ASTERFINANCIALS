package com.asterfinancials.app

import android.content.Context
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
    }

    fun currentUser():AsterUser?{
        val p=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        val id=p.getString(USER_ID,null)?:return null
        val email=p.getString(USER_EMAIL,null)?:return null
        val name=p.getString(USER_NAME,null)?:return null
        if(p.getString(TOKEN,null).isNullOrBlank())return null
        return AsterUser(id,email,name)
    }

    fun logout(){
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().clear().apply()
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
                    save(json.getString("accessToken"),user)
                    Result.success(user)
                }
            }catch(e:Exception){
                Result.failure(e)
            }
        }
    }

    private fun save(token:String,user:AsterUser){
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit()
            .putString(TOKEN,token)
            .putString(USER_ID,user.id)
            .putString(USER_EMAIL,user.email)
            .putString(USER_NAME,user.fullName)
            .apply()
    }
}
