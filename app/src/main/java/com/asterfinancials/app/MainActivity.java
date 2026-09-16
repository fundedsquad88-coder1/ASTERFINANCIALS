package com.asterfinancials.app;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    public final class NativeConfig {
        @JavascriptInterface
        public String apiBaseUrl() {
            return BuildConfig.ASTER_API_BASE_URL;
        }
        @JavascriptInterface
        public boolean isSandbox() {
            return true;
        }
    }

    @Override
    public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(5, 6, 6));
        getWindow().setNavigationBarColor(Color.rgb(5, 6, 6));

        WebView w = new WebView(this);
        w.setBackgroundColor(Color.rgb(5, 6, 6));
        w.setWebViewClient(new WebViewClient());
        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        w.addJavascriptInterface(new NativeConfig(), "AsterNative");
        w.loadUrl("file:///android_asset/index.html");
        setContentView(w);
    }
}
