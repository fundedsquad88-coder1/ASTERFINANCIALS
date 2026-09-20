package com.asterfinancials.app

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.*
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val AsterViolet = Color(0xFFA48BFF)
val AsterCyan = Color(0xFF4FD8FF)
val AsterMint = Color(0xFF4DF2C1)
val AsterCoral = Color(0xFFFF7A93)
val AsterGold = Color(0xFFFFCF4A)
val AsterOrange = Color(0xFFFF8A4C)
val AsterInk = Color(0xFF17123A)
val AsterNight = Color(0xFF0B0A12)
val AsterNightPanel = Color(0xFF151321)
val AsterLight = Color(0xFFF4F0FF)

enum class AsterAccent { GOLD, VIOLET, MINT, CORAL }

@Composable
fun AsterGenZTheme(
    dark: Boolean,
    accent: AsterAccent = AsterAccent.GOLD,
    content: @Composable () -> Unit
){
    val (a,a2)=when(accent){
        AsterAccent.GOLD->AsterGold to AsterOrange
        AsterAccent.VIOLET->AsterViolet to AsterCyan
        AsterAccent.MINT->AsterMint to Color(0xFF59A8FF)
        AsterAccent.CORAL->AsterCoral to Color(0xFFFFB35C)
    }
    val scheme=if(dark) darkColorScheme(
        background=AsterNight,surface=AsterNightPanel,surfaceVariant=Color(0xFF211E30),
        primary=a,onPrimary=AsterInk,onBackground=Color(0xFFF6F3FF),onSurface=Color(0xFFF6F3FF)
    ) else lightColorScheme(
        background=AsterLight,surface=Color.White,surfaceVariant=Color(0xFFEDE8FF),
        primary=a,onPrimary=AsterInk,onBackground=AsterInk,onSurface=AsterInk
    )
    MaterialTheme(colorScheme=scheme,typography=Typography(
        headlineLarge=LocalTextStyle.current.copy(fontSize=30.sp),
        titleLarge=LocalTextStyle.current.copy(fontSize=20.sp),
        bodyMedium=LocalTextStyle.current.copy(fontSize=14.sp)
    )){
        Box(Modifier.fillMaxSize().background(scheme.background)){
            AsterAmbientBackground(a,a2,dark)
            content()
        }
    }
}

@Composable
fun AsterAmbientBackground(a:Color,a2:Color,dark:Boolean){
    val transition=rememberInfiniteTransition(label="ambient")
    val shift by transition.animateFloat(
        initialValue=0f,targetValue=1f,
        animationSpec=infiniteRepeatable(tween(26000,easing=LinearEasing),RepeatMode.Reverse),
        label="shift"
    )
    Box(Modifier.fillMaxSize()){
        Box(Modifier.size(520.dp).offset((-180+80*shift).dp,(-210+50*shift).dp)
            .blur(75.dp).clip(CircleShape).background(a.copy(alpha=if(dark).18f else .14f)))
        Box(Modifier.size(500.dp).align(androidx.compose.ui.Alignment.BottomEnd)
            .offset((170-70*shift).dp,130.dp).blur(80.dp).clip(CircleShape)
            .background(AsterViolet.copy(alpha=if(dark).18f else .12f)))
        Box(Modifier.size(280.dp).offset((150*shift).dp,420.dp).blur(70.dp)
            .clip(CircleShape).background(a2.copy(alpha=.10f)))
    }
}

@Composable
fun GenZGlassCard(
    modifier:Modifier=Modifier,
    radius:Float=22f,
    content:@Composable ColumnScope.()->Unit
){
    Surface(
        modifier=modifier.border(1.dp,MaterialTheme.colorScheme.onSurface.copy(alpha=.08f),RoundedCornerShape(radius.dp)),
        shape=RoundedCornerShape(radius.dp),
        color=MaterialTheme.colorScheme.surface.copy(alpha=if(MaterialTheme.colorScheme.background==AsterNight).055f else .72f),
        tonalElevation=0.dp,
        shadowElevation=if(MaterialTheme.colorScheme.background==AsterNight)12.dp else 5.dp
    ){Column(Modifier.padding(16.dp),content=content)}
}

@Composable
fun GradientActionButton(
    text:String,
    modifier:Modifier=Modifier,
    onClick:()->Unit
){
    val brush=Brush.linearGradient(listOf(MaterialTheme.colorScheme.primary,AsterOrange))
    Box(modifier.clip(RoundedCornerShape(18.dp)).background(brush).clickableWithoutRipple(onClick).padding(vertical=15.dp,horizontal=16.dp)){
        Text(text,Modifier.fillMaxWidth(),color=AsterInk,fontSize=15.sp,fontWeight=androidx.compose.ui.text.font.FontWeight.ExtraBold)
    }
}

private fun Modifier.clickableWithoutRipple(onClick:()->Unit)=this.then(
    androidx.compose.foundation.clickable(
        interactionSource=remember { androidx.compose.foundation.interaction.MutableInteractionSource() },
        indication=null,onClick=onClick
    )
)
