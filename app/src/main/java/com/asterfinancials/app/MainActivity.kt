package com.asterfinancials.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.pow

val Black=Color(0xFF050606)
val Panel=Color(0xFF0D0E0E)
val Panel2=Color(0xFF151616)
val Gold=Color(0xFFD8AD37)
val WhiteGold=Color(0xFFF1D98A)
val Muted=Color(0xFF92928B)
val Green=Color(0xFF18D779)
val Red=Color(0xFFFF5C62)

private enum class Tab(val label:String,val icon:ImageVector){
    HOME("Home",Icons.Default.Home),
    MARKETS("Markets",Icons.Default.ShowChart),
    AUTO("Auto Invest",Icons.Default.AutoGraph),
    CALC("Calculator",Icons.Default.Calculate),
    PROFILE("Profile",Icons.Default.Person)
}

private data class Coin(val symbol:String,val name:String,val price:Double,val change:Double)
private data class News(val category:String,val title:String,val source:String,val url:String)

class MainActivity:ComponentActivity(){
    override fun onCreate(b:Bundle?){
        super.onCreate(b)
        setContent{AsterApp()}
    }
}

@Composable
fun AsterApp(){
    var dark by remember{mutableStateOf(false)}
    var tab by remember{mutableStateOf(Tab.HOME)}
    MaterialTheme(
        colorScheme=if(dark)
            darkColorScheme(background=Black,surface=Panel,surfaceVariant=Panel2,primary=Gold,onPrimary=Black,onBackground=Color.White)
        else
            lightColorScheme(background=Color(0xFFF7F7F5),surface=Color.White,surfaceVariant=Color(0xFFF0F0ED),primary=Color(0xFFA87518),onPrimary=Color.White)
    ){
        Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)){
            Box(Modifier.weight(1f)){
                when(tab){
                    Tab.HOME->MaterialTheme(
                        colorScheme=lightColorScheme(
                            background=Color(0xFFF7F7F5),
                            surface=Color.White,
                            surfaceVariant=Color(0xFFF0F0ED),
                            primary=Color(0xFFA87518),
                            onPrimary=Color.White,
                            onBackground=Black,
                            onSurface=Black
                        )
                    ){
                        Surface(Modifier.fillMaxSize(),color=MaterialTheme.colorScheme.background){
                            Home({tab=it})
                        }
                    }
                    Tab.MARKETS->Markets()
                    Tab.AUTO->AutoInvest()
                    Tab.CALC->Calculator()
                    Tab.PROFILE->Profile{dark=!dark}
                }
            }
            NavigationBar(containerColor=if(dark)Panel else Color.White){
                Tab.values().forEach{t->
                    NavigationBarItem(
                        selected=tab==t,
                        onClick={tab=t},
                        icon={Icon(t.icon,null,Modifier.size(19.dp))},
                        label={Text(t.label,fontSize=8.sp)},
                        colors=NavigationBarItemDefaults.colors(
                            selectedIconColor=Gold,selectedTextColor=Gold,
                            unselectedIconColor=Muted,unselectedTextColor=Muted,
                            indicatorColor=if(dark)Color(0x332D2715) else Color(0x14A87518)
                        )
                    )
                }
            }
        }
    }
}

@Composable private fun Header(title:String,sub:String){
    Column(Modifier.padding(18.dp,18.dp,18.dp,12.dp)){
        Row(verticalAlignment=Alignment.CenterVertically){
            Image(
                painter=painterResource(com.asterfinancials.app.R.drawable.aster_watermark),
                contentDescription="Aster",
                modifier=Modifier.size(34.dp)
            )
            Spacer(Modifier.width(9.dp))
            Text("ASTER",color=Gold,fontSize=11.sp,fontWeight=FontWeight.Bold,letterSpacing=2.sp)
        }
        Text(title,fontSize=23.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=9.dp))
        Text(sub,color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=3.dp))
    }
}

@Composable fun CardBox(mod:Modifier=Modifier,content:@Composable ColumnScope.()->Unit){
    Card(mod,colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),content=content)
}

@Composable private fun Home(go:(Tab)->Unit){
    val context=LocalContext.current
    val account=remember{AccountRepository(context)}
    var summary by remember{mutableStateOf<AccountSummary?>(null)}
    var loading by remember{mutableStateOf(false)}
    val user=remember{AuthRepository(context).currentUser()}
    LaunchedEffect(Unit){
        if(user!=null){loading=true;summary=account.summary().getOrNull();loading=false}
    }
    GenZHome(
        balance=when{loading->"SYNCING…";summary==null->"— — —";else->"%.2f USDT".format(summary!!.total)},
        userName=user?.fullName.orEmpty(),
        onInvest={go(Tab.INVEST)},
        onMarkets={go(Tab.MARKETS)},
        onFunding={go(Tab.PROFILE)},
        onProfile={go(Tab.PROFILE)},
        onNotifications={go(Tab.PROFILE)},
        dark=false,
        onToggleTheme={}
    )
}

