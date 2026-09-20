package com.asterfinancials.app

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.*
import androidx.compose.ui.draw.*
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.*
import kotlinx.coroutines.launch
import kotlin.math.*
import java.text.NumberFormat
import java.util.Locale

val Black=Color(0xFF050606)
val Panel=Color(0xFF0D0E0E)
val Panel2=Color(0xFF151616)
val Gold=Color(0xFFD8AD37)
val WhiteGold=Color(0xFFF1D98A)
val Muted=Color(0xFF92928B)
val Green=Color(0xFF18D779)
val Red=Color(0xFFFF5C62)

@Composable fun CardBox(mod:Modifier=Modifier,content:@Composable ColumnScope.()->Unit){
    Card(mod,colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),content=content)
}

private enum class GTab(val label:String,val icon:ImageVector){HOME("Home",Icons.Default.Home),MARKETS("Markets",Icons.Default.ShowChart),AUTO("Invest",Icons.Default.AutoGraph),CALC("Lab",Icons.Default.Calculate),MORE("More",Icons.Default.Person)}

@Composable fun GenZApp(){
    val context=LocalContext.current
    val auth=remember{AuthRepository(context)}
    var user by remember{mutableStateOf(auth.currentUser())}
    if(user==null){
        MaterialTheme(colorScheme=lightColorScheme(primary=Gold)){
            AuthScreen(auth){user=it}
        }
        return
    }
    var dark by remember{mutableStateOf(true)}
    var tab by remember{mutableStateOf(GTab.HOME)}
    var overlay by remember{mutableStateOf<String?>(null)}
    val accents=listOf(Color(0xFFFFCF4A),Color(0xFFA48BFF),Color(0xFF4DF2C1),Color(0xFFFF7A93))
    var accent by remember{mutableStateOf(0)}
    val a=accents[accent]; val a2=listOf(Color(0xFFFF8A4C),Color(0xFF4FD8FF),Color(0xFF59A8FF),Color(0xFFFFB35C))[accent]
    val bg=if(dark)Color(0xFF0B0A12) else Color(0xFFF4F0FF)
    val text=if(dark)Color(0xFFF6F3FF) else Color(0xFF17123A)
    val mute=if(dark)Color(0xFFA7A1C4) else Color(0xFF615B88)
    MaterialTheme(colorScheme=if(dark)darkColorScheme(background=bg,surface=Color.White.copy(alpha=.055f),primary=a,onPrimary=Color(0xFF14112A))else lightColorScheme(background=bg,surface=Color.White.copy(alpha=.78f),primary=a,onPrimary=Color(0xFF14112A))){
        Box(Modifier.fillMaxSize().background(bg)){
            GenBackground(a,a2,dark)
            Column(Modifier.fillMaxSize()){
                GenTopBar(dark,a,a2,{dark=!dark},{overlay="account"})
                Box(Modifier.weight(1f)){
                    AnimatedContent(tab,transitionSpec={fadeIn(tween(220))+slideInVertically{it/12} togetherWith fadeOut(tween(120))}){t->
                        when(t){
                            GTab.HOME->GenHome(a,a2,text,mute){tab=it}
                            GTab.MARKETS->GenMarkets(a,a2,text,mute)
                            GTab.AUTO->GenAuto(a,a2,text,mute)
                            GTab.CALC->GenLab(a,a2,text,mute)
                            GTab.MORE->GenMore(a,a2,text,mute,dark,{dark=!dark},{accent=it},{overlay=it})
                        }
                    }
                }
                GenDock(tab,a,a2,mute){tab=it}
            }
        }
        if(overlay!=null){when(overlay){"deposit"->DepositScreen{overlay=null};"withdraw"->WithdrawalScreen{overlay=null};"funding"->FundingHistoryScreen{overlay=null};"referrals"->Referral{overlay=null};"notifications"->NotificationsScreen{overlay=null};"activity"->ActivityScreen{overlay=null};else->GenSheet(overlay!!,a){overlay=null}}}
    }
}

@Composable private fun GenBackground(a:Color,a2:Color,dark:Boolean){
    val inf=rememberInfiniteTransition(label="bg")
    val x by inf.animateFloat(0f,1f,infiniteRepeatable(tween(9000,easing=LinearEasing),RepeatMode.Reverse),label="x")
    Canvas(Modifier.fillMaxSize()){
        drawCircle(a.copy(alpha=if(dark).20f else .14f),size.minDimension*.55f,Offset(size.width*.05f+x*40f,size.height*.02f))
        drawCircle(Color(0xFF7B5CFF).copy(alpha=if(dark).18f else .10f),size.minDimension*.58f,Offset(size.width*.98f-x*35f,size.height*.96f))
        drawCircle(a2.copy(alpha=.08f),size.minDimension*.38f,Offset(size.width*.55f,size.height*.45f))
    }
}

