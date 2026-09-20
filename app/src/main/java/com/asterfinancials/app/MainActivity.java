package com.asterfinancials.app;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.annotation.Nullable;
import androidx.webkit.WebViewAssetLoader;

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
    private final ExecutorService network = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());
    private WebViewAssetLoader assetLoader;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(11,10,18));
        getWindow().setNavigationBarColor(Color.rgb(11,10,18));

        assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(11,10,18));
        webView.setWebViewClient(new SecureWebViewClient());

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportMultipleWindows(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }

        webView.addJavascriptInterface(new AsterNative(), "AsterNative");
        webView.loadUrl("https://appassets.androidplatform.net/assets/index.html");
        setContentView(webView);
    }

    private class SecureWebViewClient extends WebViewClient {
        @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            WebResourceResponse local = assetLoader.interceptRequest(request.getUrl());
            return local != null ? local : super.shouldInterceptRequest(view, request);
        }

        @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            String scheme = uri.getScheme();
            if ("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme)) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception ignored) { }
                return true;
            }
            return true;
        }

        @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
            // Prevent a renderer crash from taking down the Activity.
            view.post(() -> {
                if (webView != null) {
                    webView.loadUrl("https://appassets.androidplatform.net/assets/index.html");
                }
            });
            return true;
        }
    }

    public class AsterNative {
        @JavascriptInterface public void haptic(final String kind) {
            main.post(() -> {
                android.os.Vibrator v = (android.os.Vibrator) getSystemService(VIBRATOR_SERVICE);
                if (v == null || !v.hasVibrator()) return;
                long[] pattern = "success".equals(kind)
                        ? new long[]{0,18,30,28}
                        : "medium".equals(kind)
                        ? new long[]{0,24}
                        : new long[]{0,10};
                try {
                    if (android.os.Build.VERSION.SDK_INT >= 26) {
                        v.vibrate(android.os.VibrationEffect.createWaveform(pattern, -1));
                    } else {
                        v.vibrate(pattern, -1);
                    }
                } catch (SecurityException ignored) { }
            });
        }

        @JavascriptInterface public void fetch(final String urlString, final String callbackId) {
            if (!isAllowed(urlString)) {
                deliver(callbackId, "Blocked network request", false);
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
                    c.setInstanceFollowRedirects(false);
                    c.setRequestProperty("User-Agent", "AsterFinancials/1.1");
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
                URL url = new URL(value);
                if (!"https".equalsIgnoreCase(url.getProtocol())) return false;
                String host = url.getHost();
                return "api.binance.com".equals(host)
                        || "data-api.binance.vision".equals(host)
                        || "api-gcp.binance.com".equals(host)
                        || "api1.binance.com".equals(host)
                        || "api2.binance.com".equals(host)
                        || "api3.binance.com".equals(host)
                        || "api4.binance.com".equals(host)
                        || "news.google.com".equals(host) || "api.frankfurter.dev".equals(host);
            } catch (Exception e) {
                return false;
            }
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
                webView.evaluateJavascript(
                        "window.__asterNativeResult(" + quote(id) + "," + quote(body) + "," + ok + ")",
                        null
                );
            });
        }

        private String quote(String value) {
            return JSONObject.quote(value == null ? "" : value);
        }
    }

    @Override protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.removeJavascriptInterface("AsterNative");
            webView.destroy();
            webView = null;
        }
        network.shutdownNow();
        super.onDestroy();
    }
}
