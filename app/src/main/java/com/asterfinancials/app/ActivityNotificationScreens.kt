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
    val prefs=remember{context.getSharedPreferences("aster_notifications",Context.MODE_PRIVATE)}
    var market by remember{mutableStateOf(prefs.getBoolean("market",true))}
    var strategy by remember{mutableStateOf(prefs.getBoolean("strategy",true))}
    var account by remember{mutableStateOf(prefs.getBoolean("account",true))}
    Column(Modifier.fillMaxSize()){
        Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Column{
                Text("Notifications",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                Text("Control alerts shown by Aster",color=Muted,fontSize=9.sp)
            }
        }
        CardBox(Modifier.padding(horizontal=16.dp)){
            Column(Modifier.padding(16.dp)){
                NotificationToggle("Market updates","News and market-rate alerts",market){market=it;prefs.edit().putBoolean("market",it).apply()}
                NotificationToggle("Strategy updates","Auto-Invest and weekly update notices",strategy){strategy=it;prefs.edit().putBoolean("strategy",it).apply()}
                NotificationToggle("Account activity","Deposits, withdrawals and security events",account){account=it;prefs.edit().putBoolean("account",it).apply()}
            }
        }
        Text("Notification policy",color=Gold,fontSize=9.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold,modifier=Modifier.padding(16.dp,18.dp,16.dp,5.dp))
        Text("These preferences control in-app notification categories. Push delivery requires a production notification service and user permission.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(horizontal=16.dp))
    }
}

@Composable private fun NotificationToggle(title:String,sub:String,checked:Boolean,on:(Boolean)->Unit){
    Row(Modifier.fillMaxWidth().padding(vertical=9.dp),verticalAlignment=Alignment.CenterVertically){
        Column(Modifier.weight(1f)){
            Text(title,fontSize=11.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
            Text(sub,color=Muted,fontSize=8.sp)
        }
        Switch(checked=checked,onCheckedChange=on)
    }
}
