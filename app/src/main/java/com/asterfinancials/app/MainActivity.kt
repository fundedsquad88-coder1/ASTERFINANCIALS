package com.asterfinancials.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.pow

private val Black=Color(0xFF050606)
private val Panel=Color(0xFF0D0E0E)
private val Panel2=Color(0xFF151616)
private val Gold=Color(0xFFD8AD37)
private val WhiteGold=Color(0xFFF1D98A)
private val Muted=Color(0xFF92928B)
private val Green=Color(0xFF18D779)
private val Red=Color(0xFFFF5C62)

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
    var dark by remember{mutableStateOf(true)}
    var tab by remember{mutableStateOf(Tab.HOME)}
    MaterialTheme(
        colorScheme=if(dark)
            darkColorScheme(background=Black,surface=Panel,primary=Gold,onPrimary=Black,onBackground=Color.White)
        else
            lightColorScheme(background=Color(0xFFF7F7F5),surface=Color.White,primary=Color(0xFFA87518),onPrimary=Color.White)
    ){
        Column(Modifier.fillMaxSize()){
            Box(Modifier.weight(1f)){
                when(tab){
                    Tab.HOME->Home{tab=it}
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
            Box(Modifier.size(26.dp).background(Gold),contentAlignment=Alignment.Center){
                Text("A",color=Black,fontWeight=FontWeight.Black,fontSize=14.sp)
            }
            Spacer(Modifier.width(9.dp))
            Text("ASTER",color=Gold,fontSize=11.sp,fontWeight=FontWeight.Bold,letterSpacing=2.sp)
        }
        Text(title,fontSize=23.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=9.dp))
        Text(sub,color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=3.dp))
    }
}

@Composable private fun CardBox(mod:Modifier=Modifier,content:@Composable ColumnScope.()->Unit){
    Card(mod,colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),content=content)
}

@Composable private fun Home(go:(Tab)->Unit){
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{Header("Financial command center","Premium automation & market intelligence")}
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(17.dp)){
                    Text("AVAILABLE BALANCE",color=Muted,fontSize=9.sp)
                    Text("— — —",fontSize=28.sp,fontWeight=FontWeight.Bold)
                    Text("Verified balance appears after account connection.",color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(12.dp))
                    Button({go(Tab.PROFILE)},colors=ButtonDefaults.buttonColors(Gold)){
                        Icon(Icons.Default.AccountCircle,null,Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Connect account",color=Black,fontSize=10.sp)
                    }
                }
            }
            Spacer(Modifier.height(13.dp))
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
            CardBox(Modifier.padding(horizontal=16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("Invest. Automate. Compound.",fontSize=17.sp,fontWeight=FontWeight.Bold)
                    Text("A premium command center for automated investment strategies and market intelligence.",color=Muted,fontSize=10.sp,modifier=Modifier.padding(top=5.dp))
                    Text("No invented account balances or transactions.",color=Gold,fontSize=9.sp,modifier=Modifier.padding(top=8.dp))
                }
            }
        }
    }
}

@Composable private fun Quick(t:String,i:ImageVector,go:()->Unit){
    Column(
        Modifier.width(105.dp).background(MaterialTheme.colorScheme.surface).clickable{go()}.padding(12.dp),
        horizontalAlignment=Alignment.CenterHorizontally
    ){
        Icon(i,null,tint=Gold,modifier=Modifier.size(21.dp))
        Text(t,fontSize=9.sp,modifier=Modifier.padding(top=5.dp))
    }
}