@Composable private fun LegacyHome(go:(Tab)->Unit){
    val context=LocalContext.current
    val account=remember{AccountRepository(context)}
    var summary by remember{mutableStateOf<AccountSummary?>(null)}
    var accountLoading by remember{mutableStateOf(false)}
    LaunchedEffect(Unit){
        if(AuthRepository(context).currentUser()!=null){
            accountLoading=true
            summary=account.summary().getOrNull()
            accountLoading=false
        }
    }
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{
            Box(Modifier.fillMaxWidth()){
                Image(
                    painter=painterResource(com.asterfinancials.app.R.drawable.aster_watermark),
                    contentDescription=null,
                    modifier=Modifier.size(250.dp).align(Alignment.TopEnd).offset(x=55.dp,y=25.dp),
                    alpha=0.055f
                )
                Column(Modifier.padding(18.dp,14.dp,18.dp,12.dp)){
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){
                        Row(Modifier.weight(1f),verticalAlignment=Alignment.CenterVertically){
                            Image(
                                painter=painterResource(com.asterfinancials.app.R.drawable.aster_watermark),
                                contentDescription="Aster",
                                modifier=Modifier.size(44.dp)
                            )
                            Spacer(Modifier.width(8.dp))
                        }
                        Spacer(Modifier.size(48.dp))
                    }
                    Text("Financial command center",fontSize=23.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=9.dp))
                    Text("Premium automation & market intelligence",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=3.dp))
                }
            }
        }
        item{
            Image(painter=painterResource(com.asterfinancials.app.R.drawable.aster_banner_trade_earn),contentDescription="Trade. Invest. Earn.",modifier=Modifier.fillMaxWidth().padding(horizontal=16.dp).height(132.dp).clip(RoundedCornerShape(18.dp)))
            Spacer(Modifier.height(14.dp))
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(17.dp)){
                    Row(verticalAlignment=Alignment.CenterVertically){
                        Column(Modifier.weight(1f)){
                            Text("AVAILABLE BALANCE",color=Muted,fontSize=9.sp)
                            Text(
                                when {
                                    accountLoading -> "Loading…"
                                    summary == null -> "— — —"
                                    else -> "%.2f USDT".format(summary!!.total)
                                },
                                fontSize=28.sp,fontWeight=FontWeight.Bold
                            )
                            Text(
                                when {
                                    accountLoading -> "Fetching your server-side balance."
                                    summary == null -> "Sign in to view your verified account balance."
                                    else -> "Available %.2f · Invested %.2f USDT".format(summary!!.available,summary!!.invested)
                                },
                                color=Muted,fontSize=9.sp
                            )
                        }
                        Icon(Icons.Default.AccountBalanceWallet,null,tint=Gold,modifier=Modifier.size(30.dp))
                    }
                    Spacer(Modifier.height(12.dp))
                    Button({go(Tab.PROFILE)},colors=ButtonDefaults.buttonColors(Gold)){
                        Icon(Icons.Default.AccountCircle,null,Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(if(summary==null)"Sign in" else "Account",color=Black,fontSize=10.sp)
                    }
                }
            }
            Spacer(Modifier.height(14.dp))
        }
        item{
            Text("QUICK ACCESS",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(16.dp,5.dp))
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                Quick("Auto Invest",Icons.Default.AutoGraph){go(Tab.AUTO)}
                Quick("Markets",Icons.Default.ShowChart){go(Tab.MARKETS)}
                Quick("Calculator",Icons.Default.Calculate){go(Tab.CALC)}
                Quick("Deposit",Icons.Default.AccountBalanceWallet){go(Tab.PROFILE)}
            }
            Spacer(Modifier.height(14.dp))
        }
        item{
            Text("AUTO-INVEST",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(horizontal=16.dp))
            Text("Put your strategy on repeat.",fontSize=21.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(16.dp,5.dp,16.dp,10.dp))
        }
        item{
            AutoHomeCard(
                title="Crypto Auto-Invest",
                icon=Icons.Default.CurrencyBitcoin,
                description="Major digital assets with weekly progression and compounding controls.",
                instruments=listOf("BTC","ETH","SOL","BNB","XRP")
            ){go(Tab.AUTO)}
        }
        item{
            AutoHomeCard(
                title="Forex Auto-Invest",
                icon=Icons.Default.CurrencyExchange,
                description="A dedicated currency-market option with transparent reporting and account controls.",
                instruments=listOf("EUR/USD","GBP/USD","USD/JPY","XAU/USD")
            ){go(Tab.AUTO)}
        }
        item{
            CardBox(Modifier.padding(16.dp)){
                Row(Modifier.padding(16.dp),horizontalArrangement=Arrangement.spacedBy(18.dp)){
                    HomeStat(Modifier.weight(1f),"24/7","Platform access")
                    HomeStat(Modifier.weight(1f),"2","Auto-Invest categories")
                    HomeStat(Modifier.weight(1f),"Live","Market data")
                }
            }
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("Invest. Automate. Compound.",fontSize=17.sp,fontWeight=FontWeight.Bold)
                    Text("A premium command center for automated investment strategies and market intelligence.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=5.dp))
                    Text("Target figures are illustrative and not guaranteed.",color=Gold,fontSize=9.sp,modifier=Modifier.padding(top=8.dp))
                }
            }
        }
    }
}

