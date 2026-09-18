package com.asterfinancials.app;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.webkit.*;
import android.net.Uri;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.util.concurrent.*;
public class MainActivity extends Activity{
  WebView web; ExecutorService pool=Executors.newSingleThreadExecutor();
  @Override public void onCreate(Bundle b){super.onCreate(b);
    getWindow().setStatusBarColor(Color.rgb(6,7,8)); getWindow().setNavigationBarColor(Color.rgb(6,7,8));
    web=new WebView(this); web.setBackgroundColor(Color.rgb(6,7,8)); web.setWebViewClient(new WebViewClient());
    WebSettings s=web.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true); s.setAllowContentAccess(true);
    web.addJavascriptInterface(new NativeApi(),"asterNative"); setContentView(web); web.loadUrl("file:///android_asset/index.html");
  }
  class NativeApi{
    @JavascriptInterface public void requestPrices(){pool.execute(()->{try{
      URL u=new URL("https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22%5D");
      HttpURLConnection c=(HttpURLConnection)u.openConnection(); c.setConnectTimeout(7000); c.setReadTimeout(7000);
      BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream())); StringBuilder x=new StringBuilder(); String l; while((l=r.readLine())!=null)x.append(l); r.close();
      org.json.JSONArray a=new org.json.JSONArray(x.toString()); JSONObject out=new JSONObject();
      for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);String sym=o.getString("symbol").replace("USDT",""); JSONObject p=new JSONObject();p.put("price",o.getString("lastPrice"));p.put("change",o.getString("priceChangePercent")+"%");out.put(sym,p);}
      String js="window.v4ApplyPrices("+out.toString()+")"; run(js);
    }catch(Exception e){run("window.v4ApplyPrices({})");}});
    }
    void run(String js){runOnUiThread(()->web.evaluateJavascript(js,null));}
  }
  @Override protected void onDestroy(){pool.shutdownNow();super.onDestroy();}
}