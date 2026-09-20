package com.asterfinancials.app

import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.*
import androidx.compose.ui.draw.*
import androidx.compose.ui.graphics.*
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.*

private val NeonGold=Color(0xFFFFCF4A)
private val NeonViolet=Color(0xFFA48BFF)
private val NeonMint=Color(0xFF4DF2C1)
private val NeonCoral=Color(0xFFFF7A93)
private val GenZInk=Color(0xFF14112A)

@Composable
fun GenZHome(balance:String,userName:String,onInvest:()->Unit,onMarkets:()->Unit,onFunding:()->Unit,onNotifications:()->Unit,dark:Boolean,accentIndex:Int=0){
    val palettes=listOf(
        Pair(NeonGold,Color(0xFFFF8A4C)),
        Pair(NeonViolet,Color(0xFF4FD8FF)),
        Pair(NeonMint,Color(0xFF59A8FF)),
        Pair(NeonCoral,Color(0xFFFFB35C))
    )
    val (accent,accent2)=palettes[accentIndex.coerceIn(0,3)]
    var rx by remember{mutableFloatStateOf(0f)}
    var ry by remember{mutableFloatStateOf(0f)}
    val transition=rememberInfiniteTransition(label="ambient")
    val drift by transition.animateFloat(
        initialValue=0f,targetValue=1f,
        animationSpec=infiniteRepeatable(tween(12000,easing=LinearEasing),RepeatMode.Reverse),
        label="drift"
    )
    Box(Modifier.fillMaxSize().background(if(dark)Color(0xFF0B0A12) else Color(0xFFF4F0FF))){
        Box(Modifier.size(330.dp).offset((-110).dp,(-90).dp).background(accent.copy(alpha=.14f),RoundedCornerShape(999.dp)).blur(70.dp))
        Box(Modifier.size(350.dp).align(Alignment.BottomEnd).offset(110.dp,100.dp).background(NeonViolet.copy(alpha=.13f),RoundedCornerShape(999.dp)).blur(70.dp))
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom=105.dp)){
            Row(Modifier.fillMaxWidth().padding(16.dp,12.dp,16.dp,6.dp),verticalAlignment=Alignment.CenterVertically){
                Column(Modifier.weight(1f)){
                    Text("ASTER",fontSize=21.sp,fontWeight=FontWeight.Black,letterSpacing=(-.8).sp)
                    Text("financial command center",fontSize=9.sp,color=MaterialTheme.colorScheme.onBackground.copy(.55f),fontWeight=FontWeight.SemiBold)
                }
                IconButton(onClick=onNotifications){Icon(Icons.Default.NotificationsNone,"Notifications")}
            }
            Box(
                Modifier.fillMaxWidth().padding(horizontal=16.dp)
                    .pointerInput(Unit){
                        detectDragGestures(
                            onDrag={change,amount->change.consume();ry=(ry+amount.x*.06f).coerceIn(-7f,7f);rx=(rx-amount.y*.06f).coerceIn(-7f,7f)},
                            onDragEnd={rx=0f;ry=0f}
                        )
                    }
                    .graphicsLayer{rotationX=rx;rotationY=ry;cameraDistance=28*LocalDensity.current.density}
                    .clip(RoundedCornerShape(30.dp))
                    .background(Brush.linearGradient(listOf(accent,accent2)))
                    .shadow(24.dp,RoundedCornerShape(30.dp),ambientColor=accent2,spotColor=accent)
            ){
                Column(Modifier.padding(20.dp)){
                    Text("TOTAL PORTFOLIO",fontSize=11.sp,fontWeight=FontWeight.Bold,color=GenZInk.copy(.68f))
                    Text(balance,fontSize=42.sp,fontWeight=FontWeight.Black,color=GenZInk,letterSpacing=(-1.6).sp)
                    Row(verticalAlignment=Alignment.CenterVertically){
                        Surface(shape=RoundedCornerShape(99.dp),color=GenZInk.copy(.13f)){Text("● LIVE ACCOUNT",fontSize=8.sp,fontWeight=FontWeight.ExtraBold,color=GenZInk,modifier=Modifier.padding(8.dp,5.dp))}
                        Spacer(Modifier.width(8.dp))
                        Text(userName.ifBlank{"Aster member"},fontSize=10.sp,fontWeight=FontWeight.Bold,color=GenZInk.copy(.7f))
                    }
                    Spacer(Modifier.height(18.dp))
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)){
                        GenAction(Modifier.weight(1f),"AUTO-INVEST",Icons.Default.AutoGraph,GenZInk.copy(.95f),onInvest)
                        GenAction(Modifier.weight(1f),"MARKETS",Icons.Default.TrendingUp,GenZInk.copy(.13f),onMarkets)
                        GenAction(Modifier.weight(1f),"FUNDING",Icons.Default.SwapHoriz,GenZInk.copy(.13f),onFunding)
                    }
                }
            }
            Row(Modifier.fillMaxWidth().padding(16.dp),horizontalArrangement=Arrangement.spacedBy(10.dp)){
                GenStat(Modifier.weight(1f),"XP","LVL 04","72%",accent)
                GenStat(Modifier.weight(1f),"REFERRALS","15%","ACTIVE",NeonViolet)
                GenStat(Modifier.weight(1f),"SECURITY","2FA","READY",NeonMint)
            }
            GenSectionTitle("QUICK FLOW","Designed to feel alive")
            Row(Modifier.fillMaxWidth().padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(10.dp)){
                GenTile(Modifier.weight(1f),"Deposit","Verify on-chain",Icons.Default.Security,accent,onFunding)
                GenTile(Modifier.weight(1f),"Invest","Build your plan",Icons.Default.Bolt,accent2,onInvest)
            }
            GenSectionTitle("YOUR EDGE","Aster intelligence")
            Card(Modifier.fillMaxWidth().padding(horizontal=16.dp),colors=CardDefaults.cardColors(containerColor=if(dark)Color.White.copy(.06f) else Color.White.copy(.72f)),shape=RoundedCornerShape(24.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("SMART ALLOCATION",fontSize=9.sp,fontWeight=FontWeight.ExtraBold,color=accent)
                    Text("Crypto + Forex",fontSize=20.sp,fontWeight=FontWeight.Black)
                    Text("Server-controlled investment accounting. Your app never invents a return.",fontSize=10.sp,color=MaterialTheme.colorScheme.onBackground.copy(.6f),modifier=Modifier.padding(top=3.dp))
                }
            }
            Spacer(Modifier.height(20.dp))
            Text("Aster · built for the next generation",fontSize=9.sp,color=MaterialTheme.colorScheme.onBackground.copy(.42f),modifier=Modifier.align(Alignment.CenterHorizontally))
        }
    }
}

