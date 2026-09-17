package com.asterfinancials.app;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    public final class NativeConfig {
        @JavascriptInterface public String apiBaseUrl() { return BuildConfig.ASTER_API_BASE_URL; }
        @JavascriptInterface public boolean isSandbox() { return true; }
    }
    private String readAsset(String name) throws Exception {
        try (InputStream in = getAssets().open(name); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(5, 6, 6));
        getWindow().setNavigationBarColor(Color.rgb(5, 6, 6));
        WebView w = new WebView(this);
        w.setBackgroundColor(Color.rgb(5, 6, 6));
        w.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                try {
                    view.evaluateJavascript(readAsset("enhancements.js"), null);
                    view.evaluateJavascript(readAsset("wallet-auth.js"), null);
                    view.evaluateJavascript(readAsset("trade-sync.js"), null);
                    view.evaluateJavascript(readAsset("polish.js"), null);
                    view.evaluateJavascript(readAsset("coin-icons.js"), null);
                    view.evaluateJavascript(readAsset("chart-fix.js"), null);
                    view.evaluateJavascript(readAsset("market-terminal.js"), null);
                    view.evaluateJavascript(readAsset("app-polish-v23.js"), null);
                    view.evaluateJavascript(readAsset("app-navigation-v23.js"), null);
                    view.evaluateJavascript(readAsset("app-polish-v24.js"), null);
                } catch (Exception ignored) {}
            }
        });
        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true); s.setAllowContentAccess(true);
        w.addJavascriptInterface(new NativeConfig(), "AsterNative");
        w.loadUrl("file:///android_asset/index.html");
        setContentView(w);
    }
}
