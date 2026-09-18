package com.asterfinancials.app;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(8, 9, 11);
    private static final int SURFACE = Color.rgb(17, 19, 24);
    private static final int SURFACE_2 = Color.rgb(23, 26, 32);
    private static final int BORDER = Color.rgb(37, 40, 48);
    private static final int TEXT = Color.rgb(244, 242, 235);
    private static final int MUTED = Color.rgb(133, 138, 148);
    private static final int GOLD = Color.rgb(214, 167, 58);
    private static final int GOLD_LIGHT = Color.rgb(240, 206, 112);
    private static final int GREEN = Color.rgb(56, 207, 145);

    private LinearLayout content;
    private Button[] navButtons;
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Map<String, TextView> priceViews = new HashMap<>();
    private boolean light = false;

    private final String[] symbols = {"BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT"};
    private final String[] labels = {"BTC","ETH","SOL","BNB","XRP","DOGE"};
    private final String[] icons = {"₿","Ξ","S","B","X","D"};

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        buildApp();
        showTab(0);
        requestMarkets();
    }

    private void buildApp() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setPadding(dp(18), dp(8), dp(14), dp(8));
        TextView logo = text("◆  ASTER", 14, TEXT, true);
        logo.setLetterSpacing(.18f);
        top.addView(logo, new LinearLayout.LayoutParams(0, dp(52), 1));

        Button bell = button("♧", false);
        bell.setOnClickListener(v -> toast("Notifications will appear after account connection."));
        top.addView(bell, new LinearLayout.LayoutParams(dp(46), dp(46)));
        root.addView(top);

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        LinearLayout nav = new LinearLayout(this);
        nav.setPadding(dp(8), dp(6), dp(8), dp(8));
        nav.setGravity(Gravity.CENTER);
        nav.setBackgroundColor(Color.rgb(9,10,13));
        navButtons = new Button[5];
        String[] names = {"⌂\nHome","◷\nAuto-Invest","⌁\nMarkets","▣\nWallet","●\nProfile"};
        for (int i=0;i<5;i++) {
            final int index=i;
            Button b=button(names[i], false);
            b.setAllCaps(false);
            b.setTextSize(10);
            b.setGravity(Gravity.CENTER);
            b.setPadding(0,0,0,0);
            b.setMinHeight(0);
            b.setMinWidth(0);
            b.setOnClickListener(v -> showTab(index));
            navButtons[i]=b;
            nav.addView(b,new LinearLayout.LayoutParams(0,dp(64),1));
        }
        root.addView(nav,new LinearLayout.LayoutParams(-1,dp(78)));
        setContentView(root);
    }

    private void showTab(int index) {
        content.removeAllViews();
        priceViews.clear();
        for (int i=0;i<navButtons.length;i++) {
            navButtons[i].setTextColor(i==index ? GOLD_LIGHT : MUTED);
            navButtons[i].setBackground(round(i==index ? SURFACE_2 : Color.TRANSPARENT, i==index ? BORDER : Color.TRANSPARENT, 12));
        }
        if(index==0) home();
        else if(index==1) autoInvest();
        else if(index==2) markets();
        else if(index==3) wallet();
        else profile();
    }

    private void home() {
        header("Aster Financials", "A clearer way to ", "grow.");
        paragraph("A focused financial experience for Auto-Invest, wallet controls, market references and account management.");
        content.addView(balance());
        LinearLayout grid=new LinearLayout(this); grid.setOrientation(LinearLayout.VERTICAL);
        String[][] actions={{"↓","Deposit"},{"↑","Withdraw"},{"◷","Auto-Invest"},{"▣","Wallet"}};
        for(int r=0;r<2;r++){
            LinearLayout row=new LinearLayout(this);
            for(int c=0;c<2;c++){
                int idx=r*2+c; Button b=button(actions[idx][0]+"\n"+actions[idx][1],false);
                b.setGravity(Gravity.CENTER_VERTICAL); b.setPadding(dp(18),0,0,0); b.setTextSize(12);
                if(idx==2)b.setOnClickListener(v->showTab(1)); else if(idx==3)b.setOnClickListener(v->showTab(3)); else b.setOnClickListener(v->toast(actions[idx][1]+" requires secure account connection."));
                row.addView(b,weightParams(1,8));
            }
            grid.addView(row,new LinearLayout.LayoutParams(-1,dp(88)));
        }
        content.addView(grid);
        section("LIVE REFERENCE","Markets","Public data");
        LinearLayout mg=new LinearLayout(this); mg.setOrientation(LinearLayout.VERTICAL);
        for(int i=0;i<symbols.length;i++) mg.addView(marketCard(i));
        content.addView(mg);
        section("CORE PRODUCT","Auto-Invest","");
        autoCard("Crypto Auto-Invest","Automated strategy concept across major digital assets.","20–25% / week",true);
        autoCard("Forex Auto-Invest","Dedicated currency-market strategy concept.","20–25% / week",false);
        referral();
    }

    private LinearLayout balance() {
        LinearLayout x=cardLayout();
        x.addView(label("ACCOUNT BALANCE"));
        x.addView(text("— USDT",29,TEXT,true));
        x.addView(text("No connected account",11,MUTED,false));
        TextView s=text("●  Balance unavailable until account connection",10,MUTED,true);
        s.setPadding(dp(12),dp(9),dp(12),dp(9)); s.setBackground(round(SURFACE_2,Color.TRANSPARENT,20));
        x.addView(s,new LinearLayout.LayoutParams(-2,dp(38)));
        return x;
    }

    private void autoInvest() {
        header("Auto-Invest","Build a strategy. ","Repeat.");
        paragraph("Aster's core product experience, focused on Crypto and Forex Auto-Invest.");
        autoCard("Crypto Auto-Invest","Major digital assets with weekly progression and compounding controls.","20–25% / week",true);
        autoCard("Forex Auto-Invest","A dedicated currency-market option with transparent reporting and account controls.","20–25% / week",false);
        section("PROJECTION TOOL","Compounding","");
        LinearLayout calc=cardLayout();
        calc.addView(text("Illustrative end balance",8,MUTED,true));
        calc.addView(text("$2,073.60",24,GOLD_LIGHT,true));
        calc.addView(text("Compounded weekly · 4 weeks · 20.0%",10,MUTED,false));
        calc.addView(text("Illustrative calculator only. It does not represent an account balance, promised return, APR, or financial advice.",9,MUTED,false));
        content.addView(calc);
    }

    private void autoCard(String title,String desc,String rate,boolean crypto) {
        LinearLayout c=cardLayout();
        LinearLayout row=new LinearLayout(this); row.setGravity(Gravity.CENTER_VERTICAL);
        TextView ic=text(crypto?"₿":"◎",28,GOLD_LIGHT,true); ic.setGravity(Gravity.CENTER);
        ic.setBackground(round(SURFACE_2,Color.rgb(75,61,29),18));
        row.addView(ic,new LinearLayout.LayoutParams(dp(62),dp(62)));
        LinearLayout body=new LinearLayout(this); body.setPadding(dp(13),0,0,0);
        body.addView(text(title,14,TEXT,true)); body.addView(text(desc,10,MUTED,false)); body.addView(text(rate,18,GOLD_LIGHT,true));
        TextView note=text("Illustrative target range · not a guarantee.",8,MUTED,false); body.addView(note);
        Button start=button("Start Auto-Invest",true);
        start.setOnClickListener(v->toast("Live investing requires the finalized product, authenticated account and ledger backend."));
        body.addView(start,new LinearLayout.LayoutParams(-1,dp(40)));
        row.addView(body,new LinearLayout.LayoutParams(0,-2,1));
        c.addView(row);
    }

    private void markets() {
        header("Markets","Public market ","reference.");
        paragraph("Live reference data only. Values remain unavailable when the public feed cannot be reached.");
        for(int i=0;i<symbols.length;i++) content.addView(marketCard(i));
    }

    private View marketCard(int i) {
        LinearLayout c=cardLayout();
        LinearLayout top=new LinearLayout(this); top.setGravity(Gravity.CENTER_VERTICAL);
        TextView ic=text(icons[i],18,GOLD_LIGHT,true); ic.setGravity(Gravity.CENTER); ic.setBackground(round(SURFACE_2,Color.rgb(62,52,31),10));
        top.addView(ic,new LinearLayout.LayoutParams(dp(36),dp(36)));
        LinearLayout nm=new LinearLayout(this); nm.setPadding(dp(9),0,0,0);
        nm.addView(text(labels[i],12,TEXT,true)); nm.addView(text("USDT",8,MUTED,false));
        top.addView(nm,new LinearLayout.LayoutParams(0,-2,1));
        top.addView(text("›",20,MUTED,false));
        c.addView(top);
        TextView price=text("—",18,TEXT,true); priceViews.put(symbols[i],price); c.addView(price);
        c.addView(text("Waiting for live data",9,MUTED,false));
        c.setOnClickListener(v->toast(labels[i]+" market detail will open when the authenticated market service is connected."));
        return c;
    }

    private void wallet() {
        header("Wallet","Your assets, ","clearly.");
        paragraph("Ready for a real authenticated ledger. No simulated holdings are displayed.");
        LinearLayout c=cardLayout();
        c.addView(text("CONNECTED ACCOUNT",8,MUTED,true));
        c.addView(text("Not connected",24,TEXT,true));
        c.addView(text("Connect an authenticated Aster account to display balances and transaction history.",10,MUTED,false));
        Button connect=button("Connect account",true); connect.setOnClickListener(v->toast("Secure account connection is the next backend integration step."));
        c.addView(connect);
        content.addView(c);
        String[] a={"₮   USDT","₿   Bitcoin","Ξ   Ethereum"};
        for(String s:a){LinearLayout row=cardLayout();row.addView(text(s,12,TEXT,true));row.addView(text("—",10,MUTED,false));content.addView(row);}
    }

    private void profile() {
        header("Account","Control your ","Aster.");
        paragraph("Account, security, referral and legal controls.");
        LinearLayout c=cardLayout();
        c.addView(row("Account","Not connected","Connect",true));
        c.addView(row("Security","Authentication, 2FA & device controls","›",false));
        c.addView(row("Referral","Links, activity & rewards","›",false));
        c.addView(row("Notifications","Alerts & account activity","›",false));
        c.addView(row("Theme",light?"Premium light":"Premium dark",light?"○":"●",false));
        content.addView(c);
        section("LEGAL","Aster information","");
        Button terms=button("Terms of Use",false); terms.setOnClickListener(v->toast("Platform rules will appear after legal content is finalized.")); content.addView(terms);
        Button risk=button("Risk Disclosure",false); risk.setOnClickListener(v->toast("Market-linked products can involve substantial loss. Illustrative performance is not a guarantee.")); content.addView(risk);
        Button privacy=button("Privacy Policy",false); privacy.setOnClickListener(v->toast("Privacy controls will be finalized with account and compliance integration.")); content.addView(privacy);
    }

    private View row(String title,String sub,String action,boolean connect) {
        LinearLayout r=new LinearLayout(this);r.setGravity(Gravity.CENTER_VERTICAL);r.setPadding(0,dp(12),0,dp(12));
        LinearLayout left=new LinearLayout(this);left.setOrientation(LinearLayout.VERTICAL);left.addView(text(title,11,TEXT,true));left.addView(text(sub,9,MUTED,false));
        r.addView(left,new LinearLayout.LayoutParams(0,-2,1));
        Button b=button(action,connect); b.setTextSize(9);
        if(connect)b.setOnClickListener(v->toast("Account authentication is not connected yet."));
        else if(title.equals("Theme"))b.setOnClickListener(v->{light=!light;profile();});
        else b.setOnClickListener(v->toast(title+" controls will activate after account connection."));
        r.addView(b,new LinearLayout.LayoutParams(dp(100),dp(42)));
        return r;
    }

    private void referral() {
        section("REFERRAL","Grow your circle.","");
        LinearLayout c=cardLayout(); c.addView(text("15%",34,GOLD_LIGHT,true)); c.addView(text("Track referral activity from one dedicated area. The displayed 15% is a product concept and must match final terms.",10,MUTED,false)); content.addView(c);
    }

    private void header(String eyebrow,String first,String gold) {
        LinearLayout h=new LinearLayout(this);h.setOrientation(LinearLayout.VERTICAL);h.setPadding(dp(18),dp(10),dp(18),dp(8));
        TextView e=text(eyebrow.toUpperCase(),9,GOLD_LIGHT,true);e.setLetterSpacing(.16f);h.addView(e);
        LinearLayout title=new LinearLayout(this); TextView a=text(first,30,TEXT,true);TextView g=text(gold,30,GOLD_LIGHT,true);title.addView(a);title.addView(g);h.addView(title);
        content.addView(h);
    }

    private void paragraph(String s){TextView p=text(s,11,MUTED,false);p.setPadding(dp(18),0,dp(18),dp(12));content.addView(p);}
    private void section(String eyebrow,String title,String right){
        LinearLayout s=new LinearLayout(this);s.setGravity(Gravity.CENTER_VERTICAL);s.setPadding(dp(18),dp(18),dp(18),dp(6));
        LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.addView(text(eyebrow,8,MUTED,true));l.addView(text(title,19,TEXT,true));s.addView(l,new LinearLayout.LayoutParams(0,-2,1));s.addView(text(right,9,MUTED,false));content.addView(s);
    }

    private LinearLayout cardLayout(){
        LinearLayout c=new LinearLayout(this);c.setOrientation(LinearLayout.VERTICAL);c.setPadding(dp(16),dp(15),dp(16),dp(15));c.setBackground(round(SURFACE,BORDER,19));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.setMargins(dp(18),dp(7),dp(18),dp(7));c.setLayoutParams(p);return c;
    }

    private Button button(String s,boolean gold){
        Button b=new Button(this);b.setText(s);b.setTextColor(gold?Color.rgb(17,17,15):TEXT);b.setTextSize(10);b.setAllCaps(false);b.setGravity(Gravity.CENTER);b.setPadding(dp(10),dp(6),dp(10),dp(6));b.setBackground(round(gold?GOLD:SURFACE,BORDER,13));return b;
    }

    private TextView label(String s){return text(s,8,MUTED,true);}
    private TextView text(String s,float size,int color,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setTypeface(Typeface.create("sans",bold?Typeface.BOLD:Typeface.NORMAL));t.setIncludeFontPadding(true);return t;}
    private LinearLayout.LayoutParams weightParams(float w,int margin){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,-1,w);p.setMargins(margin>0?dp(margin):0,dp(4),margin>0?dp(margin):0,dp(4));return p;}
    private GradientDrawable round(int fill,int stroke,int radius){GradientDrawable g=new GradientDrawable();g.setColor(fill);if(stroke!=Color.TRANSPARENT)g.setStroke(dp(1),stroke);g.setCornerRadius(dp(radius));return g;}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}

    private void requestMarkets(){
        network.execute(()->{
            try{
                URL u=new URL("https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22,%22DOGEUSDT%22%5D");
                HttpURLConnection c=(HttpURLConnection)u.openConnection();c.setConnectTimeout(7000);c.setReadTimeout(7000);
                if(c.getResponseCode()!=200){c.disconnect();return;}
                BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream()));StringBuilder body=new StringBuilder();String line;while((line=r.readLine())!=null)body.append(line);r.close();c.disconnect();
                JSONArray rows=new JSONArray(body.toString());
                final Map<String,String> prices=new HashMap<>();
                for(int i=0;i<rows.length();i++){JSONObject x=rows.getJSONObject(i);prices.put(x.getString("symbol"),"$"+Double.parseDouble(x.getString("lastPrice"))); }
                runOnUiThread(()->{for(String s:prices.keySet()){TextView v=priceViews.get(s);if(v!=null)v.setText(prices.get(s));}});
            }catch(Exception ignored){}
        });
    }

    @Override public void onBackPressed(){
        showTab(0);
    }

    @Override protected void onDestroy(){network.shutdownNow();super.onDestroy();}
}
