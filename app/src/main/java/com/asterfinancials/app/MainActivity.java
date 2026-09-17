package com.asterfinancials.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Xml;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;
import org.xmlpull.v1.XmlPullParser;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.StringReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private WebView webView;
    private final ExecutorService net = Executors.newCachedThreadPool();

    private String readAsset(String name) throws Exception {
        try (InputStream in = getAssets().open(name); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] b = new byte[8192];
            int n;
            while ((n = in.read(b)) != -1) out.write(b, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }

    private String getUrl(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestMethod("GET");
        c.setConnectTimeout(10000);
        c.setReadTimeout(12000);
        c.setUseCaches(false);
        c.setRequestProperty("Accept", "application/json, application/xml, text/xml, */*");
        c.setRequestProperty("User-Agent", "AsterFinancials/1.0 Android Market Intelligence");
        try (InputStream in = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] b = new byte[8192];
            int n;
            while ((n = in.read(b)) != -1) out.write(b, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        } finally {
            c.disconnect();
        }
    }

    private void jsCallback(String fn, String json) {
        if (webView == null) return;
        final String safe = json == null ? "null" : json.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029");
        webView.post(() -> webView.evaluateJavascript(fn + "('" + safe + "')", null));
    }

    private JSONArray parseNewsFeed(String xml, String source) {
        JSONArray out = new JSONArray();
        if (xml == null || xml.isEmpty()) return out;
        try {
            XmlPullParser p = Xml.newPullParser();
            p.setInput(new StringReader(xml));
            boolean item = false;
            String title = "", link = "", date = "", desc = "", tag = "";
            int event;
            while ((event = p.next()) != XmlPullParser.END_DOCUMENT) {
                if (event == XmlPullParser.START_TAG) {
                    tag = p.getName();
                    if ("item".equalsIgnoreCase(tag) || "entry".equalsIgnoreCase(tag)) {
                        item = true; title = ""; link = ""; date = ""; desc = "";
                    } else if (item && ("title".equalsIgnoreCase(tag) || "link".equalsIgnoreCase(tag) || "pubDate".equalsIgnoreCase(tag) || "published".equalsIgnoreCase(tag) || "updated".equalsIgnoreCase(tag) || "description".equalsIgnoreCase(tag) || "summary".equalsIgnoreCase(tag))) {
                        if ("link".equalsIgnoreCase(tag)) {
                            String href = p.getAttributeValue(null, "href");
                            if (href != null && !href.isEmpty()) link = href;
                        }
                    }
                } else if (event == XmlPullParser.TEXT && item) {
                    String value = p.getText();
                    if ("title".equalsIgnoreCase(tag)) title = value;
                    else if ("link".equalsIgnoreCase(tag) && link.isEmpty()) link = value;
                    else if ("pubDate".equalsIgnoreCase(tag) || "published".equalsIgnoreCase(tag) || "updated".equalsIgnoreCase(tag)) date = value;
                    else if ("description".equalsIgnoreCase(tag) || "summary".equalsIgnoreCase(tag)) desc = value;
                } else if (event == XmlPullParser.END_TAG) {
                    String end = p.getName();
                    if (item && ("item".equalsIgnoreCase(end) || "entry".equalsIgnoreCase(end))) {
                        if (!title.trim().isEmpty()) {
                            try {
                                JSONObject o = new JSONObject();
                                o.put("source", source);
                                o.put("title", title.trim());
                                o.put("link", link.trim());
                                o.put("date", date.trim());
                                o.put("desc", desc.trim());
                                out.put(o);
                            } catch (Exception ignored) {}
                        }
                        item = false;
                    }
                    tag = "";
                }
            }
        } catch (Exception ignored) {}
        return out;
    }

    private class AsterBridge {
        @JavascriptInterface public void requestPrices() {
            net.execute(() -> {
                try {
                    String symbols = "%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22%5D";
                    String data = getUrl("https://api.binance.com/api/v3/ticker/24hr?symbols=" + symbols);
                    jsCallback("window.asterNativePrices", data);
                } catch (Exception e) {
                    jsCallback("window.asterNativePrices", "[]");
                }
            });
        }

        @JavascriptInterface public void requestMacro() {
            net.execute(() -> {
                JSONArray out = new JSONArray();
                String[][] map = {{"GC=F", "XAUUSD"}, {"SI=F", "XAGUSD"}, {"CL=F", "WTI"}, {"BZ=F", "BRENT"}};
                for (String[] pair : map) {
                    try {
                        String raw = getUrl("https://query1.finance.yahoo.com/v8/finance/chart/" + Uri.encode(pair[0]) + "?range=1d&interval=5m");
                        JSONObject root = new JSONObject(raw).getJSONObject("chart").getJSONArray("result").getJSONObject(0);
                        JSONObject meta = root.getJSONObject("meta");
                        double price = meta.optDouble("regularMarketPrice", Double.NaN);
                        double prev = meta.optDouble("previousClose", Double.NaN);
                        double change = (!Double.isNaN(price) && !Double.isNaN(prev) && prev != 0) ? ((price - prev) / prev) * 100.0 : Double.NaN;
                        if (!Double.isNaN(price)) {
                            JSONObject o = new JSONObject();
                            o.put("symbol", pair[1]);
                            o.put("price", price);
                            if (!Double.isNaN(change)) o.put("change", change);
                            out.put(o);
                        }
                    } catch (Exception ignored) {}
                }
                jsCallback("window.asterNativeMacro", out.toString());
            });
        }

        @JavascriptInterface public void requestNews() {
            net.execute(() -> {
                JSONArray all = new JSONArray();
                String[][] feeds = {
                        {"CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"},
                        {"Cointelegraph", "https://cointelegraph.com/rss"},
                        {"Decrypt", "https://decrypt.co/feed"}
                };
                for (String[] f : feeds) {
                    try {
                        JSONArray one = parseNewsFeed(getUrl(f[1]), f[0]);
                        for (int i = 0; i < one.length(); i++) all.put(one.get(i));
                    } catch (Exception ignored) {}
                }
                jsCallback("window.asterNativeNews", all.toString());
            });
        }

        @JavascriptInterface public void openUrl(String url) {
            try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) {}
        }
    }

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(5, 6, 6));
        getWindow().setNavigationBarColor(Color.rgb(5, 6, 6));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(5, 6, 6));
        webView.addJavascriptInterface(new AsterBridge(), "asterNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView v, String u) {
                super.onPageFinished(v, u);
                try {
                    v.evaluateJavascript("window._asterOriginalShow=window.show;", null);
                    v.evaluateJavascript(readAsset("app-polish-v23.js"), null);
                    v.evaluateJavascript(readAsset("app-navigation-v23.js"), null);
                    v.evaluateJavascript(readAsset("app-polish-v24.js"), null);
                    v.evaluateJavascript(readAsset("markets-v25.js"), null);
                    v.evaluateJavascript(readAsset("markets-v26.js"), null);
                    v.evaluateJavascript(readAsset("markets-v27.js"), null);
                    v.evaluateJavascript(readAsset("markets-v28.js"), null);
                    v.evaluateJavascript(readAsset("markets-v29.js"), null);
                } catch (Exception ignored) {}
            }
        });
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    @Override protected void onDestroy() {
        net.shutdownNow();
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