@Composable private fun GenTopBar(dark:Boolean,a:Color,a2:Color,onTheme:()->Unit,onInfo:()->Unit){
    Row(Modifier.fillMaxWidth().padding(16.dp,12.dp,16.dp,6.dp),verticalAlignment=Alignment.CenterVertically){
        Box(Modifier.size(31.dp).background(Brush.linearGradient(listOf(a,a2)),CircleShape),contentAlignment=Alignment.Center){Icon(Icons.Default.AutoAwesome,null,tint=Color(0xFF14112A),modifier=Modifier.size(18.dp))}
        Text("aster",fontSize=21.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(start=8.dp))
        Spacer(Modifier.weight(1f))
        Text("LIVE",color=a,fontSize=9.sp,fontWeight=FontWeight.Black,modifier=Modifier.background(a.copy(alpha=.12f),RoundedCornerShape(99.dp)).padding(horizontal=10.dp,vertical=7.dp))
        IconButton(onClick=onInfo){Icon(Icons.Default.Bolt,null,tint=a)}
        IconButton(onClick=onTheme){Icon(if(dark)Icons.Default.LightMode else Icons.Default.DarkMode,null,tint=a)}
    }
}

@Composable private fun GenHome(a:Color,a2:Color,text:Color,mute:Color,go:(GTab)->Unit){
    val ctx=LocalContext.current; val account=remember{AccountRepository(ctx)}
    var summary by remember{mutableStateOf<AccountSummary?>(null)}
    LaunchedEffect(Unit){summary=account.summary().getOrNull()}
    val total=summary?.total?:0.0
    LazyColumn(contentPadding=PaddingValues(16.dp,4.dp,16.dp,125.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{Text("gm 👋",fontSize=30.sp,fontWeight=FontWeight.Black,color=text);Text("Your Aster command center.",color=mute,fontSize=13.sp)}
        item{GlassCard(a,a2,true){Text("TOTAL BALANCE · VERIFIED",color=Color(0xFF14112A).copy(alpha=.72f),fontSize=11.sp,fontWeight=FontWeight.Bold);Text(if(summary==null)"— — —" else fmt(total),fontSize=46.sp,fontWeight=FontWeight.Black,color=Color(0xFF14112A));Text("USDT",color=Color(0xFF14112A).copy(alpha=.7f),fontSize=10.sp,fontWeight=FontWeight.Bold);Spacer(Modifier.height(14.dp));PulseBand(Color(0xFF14112A));Row(horizontalArrangement=Arrangement.spacedBy(9.dp),modifier=Modifier.padding(top=12.dp)){Button({go(GTab.AUTO)},colors=ButtonDefaults.buttonColors(Color(0xFF14112A)),shape=RoundedCornerShape(16.dp),modifier=Modifier.weight(1f)){Text("Auto-Invest",color=Color.White,fontWeight=FontWeight.Black,fontSize=10.sp)};Button({go(GTab.MARKETS)},colors=ButtonDefaults.buttonColors(Color(0x3314112A)),shape=RoundedCornerShape(16.dp),modifier=Modifier.weight(1f)){Text("Markets",color=Color(0xFF14112A),fontWeight=FontWeight.Black,fontSize=10.sp)}}}}
        item{Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){StatTile("LEVEL","1",a,Modifier.weight(1f));StatTile("LIVE PLANS","—",a,Modifier.weight(1f));StatTile("BEST WEEK","—",a,Modifier.weight(1f))}}
        item{SectionTitle("QUICK ACCESS",a)}
        item{Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(10.dp)){QuickTile("Deposit",Icons.Default.SouthWest,a){go(GTab.MORE)};QuickTile("Invest",Icons.Default.AutoGraph,a){go(GTab.AUTO)};QuickTile("Markets",Icons.Default.ShowChart,a){go(GTab.MARKETS)};QuickTile("Lab",Icons.Default.Calculate,a){go(GTab.CALC)}}}
        item{SectionTitle("ASTER ENERGY",a)}
        item{GlassCard(a,a2,false){Text("Invest. Automate. Compound.",fontSize=19.sp,fontWeight=FontWeight.Black,color=text);Text("Fast interactions, tactile feedback and server-backed account data.",color=mute,fontSize=11.sp,modifier=Modifier.padding(top=5.dp));Text("Target figures are illustrative — never guaranteed.",color=a,fontSize=9.sp,modifier=Modifier.padding(top=9.dp))}}
    }
}