@Composable private fun AutoHomeCard(title:String,icon:ImageVector,description:String,instruments:List<String>,go:()->Unit){
    CardBox(Modifier.padding(horizontal=16.dp,vertical=5.dp)){
        Column(Modifier.padding(17.dp)){
            Row(verticalAlignment=Alignment.CenterVertically){
                Box(Modifier.size(44.dp).background(MaterialTheme.colorScheme.surfaceVariant),contentAlignment=Alignment.Center){
                    Icon(icon,null,tint=Gold,modifier=Modifier.size(23.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)){
                    Text(title,fontSize=16.sp,fontWeight=FontWeight.Bold)
                    Text(description,color=Muted,fontSize=9.sp,lineHeight=14.sp,modifier=Modifier.padding(top=3.dp))
                }
            }
            Spacer(Modifier.height(14.dp))
            Text("20–25% / week",color=Gold,fontSize=24.sp,fontWeight=FontWeight.Black)
            Text("Illustrative target range",color=Muted,fontSize=8.sp)
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(top=10.dp),horizontalArrangement=Arrangement.spacedBy(6.dp)){
                instruments.forEach{Text(it,fontSize=8.sp,color=Muted,modifier=Modifier.background(MaterialTheme.colorScheme.surfaceVariant).padding(horizontal=8.dp,vertical=5.dp))}
            }
            Spacer(Modifier.height(12.dp))
            Button(go,colors=ButtonDefaults.buttonColors(Gold)){
                Text("Explore Auto-Invest →",color=Black,fontSize=10.sp,fontWeight=FontWeight.Bold)
            }
        }
    }
}

@Composable private fun HomeStat(modifier:Modifier,value:String,label:String){
    Column(modifier){
        Text(value,color=Gold,fontSize=17.sp,fontWeight=FontWeight.Black)
        Text(label,color=Muted,fontSize=7.sp,lineHeight=10.sp)
    }
}

@Composable private fun Quick(t:String,i:ImageVector,go:()->Unit){
    Column(
        Modifier.width(105.dp).background(MaterialTheme.colorScheme.surface).clickable{go()}.padding(12.dp),
        horizontalAlignment=Alignment.CenterHorizontally
    ){
        Icon(i,null,tint=Gold,modifier=Modifier.size(21.dp))
        Text(t,fontSize=9.sp,color=Gold,modifier=Modifier.padding(top=5.dp))
    }
}

