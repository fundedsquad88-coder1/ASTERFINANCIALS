package com.asterfinancials.app

import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.*
import androidx.compose.ui.draw.*
import androidx.compose.ui.graphics.*
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.*
import kotlin.math.*

private val NeonGold=Color(0xFFFFCF4A)
private val NeonViolet=Color(0xFFA48BFF)
private val NeonMint=Color(0xFF4DF2C1)
private val NeonCoral=Color(0xFFFF7A93)
private val GenZInk=Color(0xFF14112A)

@Composable
fun GenZTheme(
    dark:Boolean,
    accent:Int=0,
    content:@Composable()->Unit
){
    val a=listOf(NeonGold,NeonViolet,NeonMint,NeonCoral)[accent.coerceIn(0,3)]
    val a2=listOf(Color(0xFFFF8A4C),Color(0xFF4FD8FF),Color(0xFF59A8FF),Color(0xFFFFB35C))[accent.coerceIn(0,3)]
    val scheme=if(dark) darkColorScheme(background=Color(0xFF0B0A12),surface=Color(0x0FFFFFFF),primary=a,onPrimary=GenZInk,onBackground=Color(0xFFF6F3FF),onSurface=Color(0xFFF6F3FF))
    else lightColorScheme(background=Color(0xFFF4F0FF),surface=Color(0xCCFFFFFF),primary=a,onPrimary=GenZInk,onBackground=GenZInk,onSurface=GenZInk)
    CompositionLocalProvider(LocalGenAccent provides Pair(a,a2)){
        MaterialTheme(colorScheme=scheme,typography=Typography().run{copy(headlineLarge=titleLarge.copy(fontWeight=FontWeight.ExtraBold),headlineMedium=titleMedium.copy(fontWeight=FontWeight.ExtraBold))}){content()}
    }
}

private val LocalGenAccent=compositionLocalOf{Pair(NeonGold,Color(0xFFFF8A4C))}

@Composable private fun GenBlob(modifier:Modifier=Modifier, color:Color, alpha:Float){
    Box(modifier.background(color.copy(alpha=alpha),RoundedCornerShape(999.dp)).blur(60.dp))
}

@Composable fun GenZHome(
    balance:String,
    userName:String,
    onInvest:()->Unit,
    onMarkets:()->Unit,
    onFunding:()->Unit,
    onProfile:()->Unit,
    onNotifications:()->Unit,
    dark:Boolean,
    onToggleTheme:()->Unit
){
    val (accent,accent2)=LocalGenAccent.current
    var rx by remember{mutableFloatStateOf(0f)}
    var ry by remember{mutableFloatStateOf(0f)}
    val infinite=rememberInfiniteTransition(label="ambient")
    val drift by infinite.animateFloat(0f,1f,infiniteRepeatable(tween(12000,Easing.LinearEasing),RepeatMode.Reverse),label="drift")
    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)){
        GenBlob(Modifier.size(330.dp).offset((-110).dp,(-90).dp),accent,.18f)
        GenBlob(Modifier.size(360.dp).align(Alignment.BottomEnd).offset(120.dp,100.dp),NeonViolet,.16f)
        GenBlob(Modifier.size(220.dp).align(Alignment.Center).offset((drift*80-40).dp),accent2,.08f)
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom=100.dp)){
            Row(Modifier.fillMaxWidth().padding(16.dp,12.dp,16.dp,6.dp),verticalAlignment=Alignment.CenterVertically){
                Column(Modifier.weight(1f)){
                    Text("ASTER",fontSize=21.sp,fontWeight=FontWeight.Black,letterSpacing=(-.8).sp)
                    Text("financial command center",fontSize=9.sp,color=MaterialTheme.colorScheme.onSurface.copy(.55f),fontWeight=FontWeight.SemiBold)
                }
                IconButton(onClick=onNotifications){Icon(Icons.Default.NotificationsNone,"Notifications")}
                IconButton(onClick=onToggleTheme){Icon(if(dark)Icons.Default.LightMode else Icons.Default.DarkMode,"Theme")}
            }
            val card=Modifier.fillMaxWidth().padding(horizontal=16.dp)
            Box(card.pointerInput(Unit){
                detectDragGestures(onDrag={change,amount->
                    change.consume()
                    ry=(ry+amount.x*.06f).coerceIn(-7f,7f)
                    rx=(rx-amount.y*.06f).coerceIn(-7f,7f)
                },onDragEnd={rx=0f;ry=0f})
            }.graphicsLayer{rotationX=rx;rotationY=ry;cameraDistance=28*LocalDensity.current.density}.clip(RoundedCornerShape(30.dp))
             .background(Brush.linearGradient(listOf(accent,accent2)))
             .shadow(22.dp,shape=RoundedCornerShape(30.dp),ambientColor=accent2,spotColor=accent)){
                Box(Modifier.fillMaxWidth().padding(20.dp)){
                    Column{
                        Text("TOTAL PORTFOLIO",fontSize=11.sp,fontWeight=FontWeight.Bold,color=GenZInk.copy(.68f))
                        Text(balance,fontSize=42.sp,fontWeight=FontWeight.Black,color=GenZInk,letterSpacing=(-1.6).sp)
                        Row(verticalAlignment=Alignment.CenterVertically){
                            Surface(shape=RoundedCornerShape(99.dp),color=GenZInk.copy(.13f)){Text("● LIVE ACCOUNT",fontSize=8.sp,fontWeight=FontWeight.ExtraBold,color=GenZInk,modifier=Modifier.padding(8.dp,5.dp))}
                            Spacer(Modifier.width(8.dp));Text(userName.ifBlank{"Aster member"},fontSize=10.sp,fontWeight=FontWeight.Bold,color=GenZInk.copy(.7f))
                        }
                        Spacer(Modifier.height(18.dp))
                        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(9.dp)){
                            GenAction("AUTO-INVEST",Icons.Default.AutoGraph,accent,onInvest)
                            GenAction("MARKETS",Icons.Default.TrendingUp,GenZInk.copy(.13f),onMarkets)
                            GenAction("FUNDING",Icons.Default.SwapHoriz,GenZInk.copy(.13f),onFunding)
                        }
                    }
                    Box(Modifier.align(Alignment.TopEnd).size(74.dp).clip(RoundedCornerShape(50.dp)).background(Color.White.copy(.16f)).blur(1.dp))
                }
            }
            Row(Modifier.fillMaxWidth().padding(16.dp),horizontalArrangement=Arrangement.spacedBy(10.dp)){
                GenStat("XP","LVL 04","72%",accent)
                GenStat("REFERRALS","15%","ACTIVE",NeonViolet)
                GenStat("SECURITY","2FA","READY",NeonMint)
            }
            GenSectionTitle("QUICK FLOW","Designed to feel alive")
            Row(Modifier.fillMaxWidth().padding(horizontal=16.dp),horizontalArrangement=Arrangement.spacedBy(10.dp)){
                GenTile("Deposit","Verify on-chain",Icons.Default.Security,accent,onFunding)
                GenTile("Invest","Build your plan",Icons.Default.Bolt,accent2,onInvest)
            }
            GenSectionTitle("YOUR EDGE","Aster intelligence")
            Card(Modifier.fillMaxWidth().padding(horizontal=16.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface.copy(.72f)),shape=RoundedCornerShape(24.dp)){
                Column(Modifier.padding(16.dp)){
                    Text("SMART ALLOCATION",fontSize=9.sp,fontWeight=FontWeight.ExtraBold,color=accent)
                    Text("Crypto + Forex",fontSize=20.sp,fontWeight=FontWeight.Black)
                    Text("Server-controlled investment accounting. Your app never invents a return.",fontSize=10.sp,color=MaterialTheme.colorScheme.onSurface.copy(.6f),modifier=Modifier.padding(top=3.dp))
                }
            }
        }
    }
}

