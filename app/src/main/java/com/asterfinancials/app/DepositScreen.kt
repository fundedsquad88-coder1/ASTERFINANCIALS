package com.asterfinancials.app

import android.content.ClipData
import android.content.Context
import android.content.ClipboardManager
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.QrCode2
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private data class WalletOption(val network:String,val address:String)

@Composable
fun DepositScreen(onBack:()->Unit){
    var network by remember{mutableStateOf("TRC-20")}
    var amount by remember{mutableStateOf("")}
    var txHash by remember{mutableStateOf("")}
    var wallets by remember{mutableStateOf(emptyList<WalletOption>())}
    var status by remember{mutableStateOf<String?>(null)}
    var loading by remember{mutableStateOf(true)}
    var submitting by remember{mutableStateOf(false)}
    val scope=rememberCoroutineScope()

    LaunchedEffect(Unit){
        wallets=loadWallets()
        loading=false
    }

    val selected=wallets.firstOrNull{it.network==network}
    val context=androidx.compose.ui.platform.LocalContext.current

    Column(Modifier.fillMaxSize()){
        Row(Modifier.padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            Text("‹",fontSize=30.sp,color=Gold)
            Spacer(Modifier.width(8.dp))
            Column(Modifier.weight(1f)){
                Text("Deposit USDT",fontSize=20.sp,fontWeight=FontWeight.Bold)
                Text("Fund your Aster account",color=Muted,fontSize=9.sp)
            }
            IconButton({scope.launch{loading=true;wallets=loadWallets();loading=false}}){
                Icon(Icons.Default.Refresh,null,tint=Gold)
            }
        }

        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=16.dp)){
            Text("NETWORK",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
            Row(Modifier.padding(top=8.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                listOf("TRC-20","BEP-20").forEach{n->
                    FilterChip(selected=network==n,onClick={network=n},label={Text(n,fontSize=10.sp)})
                }
            }

            CardBox(Modifier.fillMaxWidth().padding(top=14.dp)){
                Column(Modifier.padding(16.dp),horizontalAlignment=Alignment.CenterHorizontally){
                    Icon(Icons.Default.QrCode2,null,tint=Gold,modifier=Modifier.size(80.dp))
                    Text(if(loading)"Loading deposit address…" else selected?.address ?: "Wallet not configured",fontSize=10.sp,fontWeight=FontWeight.Bold)

                    Text("Only send USDT on the selected network.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=5.dp))
                    if(selected!=null){
                        OutlinedButton(onClick={
                            selected?.let{
                                val clip=context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                clip.setPrimaryClip(ClipData.newPlainText("Aster $network address",it.address))
                                status="Address copied."
                            }
                        }){ 
                            Icon(Icons.Default.ContentCopy,null,Modifier.size(15.dp))
                            Spacer(Modifier.width(5.dp))
                            Text("Copy address",fontSize=9.sp)
                        }
                    }
                }
            }

            OutlinedTextField(amount,{amount=it},Modifier.fillMaxWidth().padding(top=12.dp),label={Text("Amount (USDT)")},singleLine=true)
            OutlinedTextField(txHash,{txHash=it},Modifier.fillMaxWidth().padding(top=8.dp),label={Text("Transaction hash (optional)")},singleLine=true)

            Text("After sending the funds, submit the transaction hash when available. Your balance changes only after server-side verification.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=10.dp))

            status?.let{Text(it,color=if(it.startsWith("Submitted"))Green else Gold,fontSize=10.sp,modifier=Modifier.padding(top=10.dp))}

            Button(
                enabled=!submitting && selected!=null,
                onClick={
                    submitting=true; status=null
                    scope.launch{
                        status=submitDeposit(network,amount,txHash)
                        submitting=false
                    }
                },
                Modifier.fillMaxWidth().padding(top=14.dp),
                colors=ButtonDefaults.buttonColors(Gold)
            ){
                Text(if(submitting)"Submitting…" else "Submit deposit",color=Color.Black,fontWeight=FontWeight.Bold)
            }

            Spacer(Modifier.height(24.dp))
        }
    }
}

private suspend fun loadWallets():List<WalletOption>{
    return withContext(Dispatchers.IO){
        listOf(
            WalletOption("TRC-20","TMrK4d1r2cGye2TwX3JfjCaUDWvZy6aoXD"),
            WalletOption("BEP-20","0xAf37c145EE58C0C0bD281BF454Ee92beC93F13d5")
        )
    }
}

private suspend fun submitDeposit(network:String,amount:String,txHash:String):String{
    if(amount.toDoubleOrNull()==null || amount.toDoubleOrNull()!!<=0) return "Enter a valid USDT amount."
    return "Deposit submission is waiting for the deployed Aster API."
}