@Composable private fun AutoInvest(){
    val context=LocalContext.current
    val repository=remember{InvestmentRepository(context)}
    val scope=rememberCoroutineScope()
    var crypto by remember{mutableStateOf(true)}
    var amount by remember{mutableStateOf("")}
    var weeks by remember{mutableStateOf("4")}
    var rate by remember{mutableStateOf("22.5")}
    var compounding by remember{mutableStateOf(true)}
    var review by remember{mutableStateOf(false)}
    var activating by remember{mutableStateOf(false)}
    var message by remember{mutableStateOf<String?>(null)}
    var activated by remember{mutableStateOf<Investment?>(null)}
    var investments by remember{mutableStateOf(emptyList<Investment>())}
    var investmentsLoading by remember{mutableStateOf(false)}
    LaunchedEffect(Unit){
        if(AuthRepository(context).currentUser()!=null){
            investmentsLoading=true
            investments=repository.list().getOrElse{emptyList()}
            investmentsLoading=false
        }
    }
    val a=amount.toDoubleOrNull()?:0.0
    val r=(rate.toDoubleOrNull()?:0.0)/100
    val w=weeks.toDoubleOrNull()?:0.0
    val end=if(a>0 && r>=0 && w>=0)a*(1+r).pow(w) else 0.0
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{
            Text("ACTIVE INVESTMENTS",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(16.dp,14.dp,16.dp,5.dp))
            if(investmentsLoading) Text("Loading your positions…",color=Muted,fontSize=9.sp,modifier=Modifier.padding(horizontal=16.dp))
            else if(investments.isEmpty()) Text("No active investments yet. Activated positions will appear here.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(horizontal=16.dp))
            investments.filter{it.status=="active"}.forEach{inv->
                CardBox(Modifier.padding(horizontal=16.dp,vertical=4.dp)){
                    Row(Modifier.fillMaxWidth().padding(14.dp),verticalAlignment=Alignment.CenterVertically){
                        Icon(if(inv.category=="crypto")Icons.Default.CurrencyBitcoin else Icons.Default.CurrencyExchange,null,tint=Gold,modifier=Modifier.size(22.dp))
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)){
                            Text(inv.category.replaceFirstChar{ch->ch.uppercase()}+" Auto-Invest",fontWeight=FontWeight.Bold,fontSize=11.sp)
                            Text("Principal %.2f · Current %.2f USDT".format(inv.principal,inv.currentValue),color=Muted,fontSize=9.sp)
                        }
                        Text("ACTIVE",color=Green,fontSize=8.sp,fontWeight=FontWeight.Bold)
                    }
                }
            }
        }
        item{Header("Auto Invest","Choose a strategy and activate only against verified funds")}
        item{
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                Strategy("Cryptocurrency","20–25% / week",Icons.Default.CurrencyBitcoin,crypto){crypto=true}
                Strategy("Forex","20–25% / week",Icons.Default.CurrencyExchange,!crypto){crypto=false}
            }
            Spacer(Modifier.height(13.dp))
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text(if(crypto)"CRYPTOCURRENCY AUTO INVEST" else "FOREX AUTO INVEST",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text("Weekly target range: 20–25%",fontSize=19.sp,fontWeight=FontWeight.Bold)
                    Text("Target/projection only — actual performance may be lower or negative.",color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(12.dp))
                    Input("Investment amount (USDT)",amount){amount=it}
                    Input("Duration (weeks)",weeks){weeks=it}
                    Input("Illustrative projection % / week",rate){rate=it}
                    Row(Modifier.fillMaxWidth().padding(top=10.dp),verticalAlignment=Alignment.CenterVertically){
                        Column(Modifier.weight(1f)){
                            Text("Compounding",fontSize=11.sp,fontWeight=FontWeight.Bold)
                            Text("Keep gains invested when applicable",color=Muted,fontSize=8.sp)
                        }
                        Switch(checked=compounding,onCheckedChange={compounding=it})
                    }
                    Spacer(Modifier.height(10.dp))
                    Text("Illustrative projected value",color=Muted,fontSize=9.sp)
                    Text(if(a>0)"%.2f USDT".format(end) else "—",color=WhiteGold,fontSize=25.sp,fontWeight=FontWeight.Bold)
                    Text(if(a>0)"%.2f principal + %.2f illustrative gain".format(a,end-a) else "Enter an amount to calculate.",color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(10.dp))
                    Button(
                        {message=null; if(a<=0 || weeks.toDoubleOrNull()==null || rate.toDoubleOrNull()==null) message="Enter valid investment details." else review=true},
                        Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(Gold)
                    ){Text("Review & activate",color=Black,fontSize=11.sp,fontWeight=FontWeight.Bold)}
                    message?.let{Text(it,color=if(it.startsWith("Activated"))Green else Gold,fontSize=9.sp,modifier=Modifier.padding(top=9.dp))}
                    activated?.let{inv->Text("Active "+inv.category.replaceFirstChar{ch->ch.uppercase()}+" investment · %.2f USDT".format(inv.principal),color=Green,fontSize=9.sp,modifier=Modifier.padding(top=5.dp))}
                }
            }
        }
    }
    if(review){
        AlertDialog(
            onDismissRequest={if(!activating)review=false},
            title={Text("Review Auto-Invest")},
            text={Column(verticalArrangement=Arrangement.spacedBy(6.dp)){
                Text(if(crypto)"Cryptocurrency" else "Forex",fontWeight=FontWeight.Bold)
                Text("Principal: %.2f USDT".format(a))
                Text("Duration: "+weeks+" weeks")
                Text("Projection: "+rate+"% / week")
                Text("Compounding: "+if(compounding)"ON" else "OFF")
                Text("Projected value: %.2f USDT".format(end))
                Text("The projection is illustrative and not guaranteed. Activation requires sufficient verified available balance.",color=Muted,fontSize=9.sp)
            }},
            confirmButton={
                Button(enabled=!activating,onClick={
                    activating=true
                    message=null
                    scope.launch{
                        val result=repository.create(if(crypto)"crypto" else "forex",amount,rate,compounding)
                        activating=false
                        result.onSuccess{
                            activated=it
                            message="Activated — investment recorded on the Aster server."
                            review=false
                        }.onFailure{message=it.message?: "Investment could not be activated."}
                    }
                },colors=ButtonDefaults.buttonColors(Gold)){Text(if(activating)"Activating…" else "Confirm",color=Black)}
            },
            dismissButton={TextButton(enabled=!activating,onClick={review=false}){Text("Cancel")}}
        )
    }
}
@Composable private fun Strategy(t:String,r:String,i:ImageVector,sel:Boolean,go:()->Unit){
    CardBox(Modifier.width(175.dp).clickable{go()}){
        Column(Modifier.padding(13.dp)){
            Icon(i,null,tint=if(sel)Gold else Muted,modifier=Modifier.size(22.dp))
            Text(t,fontSize=11.sp,fontWeight=FontWeight.Bold)
            Text(r,color=if(sel)Gold else Muted,fontSize=9.sp)
            if(sel)Text("SELECTED",color=Gold,fontSize=8.sp,fontWeight=FontWeight.Bold)
        }
    }
}

