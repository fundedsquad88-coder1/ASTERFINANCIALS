package com.asterfinancials.app

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.NumberFormat
import java.util.Locale

@Composable
fun ActivityScreen(onBack:()->Unit){
    val context=androidx.compose.ui.platform.LocalContext.current
    val repo=remember{ActivityRepository(context)}
    var items by remember{mutableStateOf(emptyList<ActivityItem>())}
    var loading by remember{mutableStateOf(true)}
    var error by remember{mutableStateOf(false)}
    LaunchedEffect(Unit){
        loading=true
        val result=repo.list()
        items=result.getOrElse{emptyList()}
        error=result.isFailure
        loading=false
    }
    Column(Modifier.fillMaxSize()){
        Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Column{
                Text("Activity",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                Text("Verified account transaction history",color=Muted,fontSize=9.sp)
            }
        }
        if(loading) Text("Loading activity…",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else if(error) Text("Activity is unavailable right now. Please try again.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else if(items.isEmpty()) Text("No posted account activity yet.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            items(items){item->
                CardBox{
                    Row(Modifier.fillMaxWidth().padding(14.dp),verticalAlignment=Alignment.CenterVertically){
                        Icon(activityIcon(item.type),null,tint=Gold,modifier=Modifier.size(21.dp))
                        Spacer(Modifier.width(11.dp))
                        Column(Modifier.weight(1f)){
                            Text(item.type.replace('_',' ').replaceFirstChar{it.uppercase()},fontSize=11.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                            Text(item.createdAt.replace('T',' ').take(19),color=Muted,fontSize=8.sp)
                            Text(item.status.uppercase(),color=if(item.status=="posted"||item.status=="completed") Green else Muted,fontSize=8.sp)
                        }
                        Text(
                            (if(item.amount>=0) "+" else "")+NumberFormat.getNumberInstance(Locale.US).format(item.amount)+" "+item.currency,
                            color=if(item.amount>=0) Green else Red,fontSize=10.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

private fun activityIcon(type:String)=when(type){
    "deposit"->Icons.Default.SouthWest
    "withdrawal"->Icons.Default.NorthEast
    "investment_principal"->Icons.Default.AutoGraph
    "investment_gain"->Icons.Default.TrendingUp
    "referral_reward"->Icons.Default.People
    else->Icons.Default.ReceiptLong
}

@Composable
fun NotificationsScreen(onBack:()->Unit){
    val context=androidx.compose.ui.platform.LocalContext.current
    val repo=remember{NotificationRepository(context)}
    var items by remember{mutableStateOf(emptyList<AsterNotification>())}
    var loading by remember{mutableStateOf(true)}
    LaunchedEffect(Unit){loading=true;items=repo.list().getOrElse{emptyList()};loading=false}
    Column(Modifier.fillMaxSize()){
        Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Column(Modifier.weight(1f)){Text("Notifications",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold);Text("Account and strategy alerts",color=Muted,fontSize=9.sp)}
            TextButton(onClick={LaunchedEffectScopeHolder.launch(repo){items=repo.list().getOrElse{emptyList()}}}){Text("Refresh",fontSize=9.sp)}
        }
        if(loading)Text("Loading notifications…",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else if(items.isEmpty())Text("No notifications yet.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
            items(items){n->
                CardBox(Modifier.fillMaxWidth().clickable{
                    LaunchedEffectScopeHolder.launch(repo){repo.read(n.id);items=repo.list().getOrElse{items}}
                }){
                    Column(Modifier.padding(14.dp)){
                        Row(verticalAlignment=Alignment.CenterVertically){
                            Icon(if(n.category=="account")Icons.Default.AccountBalanceWallet else Icons.Default.Notifications,null,tint=Gold,modifier=Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp));Text(n.title,fontSize=11.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                            if(n.readAt==null)Text(" NEW",color=Gold,fontSize=7.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                        }
                        Text(n.body,fontSize=9.sp,modifier=Modifier.padding(top=6.dp))
                        Text(n.createdAt.replace('T',' ').take(19),color=Muted,fontSize=7.sp,modifier=Modifier.padding(top=6.dp))
                    }
                }
            }
        }
    }
}

private object LaunchedEffectScopeHolder{
    fun launch(repo:NotificationRepository,block:suspend()->Unit){ kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.Main).launch{kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO){block()}} }
}

