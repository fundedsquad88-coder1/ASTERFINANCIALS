package com.asterfinancials.app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.NorthEast
import androidx.compose.material.icons.filled.SouthWest
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context

@Composable
fun FundingHistoryScreen(onBack:()->Unit){
    val context=androidx.compose.ui.platform.LocalContext.current
    val repo=remember{FundingHistoryRepository(context)}
    var tab by remember{mutableStateOf(0)}
    var deposits by remember{mutableStateOf(emptyList<DepositRecord>())}
    var withdrawals by remember{mutableStateOf(emptyList<WithdrawalRecord>())}
    var loading by remember{mutableStateOf(true)}
    LaunchedEffect(Unit){ loading=true; deposits=repo.deposits().getOrElse{emptyList()}; withdrawals=repo.withdrawals().getOrElse{emptyList()}; loading=false }
    Column(Modifier.fillMaxSize()){
        Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Column{Text("Funding history",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold);Text("Your deposit and withdrawal records",color=Muted,fontSize=9.sp)}
        }
        TabRow(selectedTabIndex=tab){
            Tab(tab==0,{tab=0},text={Text("Deposits",fontSize=10.sp)})
            Tab(tab==1,{tab=1},text={Text("Withdrawals",fontSize=10.sp)})
        }
        if(loading) Text("Loading funding history…",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else if(tab==0) LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            if(deposits.isEmpty()) item{Text("No deposits submitted yet.",color=Muted,fontSize=10.sp)}
            items(deposits){DepositCard(it)}
        } else LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            if(withdrawals.isEmpty()) item{Text("No withdrawals requested yet.",color=Muted,fontSize=10.sp)}
            items(withdrawals){WithdrawalCard(context,it)}
        }
    }
}

@Composable private fun DepositCard(d:DepositRecord){
    CardBox{
        Column(Modifier.padding(14.dp)){
            Row(verticalAlignment=Alignment.CenterVertically){
                Icon(Icons.Default.SouthWest,null,tint=Gold,modifier=Modifier.size(20.dp));Spacer(Modifier.width(9.dp))
                Column(Modifier.weight(1f)){Text("%.2f USDT".format(d.amount),fontWeight=androidx.compose.ui.text.font.FontWeight.Bold,fontSize=12.sp);Text(d.network,color=Muted,fontSize=8.sp)}
                StatusPill(d.status)
            }
            Text("TXID: "+d.txHash.take(12)+"…",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=8.dp))
            Text(when(d.status){"completed"->"Verified and credited";"confirming"->"Blockchain confirmations in progress";"rejected"->d.rejectionReason?:"Deposit rejected";else->"Submitted — awaiting independent blockchain verification"},color=if(d.status=="completed")Green else Gold,fontSize=9.sp,modifier=Modifier.padding(top=5.dp))
            if(d.confirmations>0)Text("Confirmations: "+d.confirmations,color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=3.dp))
        }
    }
}

@Composable private fun WithdrawalCard(context:Context,w:WithdrawalRecord){
    CardBox{
        Column(Modifier.padding(14.dp)){
            Row(verticalAlignment=Alignment.CenterVertically){
                Icon(Icons.Default.NorthEast,null,tint=Gold,modifier=Modifier.size(20.dp));Spacer(Modifier.width(9.dp))
                Column(Modifier.weight(1f)){Text("%.2f USDT".format(w.amount),fontWeight=androidx.compose.ui.text.font.FontWeight.Bold,fontSize=12.sp);Text(w.network+" · Net %.2f".format(w.netAmount),color=Muted,fontSize=8.sp)}
                StatusPill(w.status)
            }
            Text("Fee %.2f USDT".format(w.feeAmount),color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=6.dp))
            Text("To: "+w.destinationAddress.take(16)+"…",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=3.dp))
            if(w.txHash!=null){
                Text("TXID: "+w.txHash.take(16)+"…",color=Green,fontSize=8.sp,modifier=Modifier.padding(top=4.dp))
                OutlinedButton(onClick={val clip=context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager;clip.setPrimaryClip(ClipData.newPlainText("Withdrawal TXID",w.txHash))},modifier=Modifier.padding(top=5.dp)){Icon(Icons.Default.ContentCopy,null,Modifier.size(13.dp));Spacer(Modifier.width(4.dp));Text("Copy TXID",fontSize=8.sp)}
            }
            if(w.rejectionReason!=null)Text(w.rejectionReason,color=Red,fontSize=8.sp,modifier=Modifier.padding(top=4.dp))
        }
    }
}

@Composable private fun StatusPill(status:String){
    val done=status=="completed"
    Text(status.replace('_',' ').uppercase(),color=if(done)Green else Gold,fontSize=8.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
}