@Composable private fun Referral(){
    val context=LocalContext.current
    val repo=remember{ReferralRepository(context)}
    val clipboard=context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
    var data by remember{mutableStateOf<ReferralSummary?>(null)}
    var loading by remember{mutableStateOf(true)}
    var message by remember{mutableStateOf<String?>(null)}
    LaunchedEffect(Unit){data=repo.summary().getOrNull();loading=false}
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{Header("Aster Referral","Invite users and track your referral rewards")}
        item{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("YOUR REFERRAL CODE",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text(if(loading)"Loading…" else data?.code?:"—",fontSize=25.sp,fontWeight=FontWeight.Bold,color=WhiteGold)
                    Text("Referral reward rate: 15%",color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=4.dp))
                    Row(Modifier.padding(top=10.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                        OutlinedButton(onClick={
                            data?.code?.let{
                                clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Aster referral code",it))
                                message="Referral code copied."
                            }
                        }){Text("Copy code",fontSize=9.sp)}
                    }
                    message?.let{Text(it,color=Green,fontSize=9.sp,modifier=Modifier.padding(top=7.dp))}
                }
            }
        }
        item{
            Row(Modifier.padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                StatCard(Modifier.weight(1f),"INVITED",data?.invited?.toString()?:"—")
                StatCard(Modifier.weight(1f),"EARNED",data?.earned?.let{"%.2f".format(it)}?:"—")
            }
        }
        item{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(14.dp)){
                    Text("HOW IT WORKS",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text("Share your referral code. New accounts can enter it during registration. Rewards are recorded server-side and only become part of your balance when the corresponding reward is posted.",fontSize=10.sp,modifier=Modifier.padding(top=5.dp))
                    Text("Rewards are subject to the program's terms and backend verification.",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=7.dp))
                }
            }
        }
    }
}

@Composable private fun StatCard(modifier:Modifier,label:String,value:String){
    CardBox(modifier){
        Column(Modifier.padding(14.dp)){
            Text(label,color=Muted,fontSize=8.sp,fontWeight=FontWeight.Bold)
            Text(value,fontSize=18.sp,fontWeight=FontWeight.Bold,color=WhiteGold,modifier=Modifier.padding(top=3.dp))
        }
    }
}

@Composable private fun Calculator(){
    var a by remember{mutableStateOf("1000")}
    var r by remember{mutableStateOf("22.5")}
    var w by remember{mutableStateOf("4")}
    val amount=a.toDoubleOrNull()?:0.0
    val rate=(r.toDoubleOrNull()?:0.0)/100
    val weeks=w.toDoubleOrNull()?:0.0
    val result=amount*(1+rate).pow(weeks)
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{Header("Aster Compounding Lab","Explore the effect of keeping gains invested")}
        item{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(16.dp)){
                    Input("Starting amount (USDT)",a){a=it}
                    Input("Weekly projection %",r){r=it}
                    Input("Weeks",w){w=it}
                    Spacer(Modifier.height(12.dp))
                    Text("ILLUSTRATIVE END VALUE",color=Muted,fontSize=9.sp)
                    Text("%.2f USDT".format(result),color=WhiteGold,fontSize=26.sp,fontWeight=FontWeight.Bold)
                    Text("Principal  %.2f  +  projected gain  %.2f".format(amount,result-amount),color=Muted,fontSize=10.sp)
                    Text("Illustrative profit: %.2f USDT".format(result-amount),color=Green,fontSize=10.sp,modifier=Modifier.padding(top=5.dp))
                    Text("This calculator does not predict or guarantee investment performance.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=8.dp))
                }
            }
        }
    }
}

