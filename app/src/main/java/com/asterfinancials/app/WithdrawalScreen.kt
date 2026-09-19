package com.asterfinancials.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CurrencyBitcoin
import androidx.compose.material.icons.filled.CurrencyExchange
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@Composable
fun WithdrawalScreen(onBack:()->Unit){
    val context=androidx.compose.ui.platform.LocalContext.current
    val account=remember{AccountRepository(context)}
    val investmentsRepo=remember{InvestmentRepository(context)}
    val repo=remember{WithdrawalRepository(context)}
    val scope=rememberCoroutineScope()
    var available by remember{mutableStateOf(0.0)}
    var investments by remember{mutableStateOf(emptyList<Investment>())}
    var source by remember{mutableStateOf("available")}
    var selectedInvestment by remember{mutableStateOf<Investment?>(null)}
    var network by remember{mutableStateOf("TRC-20")}
    var address by remember{mutableStateOf("")}
    var amount by remember{mutableStateOf("")}
    var message by remember{mutableStateOf<String?>(null)}
    var busy by remember{mutableStateOf(false)}\n    var quote by remember{mutableStateOf<WithdrawalQuote?>(null)}

    LaunchedEffect(Unit){
        available=account.summary().getOrNull()?.available?:0.0
        investments=investmentsRepo.list().getOrElse{emptyList()}.filter{it.status=="active"}
    }

    Column(Modifier.fillMaxSize()){
        Row(Modifier.padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Spacer(Modifier.width(8.dp))
            Column{
                Text("Withdraw USDT",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                Text("Request a transfer from your verified balance",color=Muted,fontSize=9.sp)
            }
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=16.dp)){
            Text("SOURCE",color=Gold,fontSize=9.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
            Row(Modifier.padding(top=8.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                FilterChip(selected=source=="available",onClick={source="available";selectedInvestment=null},label={Text("Available · %.2f".format(available),fontSize=9.sp)})
                FilterChip(selected=source=="investment",onClick={source="investment"},label={Text("Auto-Invest",fontSize=9.sp)})
            }
            if(source=="investment"){
                if(investments.isEmpty()) Text("No active investments available for withdrawal.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=10.dp))
                investments.forEach{inv->
                    CardBox(Modifier.fillMaxWidth().padding(top=6.dp).then(if(selectedInvestment?.id==inv.id)Modifier else Modifier)){
                        Row(Modifier.fillMaxWidth().padding(12.dp),verticalAlignment=Alignment.CenterVertically){
                            Icon(if(inv.category=="crypto")Icons.Default.CurrencyBitcoin else Icons.Default.CurrencyExchange,null,tint=Gold,modifier=Modifier.size(20.dp))
                            Spacer(Modifier.width(8.dp))
                            Column(Modifier.weight(1f)){
                                Text(inv.category.replaceFirstChar{it.uppercase()}+" Auto-Invest",fontSize=11.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                                Text("Current value %.2f USDT".format(inv.currentValue),color=Muted,fontSize=9.sp)
                            }
                            RadioButton(selected=selectedInvestment?.id==inv.id,onClick={selectedInvestment=inv})
                        }
                    }
                }
                Text("Selected investment value: "+(selectedInvestment?.currentValue?.let{"%.2f USDT".format(it)}?:"—")+". Investment withdrawals request the full current value and remain subject to backend review.",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=8.dp))
            }else{
                OutlinedTextField(amount,{amount=it},Modifier.fillMaxWidth().padding(top=10.dp),label={Text("Amount (USDT)")},singleLine=true)
            }

            Text("NETWORK",color=Gold,fontSize=9.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold,modifier=Modifier.padding(top=14.dp))
            Row(Modifier.padding(top=8.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                FilterChip(selected=network=="TRC-20",onClick={network="TRC-20"},label={Text("TRC-20",fontSize=9.sp)})
                FilterChip(selected=network=="BEP-20",onClick={network="BEP-20"},label={Text("BEP-20",fontSize=9.sp)})
            }
            OutlinedTextField(address,{address=it},Modifier.fillMaxWidth().padding(top=10.dp),label={Text("Destination USDT address")},singleLine=true)\n            LaunchedEffect(network,amount){ if(source=="available" && (amount.toDoubleOrNull()?:0.0)>0) quote=repo.quote(network,amount).getOrNull() else quote=null }\n            quote?.let{q-> Text("Fee %.2f%% · %.4f USDT · You receive %.4f USDT".format(q.feeRate*100,q.feeAmount,q.netAmount),color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=7.dp)) }
            Text("Check the destination address and network carefully. Aster does not control an external wallet address entered by the customer.",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=8.dp))
            message?.let{Text(it,color=if(it.startsWith("Withdrawal request"))Green else Gold,fontSize=9.sp,modifier=Modifier.padding(top=10.dp))}
            Button(
                onClick={
                    busy=true;message=null
                    scope.launch{
                        val requestAmount=if(source=="investment") selectedInvestment?.currentValue?.toString() ?: amount else amount\n                        val result=repo.request(network,address,requestAmount,selectedInvestment?.id.takeIf{source=="investment"})
                        busy=false
                        result.onSuccess{message=it}.onFailure{message=it.message?:"Could not submit withdrawal."}
                    }
                },
                modifier=Modifier.fillMaxWidth().padding(top=14.dp),
                enabled=!busy && address.isNotBlank() && (source=="investment" || (amount.toDoubleOrNull()?:0.0)>0),
                colors=ButtonDefaults.buttonColors(Gold)
            ){Text(if(busy)"Submitting…" else "Request withdrawal",color=Color.Black,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)}
            Spacer(Modifier.height(24.dp))
        }
    }
}
