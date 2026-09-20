package com.asterfinancials.app;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.os.Handler;
import android.os.Looper;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private WebView webView;
    private final ExecutorService network = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(11,10,18));
        getWindow().setNavigationBarColor(Color.rgb(11,10,18));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(11,10,18));
        webView.setWebViewClient(new WebViewClient());
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        webView.addJavascriptInterface(new AsterNative(), "AsterNative");
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    public class AsterNative {
        @JavascriptInterface public void fetch(final String urlString, final String callbackId) {
            if (!isAllowed(urlString)) {
                deliver(callbackId, "Blocked host", false);
                return;
            }
            network.execute(() -> {
                HttpURLConnection c = null;
                try {
                    URL url = new URL(urlString);
                    c = (HttpURLConnection) url.openConnection();
                    c.setRequestMethod("GET");
                    c.setConnectTimeout(8000);
                    c.setReadTimeout(10000);
                    c.setRequestProperty("User-Agent", "AsterFinancials/1.0");
                    c.setRequestProperty("Accept", "application/json, application/xml, text/plain, */*");
                    int code = c.getResponseCode();
                    InputStream in = code >= 200 && code < 300 ? c.getInputStream() : c.getErrorStream();
                    String body = read(in);
                    deliver(callbackId, body, code >= 200 && code < 300);
                } catch (Exception e) {
                    deliver(callbackId, e.toString(), false);
                } finally {
                    if (c != null) c.disconnect();
                }
            });
        }

        private boolean isAllowed(String value) {
            try {
                String host = new URL(value).getHost();
                return "api.binance.com".equals(host) || "news.google.com".equals(host);
            } catch (Exception e) { return false; }
        }

        private String read(InputStream in) throws Exception {
            if (in == null) return "";
            BufferedReader r = new BufferedReader(new InputStreamReader(in));
            StringBuilder out = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) out.append(line);
            r.close();
            return out.toString();
        }

        private void deliver(String id, String body, boolean ok) {
            main.post(() -> {
                if (webView == null) return;
                webView.evaluateJavascript("window.__asterNativeResult(" + quote(id) + "," + quote(body) + "," + ok + ")", null);
            });
        }

        private String quote(String value) {
            return """ + value.replace("\\", "\\\\").replace(""", "\\"")
                    .replace("\r", "\\r").replace("\n", "\\n").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029") + """;
        }
    }
}