@Composable private fun Markets(){
    var coins by remember{mutableStateOf(listOf(
        Coin("BTC","Bitcoin",0.0,0.0),Coin("ETH","Ethereum",0.0,0.0),
        Coin("SOL","Solana",0.0,0.0),Coin("BNB","BNB",0.0,0.0),
        Coin("XRP","XRP",0.0,0.0),Coin("TRX","TRON",0.0,0.0)
    ))}
    var loading by remember{mutableStateOf(true)}
    var refreshed by remember{mutableStateOf(false)}
    var news by remember{mutableStateOf(emptyList<News>())}
    var newsLoading by remember{mutableStateOf(true)}

    LaunchedEffect(refreshed){
        loading=true
        coins=fetchMarketSnapshot(coins)
        news=fetchLiveNews()
        loading=false
        newsLoading=false
    }

    val displayedNews=if(news.isEmpty()) listOf(News("NEWS","Live headlines are temporarily unavailable","CoinDesk","https://www.coindesk.com/")) else news

    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{
            Header("Markets","Rates, movers, headlines & market intelligence")
            Row(Modifier.padding(horizontal=16.dp),verticalAlignment=Alignment.CenterVertically){
                Column(Modifier.weight(1f)){
                    Text("MARKET SNAPSHOT",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text(if(loading)"Updating rates…" else "Live public market feed",fontSize=10.sp,color=Muted)
                }
                OutlinedButton({refreshed=!refreshed}){
                    Icon(Icons.Default.Refresh,null,Modifier.size(15.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Refresh",fontSize=9.sp)
                }
            }
            Spacer(Modifier.height(10.dp))
        }
        item{
            Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                coins.take(4).forEach{c->
                    MarketMini(c.symbol,formatPrice(c.price),c.change)
                }
            }
            Spacer(Modifier.height(14.dp))
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(15.dp)){
                    Row(verticalAlignment=Alignment.CenterVertically){
                        Icon(Icons.Default.Newspaper,null,tint=Gold,modifier=Modifier.size(18.dp))
                        Spacer(Modifier.width(7.dp))
                        Text("LATEST MARKET NEWS",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    }
                    Text("Headlines worth watching",fontSize=17.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=5.dp))
                    Text("Articles are opened from their original publisher.",color=Muted,fontSize=9.sp)
                }
            }
            Spacer(Modifier.height(7.dp))
        }
        items(displayedNews){n->
            NewsRow(n)
        }
        item{
            Text("MARKETS",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(16.dp,12.dp,16.dp,4.dp))
        }
        items(coins){c->
            CardBox(Modifier.padding(horizontal=10.dp,vertical=3.dp).fillMaxWidth()){
                Row(Modifier.padding(13.dp),verticalAlignment=Alignment.CenterVertically){
                    Box(Modifier.size(34.dp).background(if(c.change>=0)Color(0x1422C77A) else Color(0x14FF5C62)),contentAlignment=Alignment.Center){
                        Text(c.symbol.take(1),color=if(c.change>=0)Green else Red,fontWeight=FontWeight.Bold)
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)){
                        Text(c.name,fontSize=11.sp,fontWeight=FontWeight.Bold)
                        Text(c.symbol+" / USDT · public feed",color=Muted,fontSize=9.sp)
                    }
                    Column(horizontalAlignment=Alignment.End){
                        Text(formatPrice(c.price),fontSize=11.sp,fontWeight=FontWeight.Bold)
                        Text(if(c.price==0.0)"—" else "%+.2f%%".format(c.change),color=if(c.change>=0)Green else Red,fontSize=9.sp)
                    }
                }
            }
        }
        item{
            Row(Modifier.padding(16.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                AnalysisCard(Modifier.weight(1f),"Fundamental",Icons.Default.AccountBalance,"Macro · news · on-chain")
                AnalysisCard(Modifier.weight(1f),"Technical",Icons.Default.Timeline,"Trend · momentum · levels")
            }
        }
    }
}

@Composable private fun NewsRow(n:News){
    val context=LocalContext.current
    CardBox(Modifier.padding(horizontal=16.dp,vertical=4.dp).fillMaxWidth().clickable{
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(n.url)))
    }){
        Row(Modifier.padding(13.dp),verticalAlignment=Alignment.CenterVertically){
            Box(Modifier.size(42.dp).background(Color(0x142D2715)),contentAlignment=Alignment.Center){
                Icon(Icons.Default.Article,null,tint=Gold,modifier=Modifier.size(20.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)){
                Text(n.category,fontSize=8.sp,color=Gold,fontWeight=FontWeight.Bold)
                Text(n.title,fontSize=11.sp,fontWeight=FontWeight.SemiBold,modifier=Modifier.padding(top=2.dp))
                Text(n.source+" · Open article",color=Muted,fontSize=8.sp,modifier=Modifier.padding(top=3.dp))
            }
            Icon(Icons.Default.OpenInNew,null,tint=Muted,modifier=Modifier.size(15.dp))
        }
    }
}