@Composable private fun GenMarkets(a:Color,a2:Color,text:Color,mute:Color){
    var filter by remember{mutableStateOf("ALL")}
    val rows=if(filter=="FOREX")listOf("EUR/USD" to "1.0820","GBP/USD" to "1.2710","USD/JPY" to "151.40","XAU/USD" to "2350.0")else if(filter=="CRYPTO")listOf("BTC/USDT" to "—","ETH/USDT" to "—","SOL/USDT" to "—","BNB/USDT" to "—")else listOf("BTC/USDT" to "—","ETH/USDT" to "—","SOL/USDT" to "—","EUR/USD" to "1.0820")
    LazyColumn(contentPadding=PaddingValues(16.dp,4.dp,16.dp,125.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{Text("Markets",fontSize=30.sp,fontWeight=FontWeight.Black,color=text);Text("Rates, movers & market intelligence.",color=mute,fontSize=13.sp)}
        item{GlassCard(a,a2,false){Row(verticalAlignment=Alignment.CenterVertically){MarketMood(a);Column{Text("MARKET MOOD",color=mute,fontSize=9.sp,fontWeight=FontWeight.Bold);Text("Chill",fontSize=24.sp,fontWeight=FontWeight.Black,color=text);Text("Nothing dramatic right now.",color=mute,fontSize=9.sp)}}}}
        item{Segment(filter,a){filter=it}}
        item{GlassCard(a,a2,false){rows.forEachIndexed{idx,(name,price)->MarketRow(name,price,if(idx%2==0)"+1.42%" else "-0.64%",a,mute,text)}}}
        item{GlassCard(a,a2,false){Text("LATEST MARKET NEWS",color=a,fontSize=9.sp,fontWeight=FontWeight.Black);Text("Headlines worth watching",fontSize=18.sp,fontWeight=FontWeight.Black,color=text,modifier=Modifier.padding(top=5.dp));Text("Live articles are supplied by the production market-data layer.",color=mute,fontSize=10.sp,modifier=Modifier.padding(top=3.dp))}}
    }
}

@Composable private fun GenAuto(a:Color,a2:Color,text:Color,mute:Color){
    val ctx=LocalContext.current; val repo=remember{InvestmentRepository(ctx)}; val scope=rememberCoroutineScope()
    var crypto by remember{mutableStateOf(true)};var amount by remember{mutableStateOf("1000")};var weeks by remember{mutableStateOf(4f)};var rate by remember{mutableStateOf(22.5f)};var compound by remember{mutableStateOf(true)};var message by remember{mutableStateOf<String?>(null)}
    val principal=amount.toDoubleOrNull()?:0.0;val projected=principal*(1+rate/100).pow(weeks)
    LazyColumn(contentPadding=PaddingValues(16.dp,4.dp,16.dp,125.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{Text("Auto-Invest",fontSize=30.sp,fontWeight=FontWeight.Black,color=text);Text("Build your strategy. Keep it transparent.",color=mute,fontSize=13.sp)}
        item{Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){StrategyCard("₿","Crypto","Wild swings",crypto,a,Modifier.weight(1f)){crypto=true};StrategyCard("FX","Forex","Steadier moves",!crypto,a,Modifier.weight(1f)){crypto=false}}}
        item{GlassCard(a,a2,false){Text(if(crypto)"CRYPTO AUTO-INVEST" else "FOREX AUTO-INVEST",color=a,fontSize=9.sp,fontWeight=FontWeight.Black);Text("Weekly target range",color=mute,fontSize=10.sp,modifier=Modifier.padding(top=4.dp));Text("20–25%",fontSize=31.sp,fontWeight=FontWeight.Black,color=text);Text("Illustrative target, not a guaranteed return.",color=mute,fontSize=9.sp);Slider(weeks,{weeks=it},valueRange=1f..52f,colors=SliderDefaults.colors(thumbColor=a,activeTrackColor=a));Text(weeks.roundToInt().toString()+" weeks",color=text,fontWeight=FontWeight.Bold);Spacer(Modifier.height(6.dp));AmountSlider(principal,a){amount=it.toInt().toString()};Row(verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text("Compounding",fontWeight=FontWeight.Bold,color=text);Text("Keep gains invested when applicable",fontSize=9.sp,color=mute)};Switch(compound,{v:Boolean -> compound=v},colors=SwitchDefaults.colors(checkedThumbColor=Color(0xFF14112A),checkedTrackColor=a))};Text("ILLUSTRATIVE END VALUE",color=mute,fontSize=9.sp,modifier=Modifier.padding(top=10.dp));Text(fmt(projected),fontSize=38.sp,fontWeight=FontWeight.Black,color=a);Text("Principal "+fmt(principal)+" + projected "+fmt(projected-principal),color=mute,fontSize=9.sp);Button({scope.launch{repo.create(if(crypto)"crypto" else "forex",amount,rate.toString(),compound).onSuccess{message="Activated on the Aster server."}.onFailure{message=it.message?:"Activation failed."}}},colors=ButtonDefaults.buttonColors(a),shape=RoundedCornerShape(16.dp),modifier=Modifier.fillMaxWidth()){Text("Activate strategy",color=Color(0xFF14112A),fontWeight=FontWeight.Black)};message?.let{Text(it,color=if(it.startsWith("Activated"))Color(0xFF4DF2C1) else a,fontSize=9.sp,modifier=Modifier.padding(top=8.dp))}}}
    }
}