@Composable private fun GenAction(label:String,icon:androidx.compose.ui.graphics.vector.ImageVector,background:Color,onClick:()->Unit){
    Button(onClick=onClick,modifier=Modifier.weight(1f).height(48.dp),shape=RoundedCornerShape(16.dp),colors=ButtonDefaults.buttonColors(containerColor=background,contentColor=GenZInk),contentPadding=PaddingValues(6.dp)){
        Icon(icon,null,Modifier.size(17.dp));Spacer(Modifier.width(5.dp));Text(label,fontSize=8.sp,fontWeight=FontWeight.Black)
    }
}
@Composable private fun GenStat(title:String,value:String,sub:String,color:Color){
    Card(Modifier.weight(1f),shape=RoundedCornerShape(20.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface.copy(.72f))){
        Column(Modifier.padding(12.dp)){Text(title,fontSize=8.sp,fontWeight=FontWeight.Bold,color=color);Text(value,fontSize=18.sp,fontWeight=FontWeight.Black);Text(sub,fontSize=7.sp,color=MaterialTheme.colorScheme.onSurface.copy(.55f))}
    }
}
@Composable private fun GenSectionTitle(title:String,sub:String){
    Column(Modifier.padding(18.dp,10.dp,16.dp,4.dp)){Text(title,fontSize=10.sp,fontWeight=FontWeight.Black,color=MaterialTheme.colorScheme.primary,letterSpacing=1.sp);Text(sub,fontSize=8.sp,color=MaterialTheme.colorScheme.onSurface.copy(.5f))}
}
@Composable private fun GenTile(title:String,sub:String,icon:androidx.compose.ui.graphics.vector.ImageVector,color:Color,onClick:()->Unit){
    Card(onClick=onClick,modifier=Modifier.weight(1f),shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface.copy(.75f))){
        Column(Modifier.padding(15.dp)){Surface(shape=RoundedCornerShape(14.dp),color=color.copy(.18f)){Icon(icon,null,tint=color,modifier=Modifier.padding(10.dp).size(19.dp))};Text(title,fontSize=15.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(top=12.dp));Text(sub,fontSize=8.sp,color=MaterialTheme.colorScheme.onSurface.copy(.55f))}
    }
}