@Composable private fun AnalysisCard(modifier:Modifier,t:String,i:ImageVector,s:String){
    CardBox(modifier){
        Column(Modifier.padding(14.dp)){
            Icon(i,null,tint=Gold,modifier=Modifier.size(19.dp))
            Text(t,fontWeight=FontWeight.Bold,fontSize=11.sp,modifier=Modifier.padding(top=6.dp))
            Text(s,color=Muted,fontSize=9.sp,modifier=Modifier.padding(top=2.dp))
        }
    }
}

@Composable private fun MarketMini(symbol:String,price:String,change:Double){
    CardBox(Modifier.width(145.dp)){
        Column(Modifier.padding(12.dp)){
            Text(symbol,color=Gold,fontWeight=FontWeight.Bold,fontSize=10.sp)
            Text(price,fontSize=15.sp,fontWeight=FontWeight.Bold)
            Text(if(price=="—")"Updating…" else "%+.2f%% 24h".format(change),color=if(change>=0)Green else Red,fontSize=9.sp)
        }
    }
}

private suspend fun fetchMarketSnapshot(old:List<Coin>):List<Coin>{
    return withContext(Dispatchers.IO){
        try{
            val url=URL("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,binancecoin,ripple,tron&order=market_cap_desc&per_page=6&page=1&sparkline=false&price_change_percentage=24h")
            val con=url.openConnection() as HttpURLConnection
            con.connectTimeout=10000
            con.readTimeout=10000
            con.requestMethod="GET"
            val text=con.inputStream.bufferedReader().use{it.readText()}
            con.disconnect()
            val arr=org.json.JSONArray(text)
            val ids=mapOf("bitcoin" to "BTC","ethereum" to "ETH","solana" to "SOL","binancecoin" to "BNB","ripple" to "XRP","tron" to "TRX")
            val names=mapOf("BTC" to "Bitcoin","ETH" to "Ethereum","SOL" to "Solana","BNB" to "BNB","XRP" to "XRP","TRX" to "TRON")
            val map=mutableMapOf<String,Coin>()
            for(i in 0 until arr.length()){
                val o=arr.getJSONObject(i)
                val s=ids[o.getString("id")]?:continue
                map[s]=Coin(s,names[s]?:s,o.optDouble("current_price",0.0),o.optDouble("price_change_percentage_24h",0.0))
            }
            old.map{map[it.symbol]?:it}
        }catch(_:Exception){
            old
        }
    }
}

private suspend fun fetchLiveNews():List<News>{
    return withContext(Dispatchers.IO){
        try{
            val con=URL("https://www.coindesk.com/arc/outboundfeeds/rss/").openConnection() as HttpURLConnection
            con.connectTimeout=10000
            con.readTimeout=10000
            val xml=con.inputStream.bufferedReader().use{it.readText()}
            con.disconnect()
            val result=mutableListOf<News>()
            val items=Regex("<item>(.*?)</item>",RegexOption.DOT_MATCHES_ALL)
            val titles=Regex("<title>(.*?)</title>",RegexOption.DOT_MATCHES_ALL)
            val links=Regex("<link>(.*?)</link>",RegexOption.DOT_MATCHES_ALL)
            for(item in items.findAll(xml).take(8)){
                val body=item.groupValues[1]
                val title=titles.find(body)?.groupValues?.get(1)?.trim()?.replace("<![CDATA[","")?.replace("]]>","")?.replace("&amp;","&")?:continue
                val link=links.find(body)?.groupValues?.get(1)?.trim()?:continue
                result.add(News("NEWS",title,"CoinDesk",link))
            }
            result
        }catch(_:Exception){emptyList()}
    }
}

private fun formatPrice(v:Double):String{
    if(v==0.0)return "—"
    val nf=NumberFormat.getCurrencyInstance(Locale.US)
    nf.maximumFractionDigits=if(v<1)6 else 2
    return nf.format(v)
}