@Composable private fun GenLab(a:Color,a2:Color,text:Color,mute:Color){
    var amount by remember{mutableStateOf(1000f)};var rate by remember{mutableStateOf(22.5f)};var weeks by remember{mutableStateOf(4f)};val result=amount*(1+rate/100).pow(weeks)
    LazyColumn(contentPadding=PaddingValues(16.dp,4.dp,16.dp,125.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{Text("Compounding Lab",fontSize=30.sp,fontWeight=FontWeight.Black,color=text);Text("Play with the math. Reality stays server-side.",color=mute,fontSize=13.sp)}
        item{GlassCard(a,a2,false){LabSlider("Starting amount",amount,100f,10000f,a){amount=it};LabSlider("Weekly projection %",rate,0f,30f,a){rate=it};LabSlider("Weeks",weeks,1f,52f,a){weeks=it};Text("ILLUSTRATIVE END VALUE",color=mute,fontSize=9.sp,modifier=Modifier.padding(top=8.dp));Text(fmt(result.toDouble()),fontSize=43.sp,fontWeight=FontWeight.Black,color=a);Text("Principal "+fmt(amount.toDouble())+" + projected gain "+fmt((result-amount).toDouble()),color=mute,fontSize=10.sp);Text("This calculator does not predict or guarantee investment performance.",color=mute,fontSize=9.sp,modifier=Modifier.padding(top=8.dp))}}
    }
}

@Composable private fun GenMore(a:Color,a2:Color,text:Color,mute:Color,dark:Boolean,toggleTheme:()->Unit,setAccent:(Int)->Unit,open:(String)->Unit){
    LazyColumn(contentPadding=PaddingValues(16.dp,4.dp,16.dp,125.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{Text("More",fontSize=30.sp,fontWeight=FontWeight.Black,color=text);Text("Your account, funding and Aster tools.",color=mute,fontSize=13.sp)}
        item{GlassCard(a,a2,false){ProfileAction("Deposit USDT",Icons.Default.SouthWest,a){open("deposit")};ProfileAction("Withdraw USDT",Icons.Default.NorthEast,a){open("withdraw")};ProfileAction("Funding history",Icons.Default.AccountBalanceWallet,a){open("funding")};ProfileAction("Referrals",Icons.Default.People,a){open("referrals")};ProfileAction("Notifications",Icons.Default.Notifications,a){open("notifications")};ProfileAction("Activity",Icons.Default.ReceiptLong,a){open("activity")}}}
        item{GlassCard(a,a2,false){Text("APPEARANCE",color=a,fontSize=9.sp,fontWeight=FontWeight.Black);Row(Modifier.fillMaxWidth().padding(top=8.dp),verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text(if(dark)"Dark mode" else "Light mode",fontWeight=FontWeight.Bold,color=text);Text("Tap to switch the Aster atmosphere.",fontSize=9.sp,color=mute)};Switch(dark,{ _:Boolean -> toggleTheme()},colors=SwitchDefaults.colors(checkedThumbColor=Color(0xFF14112A),checkedTrackColor=a))};Text("Accent",color=mute,fontSize=9.sp,modifier=Modifier.padding(top=12.dp))}}
    }
}

@Composable private fun GlassCard(a:Color,a2:Color,hero:Boolean,content:@Composable ColumnScope.()->Unit){
    val shape=RoundedCornerShape(if(hero)30.dp else 24.dp)
    Box(Modifier.fillMaxWidth().clip(shape).background(if(hero)Brush.linearGradient(listOf(a,a2)) else Brush.linearGradient(listOf(MaterialTheme.colorScheme.surface,MaterialTheme.colorScheme.surface))).border(1.dp,Color.White.copy(alpha=.12f),shape).padding(16.dp)){Column(content=content)}
}
@Composable private fun SectionTitle(t:String,a:Color){Text(t,color=a,fontSize=9.sp,fontWeight=FontWeight.Black)}
@Composable private fun StatTile(label:String,value:String,a:Color,modifier:Modifier){Box(modifier){GlassCard(a,a,false){Text(label,fontSize=8.sp,color=MaterialTheme.colorScheme.onBackground.copy(alpha=.6f),fontWeight=FontWeight.Bold);Text(value,fontSize=23.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(top=2.dp))}}}
@Composable private fun QuickTile(t:String,i:ImageVector,a:Color,go:()->Unit){Box(Modifier.width(105.dp).clip(RoundedCornerShape(20.dp)).background(MaterialTheme.colorScheme.surface).clickable{go()}.padding(14.dp)){Column{Icon(i,null,tint=a,modifier=Modifier.size(22.dp));Text(t,fontSize=10.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(top=7.dp))}}}
@Composable private fun Segment(selected:String,a:Color,on:(String)->Unit){Row(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface,RoundedCornerShape(16.dp)).padding(4.dp)){listOf("ALL","CRYPTO","FOREX").forEach{x->Box(Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(if(selected==x)a else Color.Transparent).clickable{on(x)}.padding(10.dp),contentAlignment=Alignment.Center){Text(x,fontSize=9.sp,fontWeight=FontWeight.Black,color=if(selected==x)Color(0xFF14112A)else MaterialTheme.colorScheme.onBackground)}}}}
@Composable private fun MarketMood(a:Color){Canvas(Modifier.size(105.dp,65.dp)){drawArc(a.copy(alpha=.2f),180f,180f,false,style=Stroke(10f));drawArc(a,200f,55f,false,style=Stroke(10f));drawCircle(a,6f,Offset(53f,56f));drawLine(Color.White.copy(alpha=.8f),Offset(53f,56f),Offset(70f,34f),4f)}}
@Composable private fun MarketRow(name:String,price:String,change:String,a:Color,mute:Color,text:Color){Row(Modifier.fillMaxWidth().padding(vertical=9.dp),verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text(name,fontWeight=FontWeight.Bold,color=text,fontSize=12.sp);Text("Live feed",fontSize=8.sp,color=mute)};Text(price,fontWeight=FontWeight.Bold,fontSize=12.sp,color=text);Text(change,color=if(change.startsWith("+"))Color(0xFF4DF2C1) else Color(0xFFFF6B8B),fontSize=10.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(start=10.dp))}}
@Composable private fun StrategyCard(code:String,title:String,sub:String,selected:Boolean,a:Color,modifier:Modifier,go:()->Unit){Box(modifier.clip(RoundedCornerShape(25.dp)).background(MaterialTheme.colorScheme.surface).border(1.5.dp,if(selected)a else Color.White.copy(alpha=.1f),RoundedCornerShape(25.dp)).clickable{go()}.padding(16.dp)){Column{Box(Modifier.size(50.dp).background(Brush.linearGradient(listOf(a,Color(0xFFFF8A4C))),CircleShape),contentAlignment=Alignment.Center){Text(code,fontWeight=FontWeight.Black,color=Color(0xFF14112A))};Text(title,fontSize=17.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(top=10.dp));Text(sub,color=MaterialTheme.colorScheme.onBackground.copy(alpha=.65f),fontSize=9.sp);if(selected)Text("✓ SELECTED",color=a,fontSize=8.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(top=8.dp))}}}
@Composable private fun AmountSlider(value:Double,a:Color,on:(Double)->Unit){Text("HOW MUCH",color=MaterialTheme.colorScheme.onBackground.copy(alpha=.65f),fontSize=9.sp,fontWeight=FontWeight.Bold);Text(fmt(value,0),fontSize=34.sp,fontWeight=FontWeight.Black);Slider(value=value.toFloat(),onValueChange={on(it.toDouble())},valueRange=10f..10000f,colors=SliderDefaults.colors(thumbColor=a,activeTrackColor=a))}
@Composable private fun LabSlider(label:String,v:Float,min:Float,max:Float,a:Color,on:(Float)->Unit){Row{Text(label,fontSize=10.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f));Text(if(label.contains("%"))"%.1f".format(v) else "%.0f".format(v),color=a,fontWeight=FontWeight.Black,fontSize=11.sp)};Slider(v,onValueChange=on,valueRange=min..max,colors=SliderDefaults.colors(thumbColor=a,activeTrackColor=a))}
@Composable private fun PulseBand(c:Color){
    val inf=rememberInfiniteTransition(label="pulse")
    val p by inf.animateFloat(0.25f,1f,infiniteRepeatable(tween(1200),RepeatMode.Reverse),label="pulseAlpha")
    Row(Modifier.fillMaxWidth().height(18.dp),horizontalArrangement=Arrangement.spacedBy(5.dp),verticalAlignment=Alignment.CenterVertically){
        repeat(18){i->Box(Modifier.width(8.dp).height((7+(i%5)*3).dp).clip(RoundedCornerShape(99.dp)).background(c.copy(alpha=(.16f+p*(.10f+i%3*.04f)))) )}
    }
}
@Composable private fun AccentDot(color:Color,selected:Boolean,onClick:()->Unit){
    val h=LocalHapticFeedback.current
    Box(Modifier.size(30.dp).clip(CircleShape).background(color).border(if(selected)2.dp else 0.dp,Color.White,CircleShape).clickable{
        h.performHapticFeedback(HapticFeedbackType.LongPress);onClick()
    })
}
private fun fmt(v:Number,d:Int=2)=NumberFormat.getNumberInstance(Locale.US).apply{minimumFractionDigits=d;maximumFractionDigits=d}.format(v.toDouble())
@Composable private fun GenDock(tab:GTab,a:Color,a2:Color,mute:Color,go:(GTab)->Unit){Row(Modifier.fillMaxWidth().padding(12.dp,5.dp,12.dp,12.dp).clip(RoundedCornerShape(27.dp)).background(MaterialTheme.colorScheme.surface).border(1.dp,Color.White.copy(alpha=.1f),RoundedCornerShape(27.dp)).padding(5.dp),horizontalArrangement=Arrangement.SpaceEvenly){GTab.values().forEach{t->Box(Modifier.weight(1f).clip(RoundedCornerShape(20.dp)).background(if(tab==t)Brush.linearGradient(listOf(a,a2))else Brush.linearGradient(listOf(Color.Transparent,Color.Transparent))).clickable{go(t)}.padding(vertical=9.dp),contentAlignment=Alignment.Center){Column(horizontalAlignment=Alignment.CenterHorizontally){Icon(t.icon,null,modifier=Modifier.size(19.dp),tint=if(tab==t)Color(0xFF14112A)else mute);Text(t.label,fontSize=7.sp,fontWeight=FontWeight.Bold,color=if(tab==t)Color(0xFF14112A)else mute)}}}}}
@Composable private fun ProfileAction(t:String,i:ImageVector,a:Color,go:()->Unit){Row(Modifier.fillMaxWidth().clickable{go()}.padding(vertical=13.dp),verticalAlignment=Alignment.CenterVertically){Icon(i,null,tint=a,modifier=Modifier.size(20.dp));Text(t,fontSize=12.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f).padding(start=12.dp));Icon(Icons.Default.ChevronRight,null,tint=MaterialTheme.colorScheme.onBackground.copy(alpha=.35f))}}
@Composable private fun GenSheet(type:String,a:Color,close:()->Unit){ModalBottomSheet(onDismissRequest=close){Column(Modifier.padding(8.dp,8.dp,8.dp,30.dp)){Text(type.replaceFirstChar{it.uppercase()},fontSize=23.sp,fontWeight=FontWeight.Black);Text("The complete Aster workflow opens here.",color=MaterialTheme.colorScheme.onBackground.copy(alpha=.65f),fontSize=11.sp,modifier=Modifier.padding(top=5.dp));Button(onClick=close,colors=ButtonDefaults.buttonColors(a)){Text("Continue",color=Color(0xFF14112A),fontWeight=FontWeight.Black)}}}}
