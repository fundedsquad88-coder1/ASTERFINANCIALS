package com.asterfinancials.app;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.net.Uri;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;
import org.xmlpull.v1.XmlPullParser;
import android.util.Xml;

public class MainActivity extends Activity {
    private WebView webView;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(7,7,7));
        getWindow().setNavigationBarColor(Color.rgb(7,7,7));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(7,7,7));
        webView.setWebViewClient(new WebViewClient());
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        webView.addJavascriptInterface(new NativeBridge(), "asterNative");
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    private void send(String function, String payload) {
        final String safe = JSONObject.quote(payload);
        runOnUiThread(() -> {
            if (webView != null) webView.evaluateJavascript("window." + function + "(" + safe + ")", null);
        });
    }

    public class NativeBridge {
        @JavascriptInterface public void requestPrices() {
            executor.execute(() -> {
                try {
                    URL url = new URL("https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22%5D");
                    HttpURLConnection c = (HttpURLConnection) url.openConnection();
                    c.setConnectTimeout(8000); c.setReadTimeout(8000); c.setRequestMethod("GET");
                    c.setRequestProperty("Accept", "application/json");
                    BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream()));
                    StringBuilder out = new StringBuilder(); String line;
                    while ((line = r.readLine()) != null) out.append(line);
                    r.close(); c.disconnect();
                    send("v3ApplyPrices", out.toString());
                } catch (Exception e) {
                    send("v3ApplyPrices", "[]");
                }
            });
        }

        @JavascriptInterface public void requestNews() {
            executor.execute(() -> {
                ArrayList<JSONObject> items = new ArrayList<>();
                String[] feeds = {
                    "https://www.coindesk.com/arc/outboundfeeds/rss/",
                    "https://cointelegraph.com/rss",
                    "https://decrypt.co/feed"
                };
                for (String feed : feeds) {
                    try { parseFeed(feed, items); } catch (Exception ignored) {}
                    if (items.size() >= 12) break;
                }
                JSONArray arr = new JSONArray();
                for (int i=0;i<Math.min(items.size(),12);i++) arr.put(items.get(i));
                send("v3ApplyNews", arr.toString());
            });
        }

        private void parseFeed(String feed, ArrayList<JSONObject> items) throws Exception {
            HttpURLConnection c=(HttpURLConnection)new URL(feed).openConnection();
            c.setConnectTimeout(8000);c.setReadTimeout(8000);c.setRequestMethod("GET");
            c.setRequestProperty("User-Agent","AsterFinancials/4.0");
            XmlPullParser p=Xml.newPullParser();p.setInput(new InputStreamReader(c.getInputStream()));
            String tag=null,title=null,link=null,desc=null,date=null;boolean inItem=false;
            int event;
            while((event=p.next())!=XmlPullParser.END_DOCUMENT){
                if(event==XmlPullParser.START_TAG){tag=p.getName();if("item".equals(tag)||"entry".equals(tag)){inItem=true;title=link=desc=date=null;}}
                else if(event==XmlPullParser.TEXT && inItem && tag!=null){
                    String v=p.getText();
                    if("title".equalsIgnoreCase(tag)) title=v;
                    else if("link".equalsIgnoreCase(tag)) link=v;
                    else if("description".equalsIgnoreCase(tag)||"summary".equalsIgnoreCase(tag)) desc=v;
                    else if("pubDate".equalsIgnoreCase(tag)||"published".equalsIgnoreCase(tag)||"updated".equalsIgnoreCase(tag)) date=v;
                } else if(event==XmlPullParser.END_TAG){
                    String end=p.getName();
                    if(("item".equals(end)||"entry".equals(end))&&inItem){
                        if(title!=null && link!=null){
                            JSONObject o=new JSONObject();o.put("source",sourceName(feed));o.put("title",clean(title));o.put("url",link.trim());o.put("description",clean(desc==null?"":desc));o.put("date",date==null?"Latest":date.trim());items.add(o);
                        } inItem=false;
                    } tag=null;
                }
            }
            c.disconnect();
        }
        private String clean(String s){return s.replaceAll("<[^>]*>","").replaceAll("&amp;","&").replaceAll("&lt;","<").replaceAll("&gt;",">").trim();}
        private String sourceName(String f){if(f.contains("coindesk"))return "CoinDesk";if(f.contains("cointelegraph"))return "Cointelegraph";return "Decrypt";}
        @JavascriptInterface public void openUrl(String url){
            try { startActivity(new android.content.Intent(android.content.Intent.ACTION_VIEW, Uri.parse(url))); } catch(Exception ignored){}
        }
    }

    @Override protected void onDestroy() {
        executor.shutdownNow();
        if(webView!=null){webView.removeJavascriptInterface("asterNative");webView.destroy();webView=null;}
        super.onDestroy();
    }
}