@Composable private fun Profile(theme:()->Unit){
    var showDeposit by remember{mutableStateOf(false)}
    var showWithdrawal by remember{mutableStateOf(false)}
    var showActivity by remember{mutableStateOf(false)}
    var showNotifications by remember{mutableStateOf(false)}
    var showReferral by remember{mutableStateOf(false)}
    var showFundingHistory by remember{mutableStateOf(false)}
    if(showDeposit){
        DepositScreen(onBack={showDeposit=false})
        return
    }
    if(showWithdrawal){
        WithdrawalScreen(onBack={showWithdrawal=false})
        return
    }
    if(showActivity){
        ActivityScreen(onBack={showActivity=false})
        return
    }
    if(showNotifications){
        NotificationsScreen(onBack={showNotifications=false})
        return
    }
    if(showReferral){
        Referral(onBack={showReferral=false})
        return
    }
    if(showFundingHistory){
        FundingHistoryScreen(onBack={showFundingHistory=false})
        return
    }
    val context=LocalContext.current
    val repository=remember{AuthRepository(context)}
    var user by remember{mutableStateOf(repository.currentUser())}

    if(user==null){
        Column(Modifier.fillMaxSize()){
            Row(Modifier.padding(16.dp),verticalAlignment=Alignment.CenterVertically){
                Text("‹",fontSize=30.sp,color=Gold,modifier=Modifier.clickable{})
                Spacer(Modifier.width(8.dp))
                Text("Aster Account",fontSize=20.sp,fontWeight=FontWeight.Bold)
            }
            AuthScreen(repository){ authenticated -> user=authenticated }
        }
        return
    }

    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{
            Column(Modifier.padding(18.dp,18.dp,18.dp,12.dp)){
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){
                    Row(Modifier.weight(1f),verticalAlignment=Alignment.CenterVertically){
                        Image(
                            painter=painterResource(com.asterfinancials.app.R.drawable.aster_watermark),
                            contentDescription="Aster",
                            modifier=Modifier.size(34.dp)
                        )
                        Spacer(Modifier.width(9.dp))
                        Text("ASTER",color=Gold,fontSize=11.sp,fontWeight=FontWeight.Bold,letterSpacing=2.sp)
                    }
                    IconButton(onClick=theme){
                        Icon(
                            if(MaterialTheme.colorScheme.background==Black) Icons.Default.LightMode else Icons.Default.DarkMode,
                            contentDescription=if(MaterialTheme.colorScheme.background==Black) "Switch to light theme" else "Switch to dark theme",
                            tint=Gold
                        )
                    }
                }
                Text("Profile",fontSize=23.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=9.dp))
                Text("Account, security & preferences",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=3.dp))
            }
        }
        item{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("ACCOUNT",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text(user?.fullName ?: "Aster member",fontWeight=FontWeight.Bold)
                    Text(user?.email ?: "",color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(12.dp))
                    OutlinedButton({ repository.logout(); user=null }){
                        Text("Sign out",fontSize=10.sp)
                    }
                }
            }
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Preference("Deposit USDT",Icons.Default.AccountBalanceWallet,"BEP-20 or TRC-20"){ showDeposit=true }
                Preference("Withdraw USDT",Icons.Default.AccountBalanceWallet,"Request a transfer to your wallet"){ showWithdrawal=true }
                Preference("Referrals",Icons.Default.People,"Your referral code & rewards"){ showReferral=true }
                Preference("Funding history",Icons.Default.AccountBalanceWallet,"Deposit verification & withdrawal status"){ showFundingHistory=true }
                Preference("Activity",Icons.Default.ReceiptLong,"Deposits, withdrawals & investment ledger"){ showActivity=true }
                Preference("Security",Icons.Default.Security,"Account security controls"){}
                Preference("Notifications",Icons.Default.Notifications,"Market & strategy alerts"){ showNotifications=true }
                Preference("Support",Icons.Default.HelpOutline,"Help center"){}
            }
        }
        item{
            Text("Funding architecture",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(16.dp,14.dp,16.dp,5.dp))
            Text("Production deposit addresses, transaction verification, balances and withdrawals must be supplied by the Aster backend before real funds are shown.",color=Muted,fontSize=9.sp,modifier=Modifier.padding(horizontal=16.dp))
        }
    }
}

@Composable private fun Preference(t:String,i:ImageVector,s:String,go:()->Unit){
    Row(Modifier.fillMaxWidth().clickable{go()}.padding(13.dp),verticalAlignment=Alignment.CenterVertically){
        Icon(i,null,tint=Gold,modifier=Modifier.size(19.dp))
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)){
            Text(t,fontSize=11.sp,fontWeight=FontWeight.Bold)
            Text(s,color=Muted,fontSize=9.sp)
        }
        Icon(Icons.Default.ChevronRight,null,tint=Muted)
    }
}

@Composable private fun Input(label:String,value:String,on:(String)->Unit){
    OutlinedTextField(
        value=value,onValueChange=on,modifier=Modifier.fillMaxWidth().padding(top=8.dp),
        label={Text(label,fontSize=9.sp)},singleLine=true,
        textStyle=LocalTextStyle.current.copy(fontSize=11.sp)
    )
}