@Composable private fun AutoInvest(){
    var crypto by remember{mutableStateOf(true)}
    var amount by remember{mutableStateOf("1000")}
    var weeks by remember{mutableStateOf("4")}
    var rate by remember{mutableStateOf("22.5")}
    val a=amount.toDoubleOrNull()?:0.0
    val r=(rate.toDoubleOrNull()?:0.0)/100
    val w=weeks.toDoubleOrNull()?:0.0
    val end=a*(1+r).pow(w)
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{Header("Auto Invest","Choose a strategy and review projected outcomes")}
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
                    Input("Initial amount (USDT)",amount){amount=it}
                    Input("Weeks",weeks){weeks=it}
                    Input("Projection % / week",rate){rate=it}
                    Spacer(Modifier.height(10.dp))
                    Text("Projected balance",color=Muted,fontSize=9.sp)
                    Text("%.2f USDT".format(end),color=WhiteGold,fontSize=25.sp,fontWeight=FontWeight.Bold)
                    Text("%.2f principal + %.2f projected gain".format(a,end-a),color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(10.dp))
                    Button({},Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(Gold)){
                        Text("Review & activate",color=Black,fontSize=11.sp)
                    }
                }
            }
        }
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

    LaunchedEffect(refreshed){
        loading=true
        coins=fetchMarketSnapshot(coins)
        loading=false
    }

    val news=listOf(
        News("MARKET","Crypto market cap rises as major assets rebound","CoinMarketCap","https://coinmarketcap.com/top-stories/"),
        News("BINANCE","Binance announces spot-pair and market updates","Binance","https://www.binance.com/en/support/announcement/list"),
        News("ALTCOINS","AVAX gains amid institutional, government and protocol news","CoinMarketCap","https://coinmarketcap.com/top-stories/"),
        News("AI TOKENS","Render and AI-linked tokens gain in sector rotation","CoinMarketCap","https://coinmarketcap.com/top-stories/"),
        News("MACRO","Markets digest the latest Federal Reserve decision","CoinMarketCap","https://coinmarketcap.com/")
    )

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
        items(news){n->
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
                AnalysisCard("Fundamental",Icons.Default.AccountBalance,"Macro · news · on-chain")
                AnalysisCard("Technical",Icons.Default.Timeline,"Trend · momentum · levels")
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

@Composable private fun AnalysisCard(t:String,i:ImageVector,s:String){
    CardBox(Modifier.weight(1f)){
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
            val symbols=old.joinToString(","){it.symbol+"USDT"}
            val url=URL("https://api.binance.com/api/v3/ticker/24hr?symbols="+Uri.encode("[$symbols]"))
            val con=url.openConnection() as HttpURLConnection
            con.connectTimeout=7000
            con.readTimeout=7000
            con.requestMethod="GET"
            val text=con.inputStream.bufferedReader().use{it.readText()}
            con.disconnect()
            val arr=org.json.JSONArray(text)
            val map=mutableMapOf<String,Coin>()
            for(i in 0 until arr.length()){
                val o=arr.getJSONObject(i)
                val s=o.getString("symbol").removeSuffix("USDT")
                map[s]=Coin(s,old.firstOrNull{it.symbol==s}?.name?:s,o.getDouble("lastPrice"),o.getDouble("priceChangePercent"))
            }
            old.map{map[it.symbol]?:it}
        }catch(_:Exception){old}
    }
}

private fun formatPrice(v:Double):String{
    if(v==0.0)return "—"
    val nf=NumberFormat.getCurrencyInstance(Locale.US)
    nf.maximumFractionDigits=if(v<1)6 else 2
    return nf.format(v)
}

@Composable private fun Profile(theme:()->Unit){
    LazyColumn(contentPadding=PaddingValues(bottom=20.dp)){
        item{Header("Profile","Account, security & preferences")}
        item{
            CardBox(Modifier.padding(16.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("ACCOUNT",color=Gold,fontSize=9.sp,fontWeight=FontWeight.Bold)
                    Text("Not connected",fontWeight=FontWeight.Bold)
                    Text("Connect your account to unlock verified balances and funding.",color=Muted,fontSize=9.sp)
                    Spacer(Modifier.height(12.dp))
                    Button({},colors=ButtonDefaults.buttonColors(Gold)){
                        Text("Connect",color=Black)
                    }
                }
            }
        }
        item{
            CardBox(Modifier.padding(horizontal=16.dp)){
                Preference("Deposit USDT",Icons.Default.AccountBalanceWallet,"BEP-20 or TRC-20"){ }
                Preference("Theme",Icons.Default.DarkMode,"Black-gold / white-gold"){theme()}
                Preference("Security",Icons.Default.Security,"Account security controls"){}
                Preference("Notifications",Icons.Default.Notifications,"Market & strategy alerts"){}
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
