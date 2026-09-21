package com.asterfinancials.app;

import android.app.Activity;
import android.content.Intent;
import android.content.ClipData;
import android.content.ClipboardManager;
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
            WebResourceResponse local = assetLoader.shouldInterceptRequest(request.getUrl());
            return local != null ? local : super.shouldInterceptRequest(view, request);
        }

        @Override public void onPageFinished(WebView view, String url) {
            super.onPageFinished(view, url);
            injectTreasuryWalletUi(view);
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

    private void injectTreasuryWalletUi(WebView view) {
        String js = "(function(){"
                + "if(window.__asterTreasuryUi)return;window.__asterTreasuryUi=1;"
                + "const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\\"/g,'&quot;');"
                + "const cfg=JSON.parse(AsterNative.treasuryConfig());"
                + "function sheet(title,body){"
                + " const back=document.getElementById('sheetBack'),sh=document.getElementById('sheet');"
                + " if(!back||!sh)return;"
                + " sh.innerHTML='<div class=\\\"grab\\\"></div><h3>'+title+'</h3>'+body+'<button class=\\\"primary\\\" id=\\\"closeTreasurySheet\\\" style=\\\"margin-top:14px\\\">Close</button>';"
                + " back.classList.add('on');document.getElementById('closeTreasurySheet').onclick=()=>back.classList.remove('on');"
                + "}"
                + "function deposit(){"
                + " let net='BEP20';"
                + " const render=()=>{const x=cfg.networks.find(n=>n.network===net)||cfg.networks[0];"
                + " return '<div class=\\\"tabs\\\" id=\\\"treasuryTabs\\\">'+cfg.networks.map(n=>'<button class=\\\"'+(n.network===net?'on':'')+'\\\" data-net=\\\"'+n.network+'\\\">'+n.label+'</button>').join('')+'</div>'"
                + " +'<div class=\\\"card\\\" style=\\\"margin:10px 0\\\"><div class=\\\"eyebrow\\\">Aster treasury address</div><div style=\\\"font-size:15px;font-weight:900;word-break:break-all;margin:8px 0 12px\\\">'+esc(x.address)+'</div><div class=\\\"small muted\\\">'+esc(x.name)+' · Send <b>USDT only</b> on this network.</div><div class=\\\"outline-row\\\" style=\\\"margin-top:12px\\\"><button class=\\\"secondary\\\" id=\\\"copyTreasury\\\">Copy address</button><button class=\\\"secondary\\\" id=\\\"shareTreasury\\\">Share</button></div></div>'"
                + " +'<div class=\\\"notice\\\"><b>Important:</b> Sending USDT on another network can permanently lose funds. After sending, keep the blockchain transaction hash for verification.</div>';"
                + " };"
                + " const body=render();sheet('Deposit USDT',body);"
                + " setTimeout(()=>{"
                + "  document.querySelectorAll('#treasuryTabs button').forEach(b=>b.onclick=()=>{net=b.dataset.net;sheet('Deposit USDT',render());bind();});"
                + "  bind();"
                + " },0);"
                + " function bind(){const x=cfg.networks.find(n=>n.network===net)||cfg.networks[0];"
                + "  document.getElementById('copyTreasury')?.addEventListener('click',()=>{AsterNative.copyText(x.address);window.showToast?.('Address copied');});"
                + "  document.getElementById('shareTreasury')?.addEventListener('click',()=>AsterNative.shareText('Aster Financials USDT '+x.label+' deposit address: '+x.address));"
                + " }"
                + "}"
                + "function withdraw(){"
                + " sheet('Withdraw USDT','<div class=\\\"tabs\\\"><button class=\\\"on\\\">BEP20</button><button>TRC20</button></div><label class=\\\"eyebrow\\\">Destination address</label><input class=\\\"input\\\" id=\\\"wdAddress\\\" placeholder=\\\"Paste your wallet address\\\"><label class=\\\"eyebrow\\\">Amount (USDT)</label><input class=\\\"input\\\" id=\\\"wdAmount\\\" inputmode=\\\"decimal\\\" placeholder=\\\"0.00\\\"><div class=\\\"notice\\\">Withdrawals are submitted from Aster treasury after authentication, balance, compliance and transaction checks. This screen never fabricates a withdrawal.</div>');"
                + "}"
                + " document.getElementById('deposit')?.addEventListener('click',deposit,true);"
                + " document.getElementById('withdraw')?.addEventListener('click',withdraw,true);"
                + " document.getElementById('deposit').onclick=deposit;document.getElementById('withdraw').onclick=withdraw;"
                + "})()";
        view.evaluateJavascript(js, null);
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

        @JavascriptInterface public String treasuryConfig() {
            return "{\"custody\":\"Aster treasury\",\"networks\":["
                    + "{\"network\":\"BEP20\",\"label\":\"USDT · BEP20\",\"name\":\"BNB Smart Chain\",\"address\":\"0xAf37c145EE58C0C0bD281BF454Ee92beC93F13d5\"},"
                    + "{\"network\":\"TRC20\",\"label\":\"USDT · TRC20\",\"name\":\"Tron\",\"address\":\"TMrK4d1r2cGye2TwX3JfjCaUDWwZybaoxD\"}"
                    + "]}";
        }

        @JavascriptInterface public void copyText(final String value) {
            main.post(() -> {
                ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("Aster", value == null ? "" : value));
            });
        }

        @JavascriptInterface public void shareText(final String value) {
            main.post(() -> {
                try {
                    Intent send = new Intent(Intent.ACTION_SEND);
                    send.setType("text/plain");
                    send.putExtra(Intent.EXTRA_TEXT, value == null ? "" : value);
                    startActivity(Intent.createChooser(send, "Share Aster address"));
                } catch (Exception ignored) { }
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