@Composable private fun GenAction(modifier:Modifier,label:String,icon:androidx.compose.ui.graphics.vector.ImageVector,background:Color,onClick:()->Unit){
    Button(onClick=onClick,modifier=modifier.height(48.dp),shape=RoundedCornerShape(16.dp),colors=ButtonDefaults.buttonColors(containerColor=background,contentColor=if(background==Color.White)GenZInk else if(background.alpha>.5f)GenZInk else Color.White),contentPadding=PaddingValues(5.dp)){
        Icon(icon,null,Modifier.size(16.dp));Spacer(Modifier.width(4.dp));Text(label,fontSize=7.sp,fontWeight=FontWeight.Black)
    }
}
@Composable private fun GenStat(modifier:Modifier,title:String,value:String,sub:String,color:Color){
    Card(modifier=modifier,shape=RoundedCornerShape(20.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface.copy(.72f))){
        Column(Modifier.padding(12.dp)){Text(title,fontSize=8.sp,fontWeight=FontWeight.Bold,color=color);Text(value,fontSize=18.sp,fontWeight=FontWeight.Black);Text(sub,fontSize=7.sp,color=MaterialTheme.colorScheme.onBackground.copy(.55f))}
    }
}
@Composable private fun GenSectionTitle(title:String,sub:String){
    Column(Modifier.padding(18.dp,10.dp,16.dp,4.dp)){Text(title,fontSize=10.sp,fontWeight=FontWeight.Black,color=MaterialTheme.colorScheme.primary,letterSpacing=1.sp);Text(sub,fontSize=8.sp,color=MaterialTheme.colorScheme.onBackground.copy(.5f))}
}
@Composable private fun GenTile(modifier:Modifier,title:String,sub:String,icon:androidx.compose.ui.graphics.vector.ImageVector,color:Color,onClick:()->Unit){
    Card(onClick=onClick,modifier=modifier,shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface.copy(.75f))){
        Column(Modifier.padding(15.dp)){Surface(shape=RoundedCornerShape(14.dp),color=color.copy(.18f)){Icon(icon,null,tint=color,modifier=Modifier.padding(10.dp).size(19.dp))};Text(title,fontSize=15.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(top=12.dp));Text(sub,fontSize=8.sp,color=MaterialTheme.colorScheme.onBackground.copy(.55f))}
    }
}
