package com.asterfinancials.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private WebView webView;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(5,6,6));
        getWindow().setNavigationBarColor(Color.rgb(5,6,6));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(5,6,6));
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        webView.addJavascriptInterface(new AsterBridge(), "asterNative");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    private void runJs(String js){ webView.post(()->webView.evaluateJavascript(js,null)); }

    private String get(String url) throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(12000); c.setReadTimeout(15000); c.setRequestProperty("User-Agent","AsterFinancials/3.0");
        c.setRequestMethod("GET");
        InputStream in=c.getResponseCode()>=400?c.getErrorStream():c.getInputStream();
        BufferedReader r=new BufferedReader(new InputStreamReader(in)); StringBuilder b=new StringBuilder(); String line;
        while((line=r.readLine())!=null)b.append(line); r.close(); c.disconnect(); return b.toString();
    }

    public class AsterBridge {
        @JavascriptInterface public void requestPrices(){
            executor.execute(()->{
                try{
                    String symbols="[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\",\"BNBUSDT\",\"XRPUSDT\"]";
                    String data=get("https://api.binance.com/api/v3/ticker/24hr?symbols="+Uri.encode(symbols));
                    runJs("window.v3ApplyPrices("+JSONObject.quote(data)+");");
                }catch(Exception ignored){}
            });
        }
        @JavascriptInterface public void requestNews(){
            executor.execute(()->{
                try{
                    String[] urls={
                        "https://www.coindesk.com/arc/outboundfeeds/rss/",
                        "https://cointelegraph.com/rss",
                        "https://decrypt.co/feed"
                    };
                    String[] names={"CoinDesk","Cointelegraph","Decrypt"};
                    JSONArray out=new JSONArray();
                    for(int i=0;i<urls.length;i++){
                        try{ JSONObject o=new JSONObject();o.put("source",names[i]);o.put("xml",get(urls[i]));out.put(o); }catch(Exception ignored){}
                    }
                    runJs("window.v3ApplyNews("+out.toString()+");");
                }catch(Exception ignored){}
            });
        }
        @JavascriptInterface public void openUrl(String url){
            try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url)));}catch(Exception ignored){}
        }
    }

    @Override protected void onDestroy(){ executor.shutdownNow(); if(webView!=null)webView.destroy(); super.onDestroy(); }
}