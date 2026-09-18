package com.asterfinancials.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(
    repository:AuthRepository,
    onAuthenticated:(AsterUser)->Unit
){
    var register by remember{mutableStateOf(false)}
    var forgot by remember{mutableStateOf(false)}
    var fullName by remember{mutableStateOf("")}
    var email by remember{mutableStateOf("")}
    var password by remember{mutableStateOf("")}
    var confirm by remember{mutableStateOf("")}
    var busy by remember{mutableStateOf(false)}
    var error by remember{mutableStateOf<String?>(null)}
    val scope=rememberCoroutineScope()

    Column(
        Modifier.fillMaxSize().padding(22.dp),
        horizontalAlignment=Alignment.CenterHorizontally
    ){
        Spacer(Modifier.height(30.dp))
        Box(Modifier.size(58.dp).padding(1.dp),contentAlignment=Alignment.Center){
            Text("A",color=Gold,fontSize=34.sp,fontWeight=FontWeight.Black)
        }
        Text("ASTER",color=Gold,fontSize=13.sp,fontWeight=FontWeight.Bold,letterSpacing=3.sp)
        Text(
            if(forgot)"Reset your password" else if(register)"Create your Aster account" else "Welcome back",
            fontSize=24.sp,fontWeight=FontWeight.Bold,
            modifier=Modifier.padding(top=18.dp)
        )
        Text(
            if(forgot)"Enter your email and we'll send reset instructions."
            else if(register)"Your account will be the gateway to balances, investments and funding."
            else "Sign in to access your verified account data.",
            color=Muted,fontSize=10.sp
        )

        if(!forgot) Row(Modifier.padding(top=18.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
            FilterChip(selected=!register,onClick={register=false},label={Text("Sign in",fontSize=10.sp)})
            FilterChip(selected=register,onClick={register=true},label={Text("Create account",fontSize=10.sp)})
        }

        if(register && !forgot){
            OutlinedTextField(fullName,{fullName=it},Modifier.fillMaxWidth().padding(top=18.dp),label={Text("Full name")},singleLine=true,leadingIcon={Icon(Icons.Default.Person,null)})
        }
        OutlinedTextField(email,{email=it},Modifier.fillMaxWidth().padding(top=10.dp),label={Text("Email")},singleLine=true)
        if(!forgot) OutlinedTextField(
            password,{password=it},Modifier.fillMaxWidth().padding(top=10.dp),
            label={Text("Password")},singleLine=true,
            leadingIcon={Icon(Icons.Default.Lock,null)},
            visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation()
        )
        if(register && !forgot){
            OutlinedTextField(
                confirm,{confirm=it},Modifier.fillMaxWidth().padding(top=10.dp),
                label={Text("Confirm password")},singleLine=true,
                visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation()
            )
        }

        error?.let{Text(it,color=Color(0xFFFF5C62),fontSize=10.sp,modifier=Modifier.padding(top=10.dp))}

        Button(
            enabled=!busy,
            onClick={
                error=null
                busy=true
                scope.launch{
                    if(forgot){
                        val result=repository.forgotPassword(email)
                        busy=false
                        result.onSuccess{error="If an account exists, reset instructions have been sent."}
                            .onFailure{error=it.message?:"Could not connect to Aster."}
                    }else{
                        if(register && password!=confirm){busy=false;error="Passwords do not match";return@launch}
                        if(password.length<8){busy=false;error="Use at least 8 characters";return@launch}
                        val result=if(register) repository.register(fullName,email,password) else repository.login(email,password)
                        busy=false
                        result.onSuccess(onAuthenticated).onFailure{error=it.message?:"Could not connect to Aster."}
                    }
                }
            },
            Modifier.fillMaxWidth().padding(top=14.dp),
            colors=ButtonDefaults.buttonColors(Gold)
        ){
            Text(if(busy)"Connecting…" else if(forgot)"Send reset email" else if(register)"Create account" else "Sign in",color=Color.Black,fontWeight=FontWeight.Bold)
        }

        if(!register && !forgot){
            Text("Forgot password?",color=Gold,fontSize=10.sp,modifier=Modifier.padding(top=14.dp).clickable{forgot=true;error=null})
        }
        if(forgot){
            Text("Back to sign in",color=Gold,fontSize=10.sp,modifier=Modifier.padding(top=14.dp).clickable{forgot=false;error=null})
        }
        Row(Modifier.padding(top=18.dp),verticalAlignment=Alignment.CenterVertically){
            Icon(Icons.Default.Security,null,tint=Gold,modifier=Modifier.size(16.dp))
            Spacer(Modifier.width(6.dp))
            Text("Authentication uses the Aster HTTPS API.",color=Muted,fontSize=8.sp)
        }
    }
}
