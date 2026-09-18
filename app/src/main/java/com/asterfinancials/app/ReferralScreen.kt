package com.asterfinancials.app

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun Referral(onBack:()->Unit = {}){
    val context=androidx.compose.ui.platform.LocalContext.current
    val repo=remember{ReferralRepository(context)}
    var data by remember{mutableStateOf<ReferralSummary?>(null)}
    var loading by remember{mutableStateOf(true)}
    LaunchedEffect(Unit){ data=repo.summary().getOrNull(); loading=false }
    Column(Modifier.fillMaxSize()){
        Row(Modifier.fillMaxWidth().padding(16.dp),verticalAlignment=Alignment.CenterVertically){
            IconButton(onClick=onBack){Icon(Icons.Default.ArrowBack,null,tint=Gold)}
            Text("Referrals",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
        }
        if(loading) Text("Loading referral dashboard…",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else if(data==null) Text("Referral data is unavailable right now.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(16.dp))
        else{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("YOUR REFERRAL CODE",color=Gold,fontSize=9.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                    Row(Modifier.padding(top=7.dp),verticalAlignment=Alignment.CenterVertically){
                        Text(data!!.code ?: "—",fontSize=20.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold,modifier=Modifier.weight(1f))
                        val clipboard=LocalClipboardManager.current
                        IconButton(onClick={data!!.code?.let{clipboard.setText(AnnotatedString(it))}}){Icon(Icons.Default.ContentCopy,null,tint=Gold)}
                    }
                    Spacer(Modifier.height(16.dp))
                    Text("Program rate: "+(data!!.rate*100).toInt()+"%",color=Muted,fontSize=9.sp)
                    Text("Earned rewards: %.2f USDT".format(data!!.earned),fontSize=17.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.Bold)
                    Text("Invited: "+data!!.invited+" · Paid rewards: "+data!!.paidRewards,color=Muted,fontSize=9.sp)
                }
            }
        }
    }
}
